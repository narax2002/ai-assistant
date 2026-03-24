from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    @abstractmethod
    def chat(self, user_message: str) -> str:
        """Return a response for the supplied user message."""
