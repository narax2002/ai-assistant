import logging

from llm.base import BaseLLMProvider, LLMError

LOGGER = logging.getLogger(__name__)


class FallbackProvider(BaseLLMProvider):
    """Tries each provider in order, falling back on transient errors only."""

    def __init__(self, providers: list[BaseLLMProvider]) -> None:
        super().__init__()
        if not providers:
            raise ValueError("At least one provider is required")
        self._providers = providers
        self.last_provider_index: int = 0

    def chat(self, user_message: str, *, system_prompt: str | None = None) -> str:
        last_error: LLMError | None = None

        for i, provider in enumerate(self._providers):
            try:
                result = provider.chat(user_message, system_prompt=system_prompt)
                self.last_usage = provider.last_usage
                self.last_provider_index = i
                if i > 0:
                    LOGGER.info("Fallback succeeded on provider #%d", i)
                return result
            except LLMError as exc:
                last_error = exc
                if not exc.transient:
                    LOGGER.error("Non-transient error from provider #%d, not retrying: %s", i, exc)
                    raise
                LOGGER.warning("Transient error from provider #%d, trying next: %s", i, exc)

        # All providers exhausted
        assert last_error is not None
        raise last_error
