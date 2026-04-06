import asyncio
from unittest.mock import patch

from agents.analyst_agent import AnalystAgent
from agents.research_agent import ResearchAgent
from agents.writer_agent import WriterAgent
from llm.base import BaseLLMProvider, LLMError
from orchestrator.supervisor import Supervisor
from schemas.research import ResearchRequest
from sources.web_search import SearchResult


class FakeProvider(BaseLLMProvider):
    def chat(self, user_message: str, *, system_prompt: str | None = None) -> str:
        return f"[fake] {user_message}"


class FailingProvider(BaseLLMProvider):
    def chat(self, user_message: str, *, system_prompt: str | None = None) -> str:
        raise LLMError("provider down")


def _make_supervisor(provider: BaseLLMProvider | None = None) -> Supervisor:
    p = provider or FakeProvider()
    return Supervisor(
        research_agent=ResearchAgent(p),
        analyst_agent=AnalystAgent(p),
        writer_agent=WriterAgent(p),
    )


_FAKE_RESULTS = [
    SearchResult(title="T1", url="https://example.com/1", snippet="S1"),
    SearchResult(title="T2", url="https://example.com/2", snippet="S2"),
]


def test_handle_returns_response_with_all_fields():
    supervisor = _make_supervisor()
    req = ResearchRequest(query="멀티에이전트", request_id="test-001")
    with patch("agents.research_agent.search", return_value=_FAKE_RESULTS):
        resp = asyncio.run(supervisor.handle(req))

    assert resp.request_id == "test-001"
    assert resp.summary
    assert resp.comparison
    assert resp.next_actions
    assert resp.sources


def test_handle_includes_source_urls():
    supervisor = _make_supervisor()
    req = ResearchRequest(query="테스트")
    with patch("agents.research_agent.search", return_value=_FAKE_RESULTS):
        resp = asyncio.run(supervisor.handle(req))

    assert "https://example.com/1" in resp.sources
    assert "https://example.com/2" in resp.sources


def test_handle_falls_back_sources_when_no_results():
    supervisor = _make_supervisor()
    req = ResearchRequest(query="테스트")
    with patch("agents.research_agent.search", return_value=[]):
        resp = asyncio.run(supervisor.handle(req))

    assert "LLM 내부 지식" in resp.sources


def test_handle_includes_agent_results():
    supervisor = _make_supervisor()
    req = ResearchRequest(query="테스트")
    with patch("agents.research_agent.search", return_value=[]):
        resp = asyncio.run(supervisor.handle(req))

    assert len(resp.agent_results) == 3
    assert all(r.success for r in resp.agent_results)


def test_handle_graceful_degradation_on_failure():
    supervisor = _make_supervisor(FailingProvider())
    req = ResearchRequest(query="테스트")
    with patch("agents.research_agent.search", return_value=[]):
        resp = asyncio.run(supervisor.handle(req))

    assert "실패" in resp.summary
    assert all(not r.success for r in resp.agent_results)


def test_handle_context_chaining():
    """Analyst and writer receive research summary as context."""
    calls: list[str] = []
    original_fake = FakeProvider()

    class TrackingProvider(BaseLLMProvider):
        def chat(self, user_message: str, *, system_prompt: str | None = None) -> str:
            calls.append(user_message)
            return original_fake.chat(user_message, system_prompt=system_prompt)

    supervisor = _make_supervisor(TrackingProvider())
    req = ResearchRequest(query="테스트 주제")
    with patch("agents.research_agent.search", return_value=[]):
        asyncio.run(supervisor.handle(req))

    # First call is research agent (just query), next two should contain research summary
    assert len(calls) == 3
    assert "리서치 요약" in calls[1]
    assert "리서치 요약" in calls[2]


def test_handle_format_discord_has_sections():
    supervisor = _make_supervisor()
    req = ResearchRequest(query="테스트")
    with patch("agents.research_agent.search", return_value=[]):
        resp = asyncio.run(supervisor.handle(req))
    text = resp.format_discord()

    assert "**핵심 요약**" in text
    assert "**비교**" in text
    assert "**다음 행동**" in text
    assert "**출처**" in text
