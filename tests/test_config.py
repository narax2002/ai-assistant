import pytest

from config import load_settings


def _reset_optional_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in [
        "COMMAND_PREFIX",
        "LOG_LEVEL",
        "LLM_PROVIDER",
        "OLLAMA_BASE_URL",
        "OLLAMA_API_KEY",
        "OLLAMA_MODEL",
        "OLLAMA_TIMEOUT_SECONDS",
        "SYSTEM_PROMPT",
        "ENABLE_PROOFREAD",
        "ENABLE_GOOGLE_CALENDAR",
        "MAX_REPLY_CHARS",
        "GOOGLE_CALENDAR_CREDENTIALS_PATH",
        "GOOGLE_CALENDAR_TOKEN_PATH",
        "GOOGLE_CALENDAR_ID",
    ]:
        monkeypatch.delenv(name, raising=False)


def _set_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
    _reset_optional_env(monkeypatch)
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "test-token")


def test_load_settings_uses_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required_env(monkeypatch)

    settings = load_settings()

    assert settings.llm_provider == "ollama"
    assert settings.ollama_model == "qwen2.5:7b"
    assert settings.ollama_timeout_seconds == 60
    assert settings.enable_google_calendar is False
    assert settings.max_reply_chars == 1900


def test_load_settings_reads_calendar_and_timeout_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required_env(monkeypatch)
    monkeypatch.setenv("ENABLE_GOOGLE_CALENDAR", "true")
    monkeypatch.setenv("OLLAMA_TIMEOUT_SECONDS", "15")

    settings = load_settings()

    assert settings.enable_google_calendar is True
    assert settings.ollama_timeout_seconds == 15


def test_load_settings_rejects_invalid_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required_env(monkeypatch)
    monkeypatch.setenv("OLLAMA_TIMEOUT_SECONDS", "0")

    with pytest.raises(RuntimeError, match="OLLAMA_TIMEOUT_SECONDS must be at least 1"):
        load_settings()
