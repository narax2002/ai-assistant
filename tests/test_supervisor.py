import asyncio

from agents.analyst_agent import AnalystAgent
from agents.research_agent import ResearchAgent
from agents.writer_agent import WriterAgent
from llm.base import BaseLLMProvider, LLMError
from orchestrator.supervisor import Supervisor
from schemas.research import ResearchRequest


class FakeProvider(BaseLLMProvider):
    def chat(self, user_message: str, *, system_prompt: str | None = None) -> str:
        return f"[fake] {user_message}"


class FailingProvider(BaseLLMProvider):
    """Always raises LLMError."""

    def chat(self, user_message: str, *, system_prompt: str | None = None) -> str:
        raise LLMError("provider down")


def _make_supervisor(provider: BaseLLMProvider | None = None) -> Supervisor:
    p = provider or FakeProvider()
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


def test_handle_includes_agent_results():
    supervisor = _make_supervisor()
    req = ResearchRequest(query="테스트")
    resp = asyncio.run(supervisor.handle(req))

    assert len(resp.agent_results) == 3
    assert all(r.success for r in resp.agent_results)
    assert resp.total_elapsed_seconds >= 0


def test_handle_tracks_elapsed_time():
    supervisor = _make_supervisor()
    req = ResearchRequest(query="테스트")
    resp = asyncio.run(supervisor.handle(req))

    for r in resp.agent_results:
        assert r.elapsed_seconds >= 0


def test_handle_graceful_degradation_on_failure():
    supervisor = _make_supervisor(FailingProvider())
    req = ResearchRequest(query="테스트")
    resp = asyncio.run(supervisor.handle(req))

    assert "실패" in resp.summary
    assert "실패" in resp.comparison
    assert "실패" in resp.next_actions
    assert all(not r.success for r in resp.agent_results)
    assert all(r.error for r in resp.agent_results)


def test_handle_format_discord_has_sections():
    supervisor = _make_supervisor()
    req = ResearchRequest(query="테스트")
    resp = asyncio.run(supervisor.handle(req))
    text = resp.format_discord()

    assert "**핵심 요약**" in text
    assert "**비교**" in text
    assert "**다음 행동**" in text
    assert "**출처**" in text
