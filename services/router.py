from config import Settings
from llm.base import BaseLLMProvider
from llm.ollama_provider import OllamaProvider


def get_llm_provider(settings: Settings) -> BaseLLMProvider:
    if settings.llm_provider != "ollama":
        raise RuntimeError("Unsupported LLM_PROVIDER. Phase 1 currently supports only 'ollama'.")
    return OllamaProvider(settings)
