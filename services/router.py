import logging

from config import Settings
from llm.base import BaseLLMProvider
from llm.ollama_provider import OllamaProvider

LOGGER = logging.getLogger(__name__)


def get_llm_provider(settings: Settings) -> BaseLLMProvider:
    if settings.llm_provider != "ollama":
        raise RuntimeError("Unsupported LLM_PROVIDER. Phase 1 currently supports only 'ollama'.")

    LOGGER.info("Using LLM provider=%s model=%s", settings.llm_provider, settings.ollama_model)
    return OllamaProvider(settings)
