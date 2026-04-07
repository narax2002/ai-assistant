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
    def __init__(self) -> None:
        self.last_usage: ChatUsage = ChatUsage()

    @abstractmethod
    def chat(self, user_message: str, *, system_prompt: str | None = None) -> str:
        """Return a response for the supplied user message."""
