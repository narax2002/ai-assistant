import asyncio
from unittest.mock import patch

from agents.analyst_agent import AnalystAgent
from agents.research_agent import ResearchAgent
from agents.writer_agent import WriterAgent
from llm.base import BaseLLMProvider
from sources.web_search import SearchResult


class FakeProvider(BaseLLMProvider):
    def chat(self, user_message: str, *, system_prompt: str | None = None) -> str:
        return f"[fake] {user_message}"


def test_research_agent_name():
    assert ResearchAgent(FakeProvider()).name == "research"


def test_analyst_agent_name():
    assert AnalystAgent(FakeProvider()).name == "analyst"


def test_writer_agent_name():
    assert WriterAgent(FakeProvider()).name == "writer"


def test_research_agent_with_web_results():
    fake_results = [
        SearchResult(title="Title 1", url="https://example.com/1", snippet="Snippet 1"),
        SearchResult(title="Title 2", url="https://example.com/2", snippet="Snippet 2"),
    ]
    with patch("agents.research_agent.search", return_value=fake_results):
        result = asyncio.run(ResearchAgent(FakeProvider()).run("test query"))
    assert "[fake]" in result
    assert "test query" in result


def test_research_agent_collects_sources():
    fake_results = [
        SearchResult(title="T", url="https://example.com/a", snippet="S"),
    ]
    agent = ResearchAgent(FakeProvider())
    with patch("agents.research_agent.search", return_value=fake_results):
        asyncio.run(agent.run("test"))
    assert agent.last_sources == ["https://example.com/a"]


def test_research_agent_falls_back_without_results():
    with patch("agents.research_agent.search", return_value=[]):
        result = asyncio.run(ResearchAgent(FakeProvider()).run("test query"))
    assert "[fake]" in result


def test_analyst_agent_calls_provider():
    result = asyncio.run(AnalystAgent(FakeProvider()).run("test query"))
    assert "[fake]" in result


def test_writer_agent_calls_provider():
    result = asyncio.run(WriterAgent(FakeProvider()).run("test query"))
    assert "[fake]" in result


def test_each_agent_has_system_prompt():
    p = FakeProvider()
    assert ResearchAgent(p).system_prompt
    assert AnalystAgent(p).system_prompt
    assert WriterAgent(p).system_prompt


def test_agent_accepts_timeout():
    agent = ResearchAgent(FakeProvider(), timeout_seconds=30)
    assert agent.timeout_seconds == 30
