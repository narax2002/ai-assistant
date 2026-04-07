"""Input/output contract for the research assistant pipeline.

ResearchRequest carries the user query into the pipeline.
ResearchResponse carries the structured result back to the interface.

The fixed output format has four sections:
  - 핵심 요약: high-level answer
  - 비교: comparison of alternatives or perspectives
  - 다음 행동: actionable next steps
  - 출처: sources used
"""

import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ResearchRequest:
    query: str
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    followup_from: str | None = None


@dataclass(frozen=True)
class AgentResult:
    agent_name: str
    output: str
    elapsed_seconds: float
    success: bool
    error: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass(frozen=True)
class ResearchResponse:
    request_id: str
    summary: str
    comparison: str
    next_actions: str
    sources: str
    agent_results: list[AgentResult] = field(default_factory=list)
    total_elapsed_seconds: float = 0.0

    def format_discord(self) -> str:
        return (
            f"**핵심 요약**\n{self.summary}\n\n"
            f"**비교**\n{self.comparison}\n\n"
            f"**다음 행동**\n{self.next_actions}\n\n"
            f"**출처**\n{self.sources}"
        )
