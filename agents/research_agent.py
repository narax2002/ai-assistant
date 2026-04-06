"""Research agent — gathers and summarizes key information on a topic."""

import asyncio
import logging

from agents.base import BaseAgent
from llm.base import BaseLLMProvider
from sources.web_search import format_results, search

LOGGER = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "당신은 리서치 전문가다. "
    "주어진 주제의 핵심 내용을 3~5문장으로 요약하라. "
    "사실 위주로 간결하게, 부연 설명 없이 답하라. "
    "한국어로 답변하라."
)

_SYSTEM_PROMPT_WITH_SOURCES = (
    "당신은 리서치 전문가다. "
    "아래 검색 결과를 참고하여 주제의 핵심 내용을 3~5문장으로 요약하라. "
    "사실 위주로 간결하게, 부연 설명 없이 답하라. "
    "한국어로 답변하라."
)


class ResearchAgent(BaseAgent):
    def __init__(
        self,
        provider: BaseLLMProvider,
        *,
        timeout_seconds: int = 60,
        max_search_results: int = 5,
    ) -> None:
        super().__init__(provider, timeout_seconds=timeout_seconds)
        self._max_search_results = max_search_results
        self._last_sources: list[str] = []

    @property
    def name(self) -> str:
        return "research"

    @property
    def system_prompt(self) -> str:
        return _SYSTEM_PROMPT

    @property
    def last_sources(self) -> list[str]:
        return list(self._last_sources)

    async def run(self, query: str) -> str:
        results = await asyncio.to_thread(search, query, self._max_search_results)
        self._last_sources = [r.url for r in results if r.url]

        context = format_results(results)
        if context:
            LOGGER.info("Web search returned %d results for: %s", len(results), query)
            prompt = f"{context}\n\n질문: {query}"
            return await asyncio.wait_for(
                asyncio.to_thread(
                    self._provider.chat, prompt, system_prompt=_SYSTEM_PROMPT_WITH_SOURCES
                ),
                timeout=self.timeout_seconds,
            )

        LOGGER.info("No web results, falling back to LLM knowledge for: %s", query)
        return await asyncio.wait_for(
            asyncio.to_thread(self._provider.chat, query, system_prompt=_SYSTEM_PROMPT),
            timeout=self.timeout_seconds,
        )
