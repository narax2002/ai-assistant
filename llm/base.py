from abc import ABC, abstractmethod
from dataclasses import dataclass


class LLMError(RuntimeError):
    """Raised when the configured LLM cannot produce a response."""

    transient: bool = False


class LLMTimeoutError(LLMError):
    """Raised when the configured LLM exceeds the request timeout."""

    transient: bool = True


class LLMConnectionError(LLMError):
    """Raised when the LLM server is unreachable."""

    transient: bool = True


@dataclass(frozen=True)
class ChatUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class BaseLLMProvider(ABC):
    name: str = "base"

    def __init__(self) -> None:
        self.last_usage: ChatUsage = ChatUsage()

    @abstractmethod
    def chat(self, user_message: str, *, system_prompt: str | None = None) -> str:
        """Return a response for the supplied user message."""

    def chat_with_history(
        self,
        history: list[dict[str, str]],
        user_message: str,
        *,
        system_prompt: str | None = None,
    ) -> str:
        """Default: stitch prior turns into a single prompt. Override for native APIs.

        history: list of {"role": "user"|"assistant", "content": str} from oldest to newest.
        """
        if not history:
            return self.chat(user_message, system_prompt=system_prompt)

        lines: list[str] = []
        for turn in history:
            label = "User" if turn["role"] == "user" else "Assistant"
            lines.append(f"{label}: {turn['content']}")
        lines.append(f"User: {user_message}")
        lines.append("Assistant:")
        stitched = "\n\n".join(lines)
        return self.chat(stitched, system_prompt=system_prompt)
