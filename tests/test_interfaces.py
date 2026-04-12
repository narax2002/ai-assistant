import discord

from config import load_settings
from interfaces.discord_bot import create_research_bot
from services.shared import create_app_context
from utils.text import chunk_text


def test_chunk_text_short():
    assert chunk_text("hello", 100) == ["hello"]


def test_chunk_text_splits_on_newline():
    text = "line1\nline2\nline3"
    chunks = chunk_text(text, 10)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert len(chunk) <= 10


def test_chunk_text_empty():
    assert chunk_text("", 100) == [""]


def test_create_research_bot_returns_client(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    settings = load_settings()
    ctx = create_app_context(settings)
    client = create_research_bot(ctx)
    assert isinstance(client, discord.Client)
