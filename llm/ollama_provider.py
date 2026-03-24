from openai import OpenAI

from config import Settings
from llm.base import BaseLLMProvider

_PROOFREAD_PROMPT = (
    "당신은 한국어 교정기다. 의미를 바꾸지 말고 맞춤법, 띄어쓰기, "
    "어색한 조사와 어미만 자연스럽게 고쳐라. 설명 없이 수정된 문장만 출력하라."
)


class OllamaProvider(BaseLLMProvider):
    def __init__(self, settings: Settings) -> None:
        self.client = OpenAI(
            base_url=settings.ollama_base_url,
            api_key=settings.ollama_api_key,
        )
        self.model = settings.ollama_model
        self.system_prompt = settings.system_prompt
        self.enable_proofread = settings.enable_proofread

    def chat(self, user_message: str) -> str:
        content = self._complete(
            [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.1,
        )

        if not self.enable_proofread:
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
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )

        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("Ollama returned an empty response")
        return content.strip()
