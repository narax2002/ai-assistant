"""Writer agent — produces actionable next steps."""

from agents.base import BaseAgent

_SYSTEM_PROMPT = (
    "당신은 행동 계획 전문가다. "
    "주어진 주제에 대해 바로 실행할 수 있는 행동 3~5개를 번호 리스트로 제시하라. "
    "각 항목은 한 줄, 20자 이내로 쓰라. "
    "서론, 결론, 부연 설명을 쓰지 마라. "
    "한국어로 답변하라."
)


class WriterAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "writer"

    @property
    def system_prompt(self) -> str:
        return _SYSTEM_PROMPT
