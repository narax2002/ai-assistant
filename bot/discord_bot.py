import asyncio
import logging

import discord
from discord.ext import commands

from config import Settings
from services.router import get_llm_provider

LOGGER = logging.getLogger(__name__)


def create_bot(settings: Settings) -> commands.Bot:
    llm = get_llm_provider(settings)

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
            await ctx.send(
                f"Usage: {settings.command_prefix}{ctx.command.qualified_name} <question>"
            )
            return

        LOGGER.exception(
            "Command '%s' failed", getattr(ctx.command, "qualified_name", "unknown"), exc_info=error
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
            except Exception:
                LOGGER.exception("LLM request failed")
                await ctx.send("The assistant could not generate a response.")
                return

        for chunk in _chunk_text(response, settings.max_reply_chars):
            await ctx.send(chunk)

    return bot


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
