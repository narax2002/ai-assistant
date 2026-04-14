import logging
import subprocess

from config import Settings
from llm.base import BaseLLMProvider, ChatUsage, LLMConnectionError, LLMError, LLMTimeoutError

LOGGER = logging.getLogger(__name__)


class ClaudeCLIProvider(BaseLLMProvider):
    name = "claude-cli"

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self._cli_path = settings.claude_cli_path
        self._timeout = settings.claude_cli_timeout_seconds

    def chat(self, user_message: str, *, system_prompt: str | None = None) -> str:
        cmd = [self._cli_path, "-p", user_message]
        if system_prompt:
            cmd.extend(["--system-prompt", system_prompt])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self._timeout)
        except subprocess.TimeoutExpired as exc:
            LOGGER.warning("Claude CLI timed out after %ss", self._timeout)
            raise LLMTimeoutError("Claude CLI 응답이 제한 시간을 넘겼습니다.") from exc
        except FileNotFoundError as exc:
            LOGGER.exception("Claude CLI not found at %s", self._cli_path)
            raise LLMConnectionError(f"Claude CLI를 찾을 수 없습니다: {self._cli_path}") from exc
        except Exception as exc:
            LOGGER.exception("Unexpected Claude CLI failure")
            raise LLMError("Claude CLI 요청 처리 중 오류가 발생했습니다.") from exc

        if result.returncode != 0:
            LOGGER.error("Claude CLI exited with code %d: %s", result.returncode, result.stderr)
            raise LLMError(f"Claude CLI 실행 실패 (exit={result.returncode})")

        content = result.stdout.strip()
        if not content:
            LOGGER.error("Claude CLI returned an empty response")
            raise LLMError("Claude CLI 응답이 비어 있습니다.")

        # CLI does not provide token usage
        self.last_usage = ChatUsage()
        return content
