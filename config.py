import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    discord_bot_token: str
    command_prefix: str
    log_level: str
    llm_provider: str
    ollama_base_url: str
    ollama_api_key: str
    ollama_model: str
    ollama_timeout_seconds: int
    system_prompt: str
    enable_proofread: bool
    enable_google_calendar: bool
    max_reply_chars: int
    google_calendar_credentials_path: str
    google_calendar_token_path: str
    google_calendar_id: str
    history_db_path: str
    max_history_records: int
    max_history_size_mb: int
    discord_dev_guild_id: str


def load_settings() -> Settings:
    token = _required_env("DISCORD_BOT_TOKEN")
    return Settings(
        discord_bot_token=token,
        command_prefix=os.getenv("COMMAND_PREFIX", "!"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        llm_provider=os.getenv("LLM_PROVIDER", "ollama").lower(),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        ollama_api_key=os.getenv("OLLAMA_API_KEY", "ollama"),
        ollama_model=os.getenv("OLLAMA_MODEL", "gemma3:4b"),
        ollama_timeout_seconds=_int_env("OLLAMA_TIMEOUT_SECONDS", 60, minimum=1),
        system_prompt=os.getenv(
            "SYSTEM_PROMPT",
            "You are a practical personal AI assistant. Respond clearly and concisely.",
        ),
        enable_proofread=_bool_env("ENABLE_PROOFREAD", True),
        enable_google_calendar=_bool_env("ENABLE_GOOGLE_CALENDAR", False),
        max_reply_chars=_int_env("MAX_REPLY_CHARS", 1900, minimum=200),
        google_calendar_credentials_path=os.getenv(
            "GOOGLE_CALENDAR_CREDENTIALS_PATH",
            "data/credentials.json",
        ),
        google_calendar_token_path=os.getenv(
            "GOOGLE_CALENDAR_TOKEN_PATH",
            "data/token.json",
        ),
        google_calendar_id=os.getenv("GOOGLE_CALENDAR_ID", "primary"),
        history_db_path=os.getenv("HISTORY_DB_PATH", "data/research_history.db"),
        max_history_records=_int_env("MAX_HISTORY_RECORDS", 200, minimum=1),
        max_history_size_mb=_int_env("MAX_HISTORY_SIZE_MB", 50, minimum=1),
        discord_dev_guild_id=os.getenv("DISCORD_DEV_GUILD_ID", ""),
    )


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"{name} must be true/false")


def _int_env(name: str, default: int, *, minimum: int | None = None) -> int:
    value = os.getenv(name)
    if value is None:
        return default

    try:
        parsed = int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc

    if minimum is not None and parsed < minimum:
        raise RuntimeError(f"{name} must be at least {minimum}")
    return parsed
