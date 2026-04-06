"""Supervisor — thin control layer that dispatches work to agents."""

import logging

from agents.base import BaseAgent
from schemas.research import ResearchRequest, ResearchResponse

LOGGER = logging.getLogger(__name__)


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

        summary = await self._research.run(request.query)
        comparison = await self._analyst.run(request.query)
        next_actions = await self._writer.run(request.query)
        sources = "이 응답은 LLM 내부 지식을 기반으로 작성되었습니다."

        return ResearchResponse(
            request_id=request.request_id,
            summary=summary,
            comparison=comparison,
            next_actions=next_actions,
            sources=sources,
        )
