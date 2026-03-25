import asyncio
import logging

import discord
from discord.ext import commands

from config import Settings
from llm.base import LLMError, LLMTimeoutError
from services.calendar_service import (
    CalendarRequestError,
    CalendarService,
    CalendarSetupError,
)
from services.router import get_llm_provider

LOGGER = logging.getLogger(__name__)


def create_bot(settings: Settings) -> commands.Bot:
    llm = get_llm_provider(settings)
    calendar_service = (
        CalendarService.from_settings(settings) if settings.enable_google_calendar else None
    )

    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(command_prefix=settings.command_prefix, intents=intents)

    @bot.event
    async def on_ready() -> None:
        if bot.user is not None:
            LOGGER.info("Logged in as %s", bot.user)

    @bot.event
    async def on_command_completion(ctx: commands.Context) -> None:
        LOGGER.info("Completed command '%s' from %s", ctx.command.qualified_name, ctx.author)

    @bot.event
    async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(_command_usage(settings.command_prefix, ctx.command))
            return

        LOGGER.exception(
            "Command '%s' failed",
            getattr(ctx.command, "qualified_name", "unknown"),
            exc_info=error,
        )
        await ctx.send("The command failed to run.")

    @bot.command(name="ping", help="Verify that the bot can receive and send messages")
    async def ping(ctx: commands.Context) -> None:
        await ctx.send("pong")

    @bot.command(name="ask", help="Send a prompt to the configured LLM provider")
    async def ask(ctx: commands.Context, *, question: str) -> None:
        async with ctx.typing():
            try:
                response = await asyncio.to_thread(llm.chat, question)
            except LLMTimeoutError as exc:
                await ctx.send(str(exc))
                return
            except LLMError as exc:
                await ctx.send(str(exc))
                return
            except Exception:
                LOGGER.exception("LLM request failed")
                await ctx.send("The assistant could not generate a response.")
                return

        await _send_text_chunks(ctx, response, settings.max_reply_chars)

    @bot.command(name="schedule", help="Show upcoming Google Calendar events")
    async def schedule(ctx: commands.Context) -> None:
        if calendar_service is None:
            await ctx.send(_calendar_disabled_message())
            return

        async with ctx.typing():
            try:
                response = await asyncio.to_thread(
                    calendar_service.format_upcoming_events,
                    5,
                )
            except CalendarSetupError as exc:
                await ctx.send(str(exc))
                return
            except CalendarRequestError:
                LOGGER.exception("Calendar request failed")
                await ctx.send("Google Calendar 일정을 불러오지 못했습니다.")
                return

        await _send_text_chunks(ctx, response, settings.max_reply_chars)

    @bot.command(name="today", help="Summarize today's Google Calendar events")
    async def today(ctx: commands.Context) -> None:
        if calendar_service is None:
            await ctx.send(_calendar_disabled_message())
            return

        async with ctx.typing():
            try:
                events_text = await asyncio.to_thread(
                    calendar_service.format_today_events,
                    10,
                )
            except CalendarSetupError as exc:
                await ctx.send(str(exc))
                return
            except CalendarRequestError:
                LOGGER.exception("Calendar request failed")
                await ctx.send("Google Calendar 일정을 불러오지 못했습니다.")
                return

            if events_text == "오늘 일정이 없습니다.":
                await ctx.send(events_text)
                return

            try:
                response = await asyncio.to_thread(
                    llm.chat,
                    _build_today_summary_prompt(events_text),
                )
            except LLMTimeoutError as exc:
                await ctx.send(str(exc))
                return
            except LLMError as exc:
                await ctx.send(str(exc))
                return
            except Exception:
                LOGGER.exception("LLM today summary failed")
                await ctx.send("오늘 일정 요약을 생성하지 못했습니다.")
                return

        await _send_text_chunks(ctx, response, settings.max_reply_chars)

    return bot


async def _send_text_chunks(ctx: commands.Context, text: str, limit: int) -> None:
    for chunk in _chunk_text(text, limit):
        await ctx.send(chunk)


def _command_usage(prefix: str, command: commands.Command | None) -> str:
    if command is None:
        return "Usage information is unavailable."

    signature = command.signature.strip()
    usage = f"Usage: {prefix}{command.qualified_name}"
    if signature:
        usage = f"{usage} {signature}"
    return usage


def _build_today_summary_prompt(events_text: str) -> str:
    return (
        "다음은 오늘의 Google Calendar 일정이다.\n"
        f"{events_text}\n\n"
        "오늘 일정을 짧게 요약하고, 시간 순서대로 정리해줘. "
        "중요한 일정과 주의할 점이 있으면 함께 알려줘."
    )


def _calendar_disabled_message() -> str:
    return (
        "Google Calendar 기능은 현재 비활성화되어 있습니다. "
        "로그인 흐름이 필요한 기능은 나중에 다시 추가할 예정입니다."
    )


def _chunk_text(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + limit, len(text))
        if end < len(text):
            split_at = text.rfind("\n", start, end)
            if split_at > start:
                end = split_at
        chunks.append(text[start:end].strip())
        start = end

    return [chunk for chunk in chunks if chunk]
