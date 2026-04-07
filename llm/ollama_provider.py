import logging

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from config import Settings
from llm.base import BaseLLMProvider, ChatUsage, LLMConnectionError, LLMError, LLMTimeoutError

LOGGER = logging.getLogger(__name__)

_PROOFREAD_PROMPT = (
    "당신은 한국어 교정기다. 의미를 바꾸지 말고 맞춤법, 띄어쓰기, "
    "어색한 조사와 어미만 자연스럽게 고쳐라. 설명 없이 수정된 문장만 출력하라."
)


class OllamaProvider(BaseLLMProvider):
    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.client = OpenAI(
            base_url=settings.ollama_base_url,
            api_key=settings.ollama_api_key,
        )
        self.model = settings.ollama_model
        self.timeout_seconds = settings.ollama_timeout_seconds
        self.system_prompt = settings.system_prompt
        self.enable_proofread = settings.enable_proofread

    def chat(self, user_message: str, *, system_prompt: str | None = None) -> str:
        prompt = system_prompt if system_prompt is not None else self.system_prompt

        content = self._complete(
            [
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.1,
        )

        if system_prompt is not None or not self.enable_proofread:
            return content

        corrected = self._complete(
            [
                {"role": "system", "content": _PROOFREAD_PROMPT},
                {"role": "user", "content": content},
            ],
            temperature=0,
        )
        return corrected or content

    def _complete(self, messages: list[dict[str, str]], temperature: float) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                timeout=self.timeout_seconds,
            )
        except APITimeoutError as exc:
            LOGGER.warning(
                "Ollama request timed out after %s seconds",
                self.timeout_seconds,
                exc_info=exc,
            )
            raise LLMTimeoutError("Ollama 응답이 제한 시간을 넘겼습니다.") from exc
        except APIConnectionError as exc:
            LOGGER.exception("Ollama connection failed")
            raise LLMConnectionError(
                "Ollama 서버에 연결하지 못했습니다. `ollama serve` 상태를 확인하세요."
            ) from exc
        except APIStatusError as exc:
            LOGGER.exception("Ollama returned an API error status=%s", exc.status_code)
            raise LLMError(f"Ollama 요청이 실패했습니다. status={exc.status_code}") from exc
        except Exception as exc:
            LOGGER.exception("Unexpected Ollama failure")
            raise LLMError("Ollama 요청 처리 중 오류가 발생했습니다.") from exc

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
            LOGGER.error("Ollama returned an empty response")
            raise LLMError("Ollama 응답이 비어 있습니다.")
        return content.strip()
