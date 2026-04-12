from unittest.mock import MagicMock, patch

import pytest
from conftest import make_settings

from llm.base import LLMConnectionError, LLMError, LLMTimeoutError
from llm.openai_provider import OpenAIProvider


def _make_provider(**overrides):
    return OpenAIProvider(make_settings(openai_api_key="sk-test", **overrides))


def _mock_response(content="hello", prompt_tokens=10, completion_tokens=5):
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    usage = MagicMock()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion_tokens
    response.usage = usage
    return response


class TestOpenAIProviderChat:
    @patch("llm.openai_provider.OpenAI")
    def test_returns_response_content(self, mock_cls):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response("답변입니다")

        provider = _make_provider()
        result = provider.chat("질문")

        assert result == "답변입니다"

    @patch("llm.openai_provider.OpenAI")
    def test_passes_system_prompt(self, mock_cls):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response()

        provider = _make_provider()
        provider.chat("질문", system_prompt="시스템")

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        assert messages[0] == {"role": "system", "content": "시스템"}
        assert messages[1] == {"role": "user", "content": "질문"}

    @patch("llm.openai_provider.OpenAI")
    def test_tracks_token_usage(self, mock_cls):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response(
            prompt_tokens=20, completion_tokens=10
        )

        provider = _make_provider()
        provider.chat("질문")

        assert provider.last_usage.prompt_tokens == 20
        assert provider.last_usage.completion_tokens == 10


class TestOpenAIProviderErrors:
    @patch("llm.openai_provider.OpenAI")
    def test_timeout_raises_llm_timeout(self, mock_cls):
        from openai import APITimeoutError

        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = APITimeoutError(request=MagicMock())

        provider = _make_provider()
        with pytest.raises(LLMTimeoutError):
            provider.chat("질문")

    @patch("llm.openai_provider.OpenAI")
    def test_connection_error_raises_llm_connection(self, mock_cls):
        from openai import APIConnectionError

        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = APIConnectionError(request=MagicMock())

        provider = _make_provider()
        with pytest.raises(LLMConnectionError):
            provider.chat("질문")

    @patch("llm.openai_provider.OpenAI")
    def test_empty_response_raises_llm_error(self, mock_cls):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response(content="")

        provider = _make_provider()
        with pytest.raises(LLMError, match="비어 있습니다"):
            provider.chat("질문")
