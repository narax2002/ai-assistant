import asyncio

from agents.analyst_agent import AnalystAgent
from agents.research_agent import ResearchAgent
from agents.writer_agent import WriterAgent
from llm.base import BaseLLMProvider
from orchestrator.supervisor import Supervisor
from schemas.research import ResearchRequest


class FakeProvider(BaseLLMProvider):
    def chat(self, user_message: str, *, system_prompt: str | None = None) -> str:
        return f"[fake] {user_message}"


def _make_supervisor() -> Supervisor:
    p = FakeProvider()
    return Supervisor(
        research_agent=ResearchAgent(p),
        analyst_agent=AnalystAgent(p),
        writer_agent=WriterAgent(p),
    )


def test_handle_returns_response_with_all_fields():
    supervisor = _make_supervisor()
    req = ResearchRequest(query="멀티에이전트", request_id="test-001")
    resp = asyncio.run(supervisor.handle(req))

    assert resp.request_id == "test-001"
    assert resp.summary
    assert resp.comparison
    assert resp.next_actions
    assert resp.sources


def test_handle_format_discord_has_sections():
    supervisor = _make_supervisor()
    req = ResearchRequest(query="테스트")
    resp = asyncio.run(supervisor.handle(req))
    text = resp.format_discord()

    assert "**핵심 요약**" in text
    assert "**비교**" in text
    assert "**다음 행동**" in text
    assert "**출처**" in text
