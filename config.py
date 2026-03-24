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
    system_prompt: str
    enable_proofread: bool
    max_reply_chars: int


def load_settings() -> Settings:
    token = _required_env("DISCORD_BOT_TOKEN")
    return Settings(
        discord_bot_token=token,
        command_prefix=os.getenv("COMMAND_PREFIX", "!"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        llm_provider=os.getenv("LLM_PROVIDER", "ollama").lower(),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        ollama_api_key=os.getenv("OLLAMA_API_KEY", "ollama"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2"),
        system_prompt=os.getenv(
            "SYSTEM_PROMPT",
            "You are a practical personal AI assistant. Respond clearly and concisely.",
        ),
        enable_proofread=_bool_env("ENABLE_PROOFREAD", True),
        max_reply_chars=_int_env("MAX_REPLY_CHARS", 1900),
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


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default

    try:
        parsed = int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc

    if parsed < 200:
        raise RuntimeError(f"{name} must be at least 200")
    return parsed
