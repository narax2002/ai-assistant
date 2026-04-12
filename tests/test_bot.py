import asyncio

from conftest import make_settings

from bot.discord_bot import (
    _build_today_summary_prompt,
    _calendar_disabled_message,
    _chunk_text,
    _command_usage,
    create_bot,
)


class FakeContext:
    def __init__(self) -> None:
        self.messages: list[str] = []

    async def send(self, message: str) -> None:
        self.messages.append(message)


def test_chunk_text_prefers_newline_boundaries() -> None:
    text = "line1\nline2\nline3"

    chunks = _chunk_text(text, 8)

    assert chunks == ["line1", "line2", "line3"]


def test_command_usage_includes_prefix_and_signature() -> None:
    bot = create_bot(make_settings())
    command = bot.get_command("ask")

    usage = _command_usage("!", command)

    assert usage == "Usage: !ask <question>"


def test_build_today_summary_prompt_contains_events() -> None:
    events_text = "- 2026-03-25 09:00 | Standup"

    prompt = _build_today_summary_prompt(events_text)

    assert events_text in prompt
    assert "짧게 요약" in prompt


def test_schedule_command_returns_disabled_message_when_calendar_is_off() -> None:
    bot = create_bot(make_settings(enable_google_calendar=False))
    command = bot.get_command("schedule")
    ctx = FakeContext()

    asyncio.run(command.callback(ctx))

    assert ctx.messages == [_calendar_disabled_message()]


def test_today_command_returns_disabled_message_when_calendar_is_off() -> None:
    bot = create_bot(make_settings(enable_google_calendar=False))
    command = bot.get_command("today")
    ctx = FakeContext()

    asyncio.run(command.callback(ctx))

    assert ctx.messages == [_calendar_disabled_message()]
