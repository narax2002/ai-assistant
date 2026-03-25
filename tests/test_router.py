import pytest

from config import Settings
from llm.ollama_provider import OllamaProvider
from services.router import get_llm_provider


def _settings(**overrides: object) -> Settings:
    data = {
        "discord_bot_token": "token",
        "command_prefix": "!",
        "log_level": "INFO",
        "llm_provider": "ollama",
        "ollama_base_url": "http://localhost:11434/v1",
        "ollama_api_key": "ollama",
        "ollama_model": "qwen2.5:7b",
        "ollama_timeout_seconds": 60,
        "system_prompt": "test prompt",
        "enable_proofread": True,
        "enable_google_calendar": False,
        "max_reply_chars": 1900,
        "google_calendar_credentials_path": "data/credentials.json",
        "google_calendar_token_path": "data/token.json",
        "google_calendar_id": "primary",
    }
    data.update(overrides)
    return Settings(**data)


def test_get_llm_provider_returns_ollama_provider() -> None:
    provider = get_llm_provider(_settings())

    assert isinstance(provider, OllamaProvider)


def test_get_llm_provider_rejects_unsupported_provider() -> None:
    with pytest.raises(RuntimeError, match="Unsupported LLM_PROVIDER"):
        get_llm_provider(_settings(llm_provider="groq"))
