import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import Settings  # noqa: E402

_SETTINGS_DEFAULTS = {
    "discord_bot_token": "token",
    "command_prefix": "!",
    "log_level": "INFO",
    "llm_provider": "ollama",
    "ollama_base_url": "http://localhost:11434/v1",
    "ollama_api_key": "ollama",
    "ollama_model": "gemma3:4b",
    "ollama_timeout_seconds": 60,
    "system_prompt": "test prompt",
    "enable_proofread": True,
    "enable_google_calendar": False,
    "max_reply_chars": 1900,
    "google_calendar_credentials_path": "data/credentials.json",
    "google_calendar_token_path": "data/token.json",
    "google_calendar_id": "primary",
    "history_db_path": ":memory:",
    "max_history_records": 200,
    "max_history_size_mb": 50,
    "discord_dev_guild_id": "",
    # OpenAI API provider
    "openai_api_key": "",
    "openai_model": "gpt-4o-mini",
    "openai_timeout_seconds": 60,
    # Claude API provider
    "claude_api_key": "",
    "claude_model": "claude-haiku-4-5-20251001",
    "claude_timeout_seconds": 60,
    # Claude CLI provider
    "claude_cli_enabled": False,
    "claude_cli_path": "claude",
    "claude_cli_timeout_seconds": 120,
    # Codex CLI provider
    "codex_cli_enabled": False,
    "codex_cli_path": "codex",
    "codex_cli_timeout_seconds": 120,
}


def make_settings(**overrides: object) -> Settings:
    """Create a Settings instance with sensible test defaults."""
    data = {**_SETTINGS_DEFAULTS, **overrides}
    return Settings(**data)


@pytest.fixture()
def settings() -> Settings:
    return make_settings()
