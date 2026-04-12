import subprocess
from unittest.mock import MagicMock, patch

import pytest
from conftest import make_settings

from llm.base import LLMConnectionError, LLMError, LLMTimeoutError
from llm.claude_cli_provider import ClaudeCLIProvider
from llm.codex_cli_provider import CodexCLIProvider

# --- Claude CLI ---


class TestClaudeCLIProvider:
    @patch("llm.claude_cli_provider.subprocess.run")
    def test_returns_stdout(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="답변\n", stderr="")

        provider = ClaudeCLIProvider(make_settings(claude_cli_enabled=True))
        result = provider.chat("질문")

        assert result == "답변"

    @patch("llm.claude_cli_provider.subprocess.run")
    def test_passes_system_prompt_flag(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

        provider = ClaudeCLIProvider(make_settings(claude_cli_enabled=True))
        provider.chat("질문", system_prompt="시스템")

        cmd = mock_run.call_args[0][0]
        assert "--system-prompt" in cmd
        idx = cmd.index("--system-prompt")
        assert cmd[idx + 1] == "시스템"

    @patch("llm.claude_cli_provider.subprocess.run")
    def test_timeout_raises_llm_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=120)

        provider = ClaudeCLIProvider(make_settings(claude_cli_enabled=True))
        with pytest.raises(LLMTimeoutError):
            provider.chat("질문")

    @patch("llm.claude_cli_provider.subprocess.run")
    def test_not_found_raises_llm_connection(self, mock_run):
        mock_run.side_effect = FileNotFoundError()

        provider = ClaudeCLIProvider(make_settings(claude_cli_enabled=True))
        with pytest.raises(LLMConnectionError):
            provider.chat("질문")

    @patch("llm.claude_cli_provider.subprocess.run")
    def test_nonzero_exit_raises_llm_error(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")

        provider = ClaudeCLIProvider(make_settings(claude_cli_enabled=True))
        with pytest.raises(LLMError, match="exit=1"):
            provider.chat("질문")

    @patch("llm.claude_cli_provider.subprocess.run")
    def test_empty_output_raises_llm_error(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        provider = ClaudeCLIProvider(make_settings(claude_cli_enabled=True))
        with pytest.raises(LLMError, match="비어 있습니다"):
            provider.chat("질문")


# --- Codex CLI ---


class TestCodexCLIProvider:
    @patch("llm.codex_cli_provider.subprocess.run")
    def test_returns_stdout(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="답변\n", stderr="")

        provider = CodexCLIProvider(make_settings(codex_cli_enabled=True))
        result = provider.chat("질문")

        assert result == "답변"

    @patch("llm.codex_cli_provider.subprocess.run")
    def test_prepends_system_prompt_to_message(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

        provider = CodexCLIProvider(make_settings(codex_cli_enabled=True))
        provider.chat("질문", system_prompt="시스템")

        cmd = mock_run.call_args[0][0]
        assert cmd[1] == "-q"
        assert cmd[2] == "시스템\n\n질문"

    @patch("llm.codex_cli_provider.subprocess.run")
    def test_timeout_raises_llm_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="codex", timeout=120)

        provider = CodexCLIProvider(make_settings(codex_cli_enabled=True))
        with pytest.raises(LLMTimeoutError):
            provider.chat("질문")

    @patch("llm.codex_cli_provider.subprocess.run")
    def test_not_found_raises_llm_connection(self, mock_run):
        mock_run.side_effect = FileNotFoundError()

        provider = CodexCLIProvider(make_settings(codex_cli_enabled=True))
        with pytest.raises(LLMConnectionError):
            provider.chat("질문")

    @patch("llm.codex_cli_provider.subprocess.run")
    def test_nonzero_exit_raises_llm_error(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")

        provider = CodexCLIProvider(make_settings(codex_cli_enabled=True))
        with pytest.raises(LLMError, match="exit=1"):
            provider.chat("질문")
