from unittest.mock import MagicMock, patch

import pytest
from conftest import make_settings

from llm.base import LLMConnectionError, LLMError, LLMTimeoutError
from llm.claude_api_provider import ClaudeAPIProvider


def _make_provider(**overrides):
    return ClaudeAPIProvider(make_settings(claude_api_key="sk-ant-test", **overrides))


def _mock_response(text="hello", input_tokens=10, output_tokens=5):
    response = MagicMock()
    block = MagicMock()
    block.text = text
    response.content = [block]
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    response.usage = usage
    return response


class TestClaudeAPIProviderChat:
    @patch("llm.claude_api_provider.anthropic.Anthropic")
    def test_returns_response_content(self, mock_cls):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = _mock_response("답변입니다")

        provider = _make_provider()
        result = provider.chat("질문")

        assert result == "답변입니다"

    @patch("llm.claude_api_provider.anthropic.Anthropic")
    def test_passes_system_prompt_as_kwarg(self, mock_cls):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = _mock_response()

        provider = _make_provider()
        provider.chat("질문", system_prompt="시스템")

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["system"] == "시스템"
        assert call_kwargs["messages"] == [{"role": "user", "content": "질문"}]

    @patch("llm.claude_api_provider.anthropic.Anthropic")
    def test_no_system_kwarg_when_none(self, mock_cls):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = _mock_response()

        provider = _make_provider()
        provider.chat("질문")

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert "system" not in call_kwargs

    @patch("llm.claude_api_provider.anthropic.Anthropic")
    def test_tracks_token_usage(self, mock_cls):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = _mock_response(input_tokens=20, output_tokens=10)

        provider = _make_provider()
        provider.chat("질문")

        assert provider.last_usage.prompt_tokens == 20
        assert provider.last_usage.completion_tokens == 10


class TestClaudeAPIProviderErrors:
    @patch("llm.claude_api_provider.anthropic.Anthropic")
    def test_timeout_raises_llm_timeout(self, mock_cls):
        import anthropic

        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.side_effect = anthropic.APITimeoutError(request=MagicMock())

        provider = _make_provider()
        with pytest.raises(LLMTimeoutError):
            provider.chat("질문")

    @patch("llm.claude_api_provider.anthropic.Anthropic")
    def test_connection_error_raises_llm_connection(self, mock_cls):
        import anthropic

        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.side_effect = anthropic.APIConnectionError(request=MagicMock())

        provider = _make_provider()
        with pytest.raises(LLMConnectionError):
            provider.chat("질문")

    @patch("llm.claude_api_provider.anthropic.Anthropic")
    def test_empty_response_raises_llm_error(self, mock_cls):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        resp = MagicMock()
        resp.content = []
        resp.usage = MagicMock(input_tokens=0, output_tokens=0)
        mock_client.messages.create.return_value = resp

        provider = _make_provider()
        with pytest.raises(LLMError, match="비어 있습니다"):
            provider.chat("질문")
