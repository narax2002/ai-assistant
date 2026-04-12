import logging

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from config import Settings
from llm.base import BaseLLMProvider, ChatUsage, LLMConnectionError, LLMError, LLMTimeoutError

LOGGER = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.timeout_seconds = settings.openai_timeout_seconds

    def chat(self, user_message: str, *, system_prompt: str | None = None) -> str:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,
                timeout=self.timeout_seconds,
            )
        except APITimeoutError as exc:
            LOGGER.warning("OpenAI request timed out after %ss", self.timeout_seconds)
            raise LLMTimeoutError("OpenAI 응답이 제한 시간을 넘겼습니다.") from exc
        except APIConnectionError as exc:
            LOGGER.exception("OpenAI connection failed")
            raise LLMConnectionError("OpenAI 서버에 연결하지 못했습니다.") from exc
        except APIStatusError as exc:
            LOGGER.exception("OpenAI API error status=%s", exc.status_code)
            raise LLMError(f"OpenAI 요청이 실패했습니다. status={exc.status_code}") from exc
        except Exception as exc:
            LOGGER.exception("Unexpected OpenAI failure")
            raise LLMError("OpenAI 요청 처리 중 오류가 발생했습니다.") from exc

        usage = response.usage
        if usage:
            self.last_usage = ChatUsage(
                prompt_tokens=usage.prompt_tokens or 0,
                completion_tokens=usage.completion_tokens or 0,
            )
            LOGGER.debug(
                "model=%s prompt_tokens=%d completion_tokens=%d",
                self.model,
                self.last_usage.prompt_tokens,
                self.last_usage.completion_tokens,
            )

        content = response.choices[0].message.content
        if not content:
            LOGGER.error("OpenAI returned an empty response")
            raise LLMError("OpenAI 응답이 비어 있습니다.")
        return content.strip()
