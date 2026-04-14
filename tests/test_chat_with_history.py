"""Tests for chat_with_history across providers."""

from unittest.mock import MagicMock, patch

from conftest import make_settings

from llm.base import BaseLLMProvider, LLMConnectionError
from llm.claude_cli_provider import ClaudeCLIProvider
from llm.fallback_provider import FallbackProvider
from llm.ollama_provider import OllamaProvider


class _Echo(BaseLLMProvider):
    name = "echo"

    def chat(self, user_message, *, system_prompt=None):
        self.last_user_message = user_message
        return "ok"


class TestBaseDefault:
    def test_no_history_calls_chat_directly(self):
        p = _Echo()
        p.chat_with_history([], "hello")
        assert p.last_user_message == "hello"

    def test_stitches_history_into_prompt(self):
        p = _Echo()
        history = [
            {"role": "user", "content": "이름이 뭐야"},
            {"role": "assistant", "content": "Claude예요"},
        ]
        p.chat_with_history(history, "그럼 나이는?")
        stitched = p.last_user_message
        assert "User: 이름이 뭐야" in stitched
        assert "Assistant: Claude예요" in stitched
        assert "User: 그럼 나이는?" in stitched
        assert stitched.endswith("Assistant:")


class TestOllamaNative:
    @patch("llm.ollama_provider.OpenAI")
    def test_passes_messages_array(self, mock_openai):
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="응답"))]
        mock_response.usage = None
        mock_client.chat.completions.create.return_value = mock_response

        provider = OllamaProvider(make_settings())
        history = [
            {"role": "user", "content": "안녕"},
            {"role": "assistant", "content": "반가워요"},
        ]
        result = provider.chat_with_history(history, "오늘 날씨는?")

        assert result == "응답"
        sent = mock_client.chat.completions.create.call_args.kwargs["messages"]
        assert sent[0]["role"] == "system"
        assert sent[1] == {"role": "user", "content": "안녕"}
        assert sent[2] == {"role": "assistant", "content": "반가워요"}
        assert sent[3] == {"role": "user", "content": "오늘 날씨는?"}


class TestCLIInheritsDefault:
    @patch("llm.claude_cli_provider.subprocess.run")
    def test_claude_cli_uses_stitched_prompt(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="응답", stderr="")
        provider = ClaudeCLIProvider(make_settings(claude_cli_enabled=True))

        history = [{"role": "user", "content": "이전"}]
        provider.chat_with_history(history, "다음")

        cmd = mock_run.call_args[0][0]
        prompt = cmd[2]
        assert "User: 이전" in prompt
        assert "User: 다음" in prompt


class TestFallbackChain:
    def test_chat_with_history_falls_back_on_transient(self):
        bad = MagicMock(spec=BaseLLMProvider)
        bad.name = "bad"
        bad.chat_with_history.side_effect = LLMConnectionError("down")

        good = MagicMock(spec=BaseLLMProvider)
        good.name = "good"
        good.chat_with_history.return_value = "ok"
        good.last_usage = MagicMock()

        chain = FallbackProvider([bad, good])
        result = chain.chat_with_history([], "hi")
        assert result == "ok"
        assert chain.last_provider_name == "good"
