"""Analyst agent — compares and evaluates alternatives."""

from agents.base import BaseAgent

_SYSTEM_PROMPT = (
    "당신은 분석 전문가다. "
    "주어진 주제에 대해 2~3개 대안을 비교하라. "
    "각 대안의 장점과 단점을 한 줄씩만 쓰라. "
    "서론, 결론, 부연 설명을 쓰지 마라. "
    "한국어로 답변하라."
)


class AnalystAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "analyst"

    @property
    def system_prompt(self) -> str:
        return _SYSTEM_PROMPT
