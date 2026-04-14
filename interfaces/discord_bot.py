"""Discord slash-command interface for the research assistant."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands

from config import Settings
from llm.base import LLMError
from schemas.research import ResearchRequest
from services.auto_title import maybe_generate_title
from services.router import get_provider_by_name
from utils.text import chunk_text

if TYPE_CHECKING:
    from services.shared import AppContext

LOGGER = logging.getLogger(__name__)


def create_research_bot(ctx: AppContext) -> discord.Client:
    settings = ctx.settings
    supervisor = ctx.supervisor
    store = ctx.store
    conversations = ctx.conversations

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)

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

    @tree.command(name="chat", description="단일 메시지 채팅 (프로바이더 선택 가능)")
    @app_commands.describe(
        message="메시지",
        provider="사용할 프로바이더 (기본: auto)",
    )
    @app_commands.choices(
        provider=[
            app_commands.Choice(name="auto (fallback 체인)", value="auto"),
            app_commands.Choice(name="ollama", value="ollama"),
            app_commands.Choice(name="claude-cli", value="claude-cli"),
            app_commands.Choice(name="codex-cli", value="codex-cli"),
        ]
    )
    async def chat(
        interaction: discord.Interaction,
        message: str,
        provider: app_commands.Choice[str] | None = None,
    ) -> None:
        await interaction.response.defer()

        provider_name = provider.value if provider else "auto"
        try:
            if provider_name == "auto":
                llm = supervisor._provider
            else:
                llm = get_provider_by_name(provider_name, settings)
        except RuntimeError as exc:
            await interaction.followup.send(f"오류: {exc}")
            return

        try:
            result = await asyncio.to_thread(llm.chat, message)
        except LLMError as exc:
            await interaction.followup.send(f"오류: {exc}")
            return
        except Exception:
            LOGGER.exception("Unexpected error in chat handler")
            await interaction.followup.send("채팅 처리 중 오류가 발생했습니다.")
            return

        used = getattr(llm, "last_provider_name", llm.name)
        echo = f"> `/chat` message: **{message}** | provider: **{provider_name}**"
        text = f"{echo}\n\n{result}\n\n_— {used}_"
        for chunk in chunk_text(text, settings.max_reply_chars):
            await interaction.followup.send(chunk)

    conv_group = app_commands.Group(name="conv", description="스레드 기반 연속 대화")
    tree.add_command(conv_group)

    _PROVIDER_CHOICES = [
        app_commands.Choice(name="auto (fallback 체인)", value="auto"),
        app_commands.Choice(name="ollama", value="ollama"),
        app_commands.Choice(name="claude-cli", value="claude-cli"),
        app_commands.Choice(name="codex-cli", value="codex-cli"),
    ]

    @conv_group.command(name="start", description="새 대화 스레드를 엽니다")
    @app_commands.describe(title="대화 제목 (선택)")
    async def conv_start(interaction: discord.Interaction, title: str | None = None) -> None:
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "스레드는 일반 텍스트 채널에서만 만들 수 있습니다."
            )
            return

        thread_name = title or f"chat-{interaction.user.display_name}"
        try:
            thread = await channel.create_thread(
                name=thread_name[:100],
                type=discord.ChannelType.public_thread,
                auto_archive_duration=1440,
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "스레드 생성 권한이 없습니다. 봇 권한을 확인해주세요."
            )
            return

        conv = conversations.create(
            platform="discord",
            session_id=str(thread.id),
            title=title,
        )
        await thread.send(
            f"새 대화를 시작했습니다 (#{conv.id}). "
            "`/conv send` 로 이어가거나 `/conv rename` 으로 이름을 바꿀 수 있습니다."
        )
        await interaction.response.send_message(f"스레드를 만들었습니다: {thread.mention}")

    @conv_group.command(name="send", description="현재 스레드의 대화에 메시지를 보냅니다")
    @app_commands.describe(
        message="메시지",
        provider="사용할 프로바이더 (기본: auto)",
    )
    @app_commands.choices(provider=_PROVIDER_CHOICES)
    async def conv_send(
        interaction: discord.Interaction,
        message: str,
        provider: app_commands.Choice[str] | None = None,
    ) -> None:
        channel = interaction.channel
        if not isinstance(channel, discord.Thread):
            await interaction.response.send_message(
                "`/conv send` 는 `/conv start` 로 만든 스레드 안에서 실행하세요."
            )
            return

        conv = conversations.get_by_session(str(channel.id))
        if conv is None:
            await interaction.response.send_message(
                "이 스레드에 연결된 대화가 없습니다. `/conv start` 로 다시 시작해주세요."
            )
            return

        await interaction.response.defer()

        provider_name = provider.value if provider else "auto"
        try:
            if provider_name == "auto":
                llm = supervisor._provider
            else:
                llm = get_provider_by_name(provider_name, settings)
        except RuntimeError as exc:
            await interaction.followup.send(f"오류: {exc}")
            return

        prior = conversations.list_messages(conv.id, limit=settings.chat_history_turns * 2)
        history = [{"role": m.role, "content": m.content} for m in prior]

        conversations.append_message(conv.id, "user", message)

        try:
            result = await asyncio.to_thread(llm.chat_with_history, history, message)
        except LLMError as exc:
            await interaction.followup.send(f"오류: {exc}")
            return
        except Exception:
            LOGGER.exception("Unexpected error in conv send")
            await interaction.followup.send("대화 처리 중 오류가 발생했습니다.")
            return

        used = getattr(llm, "last_provider_name", llm.name)
        conversations.append_message(conv.id, "assistant", result, provider_used=used)

        asyncio.create_task(maybe_generate_title(conversations, supervisor._provider, conv.id))

        echo = f"> **{interaction.user.display_name}**: {message}"
        text = f"{echo}\n\n{result}\n\n_— {used}_"
        for chunk in chunk_text(text, settings.max_reply_chars):
            await interaction.followup.send(chunk)

    @conv_group.command(name="list", description="최근 대화 목록을 보여줍니다")
    async def conv_list(interaction: discord.Interaction) -> None:
        rows = conversations.list_recent(limit=20, platform="discord")
        if not rows:
            await interaction.response.send_message("Discord 대화가 없습니다.")
            return
        lines = ["**최근 대화**\n"]
        for c in rows:
            title = c.title or "(제목 없음)"
            lines.append(f"`#{c.id}` <#{c.session_id}> — {title}")
        await interaction.response.send_message("\n".join(lines))

    @conv_group.command(name="rename", description="현재 스레드 대화의 이름을 바꿉니다")
    @app_commands.describe(title="새 제목")
    async def conv_rename(interaction: discord.Interaction, title: str) -> None:
        channel = interaction.channel
        if not isinstance(channel, discord.Thread):
            await interaction.response.send_message(
                "`/conv rename` 은 대화 스레드 안에서 실행하세요."
            )
            return
        conv = conversations.get_by_session(str(channel.id))
        if conv is None:
            await interaction.response.send_message("이 스레드에 연결된 대화가 없습니다.")
            return

        conversations.rename(conv.id, title, locked=True)
        try:
            await channel.edit(name=title[:100])
        except discord.Forbidden:
            pass
        await interaction.response.send_message(f"이름을 **{title}** 로 변경했습니다.")

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

        store.save(request, response)

        text = response.format_discord()
        total_tokens = sum(r.prompt_tokens + r.completion_tokens for r in response.agent_results)
        stats = f"처리 시간: {response.total_elapsed_seconds}s"
        if total_tokens:
            stats += f" | 토큰: {total_tokens}"
        text += f"\n\n_{stats}_"

        for chunk in chunk_text(text, settings.max_reply_chars):
            await interaction.followup.send(chunk)

    @tree.command(name="history", description="이전 리서치 기록을 조회합니다")
    @app_commands.describe(
        search="검색 키워드 (선택)",
        record_id="상세 조회할 기록 번호 (선택)",
        page="페이지 번호 (기본: 1)",
        delete_id="삭제할 기록 번호 (선택)",
        clear_all="True로 설정하면 전체 기록을 삭제합니다",
    )
    async def history(
        interaction: discord.Interaction,
        search: str | None = None,
        record_id: int | None = None,
        page: int = 1,
        delete_id: int | None = None,
        clear_all: bool = False,
    ) -> None:
        # Delete all records
        if clear_all:
            deleted = store.delete_all()
            await interaction.response.send_message(f"전체 기록 {deleted}건을 삭제했습니다.")
            return

        # Delete a single record
        if delete_id is not None:
            if store.delete(delete_id):
                await interaction.response.send_message(f"기록 #{delete_id}을 삭제했습니다.")
            else:
                await interaction.response.send_message(f"기록 #{delete_id}을 찾을 수 없습니다.")
            return

        # Show a single record
        if record_id is not None:
            record = store.get_by_id(record_id)
            if record is None:
                await interaction.response.send_message(f"기록 #{record_id}을 찾을 수 없습니다.")
                return
            text = f"**기록 #{record.id}** | {record.created_at}\n"
            text += f"**주제:** {record.query}\n\n"
            text += record.format_discord()
            for chunk in chunk_text(text, settings.max_reply_chars):
                await interaction.response.send_message(chunk)
            return

        # List records
        limit = 10
        offset = (max(page, 1) - 1) * limit
        records = store.list_recent(limit=limit, offset=offset, search=search)
        total = store.count(search=search)

        if not records:
            await interaction.response.send_message("리서치 기록이 없습니다.")
            return

        total_pages = (total + limit - 1) // limit
        lines = [f"**리서치 기록** (페이지 {page}/{total_pages})\n"]
        for r in records:
            query_short = r.query[:50] + ("..." if len(r.query) > 50 else "")
            lines.append(f"`#{r.id}` [{r.created_at}] {query_short}")

        lines.append("\n`/history record_id:번호` 로 상세 결과를 확인하세요.")
        await interaction.response.send_message("\n".join(lines))

    @tree.command(name="followup", description="이전 리서치에 이어서 후속 질문합니다")
    @app_commands.describe(
        question="후속 질문",
        request_id="이어갈 리서치의 request_id (선택, 기본: 가장 최근)",
    )
    async def followup(
        interaction: discord.Interaction,
        question: str,
        request_id: str | None = None,
    ) -> None:
        if request_id:
            record = store.get_by_request_id(request_id)
        else:
            record = store.get_latest()

        if record is None:
            await interaction.response.send_message(
                "이전 리서치 결과가 없습니다. 먼저 /research를 사용해주세요."
            )
            return

        await interaction.response.defer()

        context_query = (
            f"이전 리서치 주제: {record.query}\n\n"
            f"이전 리서치 결과:\n"
            f"핵심 요약: {record.summary}\n"
            f"비교: {record.comparison}\n"
            f"다음 행동: {record.next_actions}\n\n"
            f"후속 질문: {question}"
        )

        request = ResearchRequest(
            query=question,
            followup_from=record.request_id,
        )
        LOGGER.info(
            "followup request=%s from=%s question=%s",
            request.request_id,
            record.request_id,
            question,
        )

        try:
            response = await supervisor.handle(
                ResearchRequest(
                    query=context_query,
                    request_id=request.request_id,
                    followup_from=record.request_id,
                )
            )
        except LLMError as exc:
            await interaction.followup.send(f"오류: {exc}")
            return
        except Exception:
            LOGGER.exception("Unexpected error in followup handler")
            await interaction.followup.send("후속 질문 처리 중 오류가 발생했습니다.")
            return

        # Save with the original question as query, not the full context
        store.save(
            ResearchRequest(
                query=question,
                request_id=request.request_id,
                followup_from=record.request_id,
            ),
            response,
        )

        header = f"_후속 질문 (이전: #{record.id} {record.query[:30]})_\n\n"
        text = header + response.format_discord()
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
