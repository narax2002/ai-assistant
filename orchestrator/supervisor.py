"""Supervisor — thin control layer that dispatches work to agents."""

import asyncio
import logging
import time

from agents.base import BaseAgent
from agents.research_agent import ResearchAgent
from llm.base import LLMError
from schemas.research import AgentResult, ResearchRequest, ResearchResponse

LOGGER = logging.getLogger(__name__)

_FALLBACK_TEXT = "이 섹션은 생성에 실패했습니다."
_MAX_ATTEMPTS = 2


class Supervisor:
    def __init__(
        self,
        research_agent: ResearchAgent,
        analyst_agent: BaseAgent,
        writer_agent: BaseAgent,
    ) -> None:
        self._research = research_agent
        self._analyst = analyst_agent
        self._writer = writer_agent

    async def handle(self, request: ResearchRequest) -> ResearchResponse:
        LOGGER.info("Handling request %s: %s", request.request_id, request.query)
        pipeline_start = time.monotonic()

        # Step 1: Research with web search
        summary_result = await self._run_agent(self._research, request.query)

        # Collect sources from research agent
        source_urls = self._research.last_sources

        # Step 2: Pass research summary as context to analyst and writer
        context_query = request.query
        if summary_result.success:
            context_query = f"주제: {request.query}\n\n리서치 요약:\n{summary_result.output}"

        comparison_result = await self._run_agent(self._analyst, context_query)
        actions_result = await self._run_agent(self._writer, context_query)

        total_elapsed = time.monotonic() - pipeline_start
        agent_results = [summary_result, comparison_result, actions_result]

        # Format sources
        if source_urls:
            sources_text = "\n".join(f"- {url}" for url in source_urls)
        else:
            sources_text = "이 응답은 LLM 내부 지식을 기반으로 작성되었습니다."

        LOGGER.info(
            "Request %s completed in %.1fs (research=%.1fs analyst=%.1fs writer=%.1fs sources=%d)",
            request.request_id,
            total_elapsed,
            summary_result.elapsed_seconds,
            comparison_result.elapsed_seconds,
            actions_result.elapsed_seconds,
            len(source_urls),
        )

        return ResearchResponse(
            request_id=request.request_id,
            summary=summary_result.output,
            comparison=comparison_result.output,
            next_actions=actions_result.output,
            sources=sources_text,
            agent_results=agent_results,
            total_elapsed_seconds=round(total_elapsed, 1),
        )

    async def _run_agent(self, agent: BaseAgent, query: str) -> AgentResult:
        for attempt in range(_MAX_ATTEMPTS):
            start = time.monotonic()
            try:
                output = await agent.run(query)
                elapsed = time.monotonic() - start
                LOGGER.info(
                    "Agent '%s' succeeded in %.1fs (attempt %d)",
                    agent.name,
                    elapsed,
                    attempt + 1,
                )
                return AgentResult(
                    agent_name=agent.name,
                    output=output,
                    elapsed_seconds=round(elapsed, 1),
                    success=True,
                )
            except (LLMError, asyncio.TimeoutError) as exc:
                elapsed = time.monotonic() - start
                LOGGER.warning(
                    "Agent '%s' failed in %.1fs (attempt %d): %s",
                    agent.name,
                    elapsed,
                    attempt + 1,
                    exc,
                )
                if attempt + 1 < _MAX_ATTEMPTS:
                    continue
                return AgentResult(
                    agent_name=agent.name,
                    output=_FALLBACK_TEXT,
                    elapsed_seconds=round(elapsed, 1),
                    success=False,
                    error=str(exc),
                )

        return AgentResult(
            agent_name=agent.name,
            output=_FALLBACK_TEXT,
            elapsed_seconds=0.0,
            success=False,
            error="exhausted retries",
        )
