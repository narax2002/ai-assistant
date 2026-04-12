import pytest

from llm.base import BaseLLMProvider, ChatUsage, LLMConnectionError, LLMError, LLMTimeoutError
from llm.fallback_provider import FallbackProvider


class FakeProvider(BaseLLMProvider):
    def __init__(self, response="ok"):
        super().__init__()
        self._response = response
        self.last_usage = ChatUsage(prompt_tokens=5, completion_tokens=3)

    def chat(self, user_message: str, *, system_prompt: str | None = None) -> str:
        return self._response


class FailProvider(BaseLLMProvider):
    def __init__(self, error: LLMError):
        super().__init__()
        self._error = error

    def chat(self, user_message: str, *, system_prompt: str | None = None) -> str:
        raise self._error


class TestFallbackProvider:
    def test_primary_succeeds_no_fallback(self):
        primary = FakeProvider("primary-result")
        secondary = FakeProvider("secondary-result")

        fb = FallbackProvider([primary, secondary])
        result = fb.chat("질문")

        assert result == "primary-result"
        assert fb.last_provider_index == 0

    def test_transient_error_falls_through_to_secondary(self):
        primary = FailProvider(LLMTimeoutError("timeout"))
        secondary = FakeProvider("secondary-result")

        fb = FallbackProvider([primary, secondary])
        result = fb.chat("질문")

        assert result == "secondary-result"
        assert fb.last_provider_index == 1

    def test_connection_error_falls_through(self):
        primary = FailProvider(LLMConnectionError("unreachable"))
        secondary = FakeProvider("backup")

        fb = FallbackProvider([primary, secondary])
        result = fb.chat("질문")

        assert result == "backup"

    def test_non_transient_error_does_not_fallback(self):
        primary = FailProvider(LLMError("permanent"))
        secondary = FakeProvider("should-not-reach")

        fb = FallbackProvider([primary, secondary])
        with pytest.raises(LLMError, match="permanent"):
            fb.chat("질문")

    def test_all_providers_fail_raises_last_error(self):
        p1 = FailProvider(LLMTimeoutError("first"))
        p2 = FailProvider(LLMConnectionError("second"))

        fb = FallbackProvider([p1, p2])
        with pytest.raises(LLMConnectionError, match="second"):
            fb.chat("질문")

    def test_usage_propagates_from_successful_provider(self):
        primary = FailProvider(LLMTimeoutError("timeout"))
        secondary = FakeProvider("ok")
        secondary.last_usage = ChatUsage(prompt_tokens=20, completion_tokens=10)

        fb = FallbackProvider([primary, secondary])
        fb.chat("질문")

        assert fb.last_usage.prompt_tokens == 20
        assert fb.last_usage.completion_tokens == 10

    def test_empty_providers_raises_value_error(self):
        with pytest.raises(ValueError, match="At least one"):
            FallbackProvider([])

    def test_passes_system_prompt_through(self):
        class RecordingProvider(BaseLLMProvider):
            def __init__(self):
                super().__init__()
                self.received_system_prompt = None

            def chat(self, user_message, *, system_prompt=None):
                self.received_system_prompt = system_prompt
                return "ok"

        provider = RecordingProvider()
        fb = FallbackProvider([provider])
        fb.chat("질문", system_prompt="시스템")

        assert provider.received_system_prompt == "시스템"
