"""Discord slash-command interface for the research assistant."""

import logging

import discord
from discord import app_commands

from agents.analyst_agent import AnalystAgent
from agents.research_agent import ResearchAgent
from agents.writer_agent import WriterAgent
from config import Settings
from llm.base import LLMError
from orchestrator.supervisor import Supervisor
from schemas.research import ResearchRequest
from services.router import get_llm_provider
from utils.text import chunk_text

LOGGER = logging.getLogger(__name__)


def create_research_bot(settings: Settings) -> discord.Client:
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)

    provider = get_llm_provider(settings)

    timeout = settings.ollama_timeout_seconds
    supervisor = Supervisor(
        research_agent=ResearchAgent(provider, timeout_seconds=timeout),
        analyst_agent=AnalystAgent(provider, timeout_seconds=timeout),
        writer_agent=WriterAgent(provider, timeout_seconds=timeout),
        provider=provider,
    )

    dev_guild = _dev_guild(settings)

    @client.event
    async def on_ready() -> None:
        if dev_guild is not None:
            tree.copy_global_to(guild=dev_guild)
            await tree.sync(guild=dev_guild)
            LOGGER.info("Synced slash commands to dev guild %s", dev_guild.id)
        else:
            await tree.sync()
            LOGGER.info("Synced slash commands globally")

        if client.user is not None:
            LOGGER.info("Logged in as %s", client.user)

    @tree.command(name="ping", description="봇 연결 상태를 확인합니다")
    async def ping(interaction: discord.Interaction) -> None:
        await interaction.response.send_message("pong")

    @tree.command(name="research", description="리서치 주제를 입력하면 분석 결과를 제공합니다")
    @app_commands.describe(query="리서치할 주제")
    async def research(interaction: discord.Interaction, query: str) -> None:
        await interaction.response.defer()

        request = ResearchRequest(query=query)
        LOGGER.info("research request=%s query=%s", request.request_id, query)

        try:
            response = await supervisor.handle(request)
        except LLMError as exc:
            await interaction.followup.send(f"오류: {exc}")
            return
        except Exception:
            LOGGER.exception("Unexpected error in research handler")
            await interaction.followup.send("리서치 처리 중 오류가 발생했습니다.")
            return

        text = response.format_discord()
        total_tokens = sum(r.prompt_tokens + r.completion_tokens for r in response.agent_results)
        stats = f"처리 시간: {response.total_elapsed_seconds}s"
        if total_tokens:
            stats += f" | 토큰: {total_tokens}"
        text += f"\n\n_{stats}_"

        for chunk in chunk_text(text, settings.max_reply_chars):
            await interaction.followup.send(chunk)

    return client


def _dev_guild(settings: Settings) -> discord.Object | None:
    guild_id = getattr(settings, "discord_dev_guild_id", None)
    if guild_id:
        return discord.Object(id=int(guild_id))
    return None
