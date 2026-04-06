"""Supervisor — thin control layer that dispatches work to agents."""

import asyncio
import logging
import time

from agents.base import BaseAgent
from llm.base import LLMError
from schemas.research import AgentResult, ResearchRequest, ResearchResponse

LOGGER = logging.getLogger(__name__)

_FALLBACK_TEXT = "이 섹션은 생성에 실패했습니다."
_MAX_ATTEMPTS = 2


class Supervisor:
    def __init__(
        self,
        research_agent: BaseAgent,
        analyst_agent: BaseAgent,
        writer_agent: BaseAgent,
    ) -> None:
        self._research = research_agent
        self._analyst = analyst_agent
        self._writer = writer_agent

    async def handle(self, request: ResearchRequest) -> ResearchResponse:
        LOGGER.info("Handling request %s: %s", request.request_id, request.query)
        pipeline_start = time.monotonic()

        summary_result = await self._run_agent(self._research, request.query)
        comparison_result = await self._run_agent(self._analyst, request.query)
        actions_result = await self._run_agent(self._writer, request.query)

        total_elapsed = time.monotonic() - pipeline_start
        agent_results = [summary_result, comparison_result, actions_result]

        LOGGER.info(
            "Request %s completed in %.1fs (research=%.1fs analyst=%.1fs writer=%.1fs)",
            request.request_id,
            total_elapsed,
            summary_result.elapsed_seconds,
            comparison_result.elapsed_seconds,
            actions_result.elapsed_seconds,
        )

        return ResearchResponse(
            request_id=request.request_id,
            summary=summary_result.output,
            comparison=comparison_result.output,
            next_actions=actions_result.output,
            sources="이 응답은 LLM 내부 지식을 기반으로 작성되었습니다.",
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

        # unreachable, but satisfies type checker
        return AgentResult(
            agent_name=agent.name,
            output=_FALLBACK_TEXT,
            elapsed_seconds=0.0,
            success=False,
            error="exhausted retries",
        )
