from abc import ABC, abstractmethod


class LLMError(RuntimeError):
    """Raised when the configured LLM cannot produce a response."""


class LLMTimeoutError(LLMError):
    """Raised when the configured LLM exceeds the request timeout."""


class BaseLLMProvider(ABC):
    @abstractmethod
    def chat(self, user_message: str, *, system_prompt: str | None = None) -> str:
        """Return a response for the supplied user message."""
