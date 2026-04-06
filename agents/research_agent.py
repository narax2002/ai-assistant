"""Research agent — gathers and summarizes key information on a topic."""

from agents.base import BaseAgent

_SYSTEM_PROMPT = (
    "당신은 리서치 전문가다. "
    "주어진 주제의 핵심 내용을 3~5문장으로 요약하라. "
    "사실 위주로 간결하게, 부연 설명 없이 답하라. "
    "한국어로 답변하라."
)


class ResearchAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "research"

    @property
    def system_prompt(self) -> str:
        return _SYSTEM_PROMPT
