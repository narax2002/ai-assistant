import asyncio

from agents.analyst_agent import AnalystAgent
from agents.research_agent import ResearchAgent
from agents.writer_agent import WriterAgent
from llm.base import BaseLLMProvider


class FakeProvider(BaseLLMProvider):
    def chat(self, user_message: str, *, system_prompt: str | None = None) -> str:
        return f"[fake] {user_message}"


def test_research_agent_name():
    assert ResearchAgent(FakeProvider()).name == "research"


def test_analyst_agent_name():
    assert AnalystAgent(FakeProvider()).name == "analyst"


def test_writer_agent_name():
    assert WriterAgent(FakeProvider()).name == "writer"


def test_research_agent_calls_provider():
    result = asyncio.run(ResearchAgent(FakeProvider()).run("test query"))
    assert "[fake]" in result
    assert "test query" in result


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
