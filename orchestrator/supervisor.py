"""Supervisor — thin control layer that dispatches work to agents."""

import asyncio
import logging
import time

from agents.base import BaseAgent
from agents.research_agent import ResearchAgent
from llm.base import BaseLLMProvider, LLMError
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
        provider: BaseLLMProvider | None = None,
    ) -> None:
        self._research = research_agent
        self._analyst = analyst_agent
        self._writer = writer_agent
        self._provider = provider

    async def handle(self, request: ResearchRequest) -> ResearchResponse:
        rid = request.request_id
        LOGGER.info("[%s] Start query=%s", rid, request.query)
        pipeline_start = time.monotonic()

        # Step 1: Research with web search
        summary_result = await self._run_agent(self._research, request.query, rid)

        # Collect sources from research agent
        source_urls = self._research.last_sources

        # Step 2: Pass research summary as context to analyst and writer
        context_query = request.query
        if summary_result.success:
            context_query = f"주제: {request.query}\n\n리서치 요약:\n{summary_result.output}"

        comparison_result = await self._run_agent(self._analyst, context_query, rid)
        actions_result = await self._run_agent(self._writer, context_query, rid)

        total_elapsed = time.monotonic() - pipeline_start
        agent_results = [summary_result, comparison_result, actions_result]

        total_prompt = sum(r.prompt_tokens for r in agent_results)
        total_completion = sum(r.completion_tokens for r in agent_results)

        # Format sources
        if source_urls:
            sources_text = "\n".join(f"- {url}" for url in source_urls)
        else:
            sources_text = "이 응답은 LLM 내부 지식을 기반으로 작성되었습니다."

        LOGGER.info(
            "[%s] Done in %.1fs | research=%.1fs analyst=%.1fs writer=%.1fs | "
            "tokens=%d (prompt=%d completion=%d) | sources=%d",
            rid,
            total_elapsed,
            summary_result.elapsed_seconds,
            comparison_result.elapsed_seconds,
            actions_result.elapsed_seconds,
            total_prompt + total_completion,
            total_prompt,
            total_completion,
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

    def _read_usage(self) -> tuple[int, int]:
        if self._provider is None:
            return 0, 0
        usage = self._provider.last_usage
        return usage.prompt_tokens, usage.completion_tokens

    async def _run_agent(self, agent: BaseAgent, query: str, request_id: str = "") -> AgentResult:
        tag = f"[{request_id}] " if request_id else ""
        for attempt in range(_MAX_ATTEMPTS):
            start = time.monotonic()
            try:
                output = await agent.run(query)
                elapsed = time.monotonic() - start
                prompt_tok, completion_tok = self._read_usage()
                LOGGER.info(
                    "%s%s OK %.1fs attempt=%d tokens=%d",
                    tag,
                    agent.name,
                    elapsed,
                    attempt + 1,
                    prompt_tok + completion_tok,
                )
                return AgentResult(
                    agent_name=agent.name,
                    output=output,
                    elapsed_seconds=round(elapsed, 1),
                    success=True,
                    prompt_tokens=prompt_tok,
                    completion_tokens=completion_tok,
                )
            except (LLMError, asyncio.TimeoutError) as exc:
                elapsed = time.monotonic() - start
                err_type = type(exc).__name__
                is_transient = getattr(exc, "transient", False)
                LOGGER.warning(
                    "%s%s FAIL %.1fs attempt=%d error=%s(%s) transient=%s",
                    tag,
                    agent.name,
                    elapsed,
                    attempt + 1,
                    err_type,
                    exc,
                    is_transient,
                )
                if attempt + 1 < _MAX_ATTEMPTS:
                    continue
                return AgentResult(
                    agent_name=agent.name,
                    output=_FALLBACK_TEXT,
                    elapsed_seconds=round(elapsed, 1),
                    success=False,
                    error=f"{err_type}: {exc}",
                )

        return AgentResult(
            agent_name=agent.name,
            output=_FALLBACK_TEXT,
            elapsed_seconds=0.0,
            success=False,
            error="exhausted retries",
        )
