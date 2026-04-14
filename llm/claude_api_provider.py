import logging

import anthropic

from config import Settings
from llm.base import BaseLLMProvider, ChatUsage, LLMConnectionError, LLMError, LLMTimeoutError

LOGGER = logging.getLogger(__name__)


class ClaudeAPIProvider(BaseLLMProvider):
    name = "claude-api"

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.client = anthropic.Anthropic(api_key=settings.claude_api_key)
        self.model = settings.claude_model
        self.timeout_seconds = settings.claude_timeout_seconds

    def chat(self, user_message: str, *, system_prompt: str | None = None) -> str:
        kwargs: dict = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": user_message}],
            "timeout": self.timeout_seconds,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        try:
            response = self.client.messages.create(**kwargs)
        except anthropic.APITimeoutError as exc:
            LOGGER.warning("Claude API request timed out after %ss", self.timeout_seconds)
            raise LLMTimeoutError("Claude API 응답이 제한 시간을 넘겼습니다.") from exc
        except anthropic.APIConnectionError as exc:
            LOGGER.exception("Claude API connection failed")
            raise LLMConnectionError("Claude API 서버에 연결하지 못했습니다.") from exc
        except anthropic.APIStatusError as exc:
            LOGGER.exception("Claude API error status=%s", exc.status_code)
            raise LLMError(f"Claude API 요청이 실패했습니다. status={exc.status_code}") from exc
        except Exception as exc:
            LOGGER.exception("Unexpected Claude API failure")
            raise LLMError("Claude API 요청 처리 중 오류가 발생했습니다.") from exc

        usage = response.usage
        if usage:
            self.last_usage = ChatUsage(
                prompt_tokens=usage.input_tokens or 0,
                completion_tokens=usage.output_tokens or 0,
            )
            LOGGER.debug(
                "model=%s prompt_tokens=%d completion_tokens=%d",
                self.model,
                self.last_usage.prompt_tokens,
                self.last_usage.completion_tokens,
            )

        content = response.content[0].text if response.content else ""
        if not content:
            LOGGER.error("Claude API returned an empty response")
            raise LLMError("Claude API 응답이 비어 있습니다.")
        return content.strip()
