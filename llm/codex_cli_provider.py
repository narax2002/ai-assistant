import logging
import subprocess

from config import Settings
from llm.base import BaseLLMProvider, ChatUsage, LLMConnectionError, LLMError, LLMTimeoutError

LOGGER = logging.getLogger(__name__)


class CodexCLIProvider(BaseLLMProvider):
    name = "codex-cli"

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self._cli_path = settings.codex_cli_path
        self._timeout = settings.codex_cli_timeout_seconds

    def chat(self, user_message: str, *, system_prompt: str | None = None) -> str:
        # Codex CLI does not support --system-prompt; prepend to user message
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{user_message}"
        else:
            full_prompt = user_message

        cmd = [self._cli_path, "exec", "--skip-git-repo-check", full_prompt]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired as exc:
            LOGGER.warning("Codex CLI timed out after %ss", self._timeout)
            raise LLMTimeoutError("Codex CLI 응답이 제한 시간을 넘겼습니다.") from exc
        except FileNotFoundError as exc:
            LOGGER.exception("Codex CLI not found at %s", self._cli_path)
            raise LLMConnectionError(f"Codex CLI를 찾을 수 없습니다: {self._cli_path}") from exc
        except Exception as exc:
            LOGGER.exception("Unexpected Codex CLI failure")
            raise LLMError("Codex CLI 요청 처리 중 오류가 발생했습니다.") from exc

        if result.returncode != 0:
            LOGGER.error("Codex CLI exited with code %d: %s", result.returncode, result.stderr)
            raise LLMError(f"Codex CLI 실행 실패 (exit={result.returncode})")

        content = result.stdout.strip()
        if not content:
            LOGGER.error("Codex CLI returned an empty response")
            raise LLMError("Codex CLI 응답이 비어 있습니다.")

        # CLI does not provide token usage
        self.last_usage = ChatUsage()
        return content
