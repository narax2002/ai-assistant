"""FastAPI server for the LLM gateway and research pipeline."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from fastapi import FastAPI, HTTPException, Query

from schemas.api import (
    ChatRequest,
    ChatResponse,
    ConversationChatRequest,
    ConversationChatResponse,
    ConversationCreate,
    ConversationDetail,
    ConversationMessageOut,
    ConversationOut,
    ConversationRename,
    FollowupAPIRequest,
    ProviderStatus,
    ResearchAPIRequest,
    ResearchAPIResponse,
)
from schemas.research import ResearchRequest
from services.auto_title import maybe_generate_title
from services.router import get_provider_by_name, list_available_providers

if TYPE_CHECKING:
    from services.shared import AppContext

LOGGER = logging.getLogger(__name__)


def create_api_app(ctx: AppContext) -> FastAPI:
    app = FastAPI(title="AI Assistant LLM Gateway")

    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(req: ChatRequest) -> ChatResponse:
        if req.provider == "auto":
            provider = ctx.supervisor._provider
        else:
            try:
                provider = get_provider_by_name(req.provider, ctx.settings)
            except RuntimeError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

        try:
            result = await asyncio.to_thread(
                provider.chat, req.message, system_prompt=req.system_prompt
            )
        except Exception as exc:
            LOGGER.exception("Chat error")
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        usage = provider.last_usage
        provider_used = getattr(provider, "last_provider_name", provider.name)
        return ChatResponse(
            response=result,
            provider_requested=req.provider,
            provider_used=provider_used,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
        )

    @app.post("/api/research", response_model=ResearchAPIResponse)
    async def research(req: ResearchAPIRequest) -> ResearchAPIResponse:
        request = ResearchRequest(query=req.query)
        LOGGER.info("API research request=%s query=%s", request.request_id, req.query)

        try:
            response = await ctx.supervisor.handle(request)
        except Exception as exc:
            LOGGER.exception("Research error")
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        ctx.store.save(request, response)

        total_tokens = sum(r.prompt_tokens + r.completion_tokens for r in response.agent_results)
        return ResearchAPIResponse(
            request_id=response.request_id,
            summary=response.summary,
            comparison=response.comparison,
            next_actions=response.next_actions,
            sources=response.sources,
            total_elapsed_seconds=response.total_elapsed_seconds,
            total_tokens=total_tokens,
        )

    @app.post("/api/followup", response_model=ResearchAPIResponse)
    async def followup(req: FollowupAPIRequest) -> ResearchAPIResponse:
        if req.request_id:
            record = ctx.store.get_by_request_id(req.request_id)
        else:
            record = ctx.store.get_latest()

        if record is None:
            raise HTTPException(
                status_code=404,
                detail="이전 리서치 결과가 없습니다. 먼저 /api/research를 사용해주세요.",
            )

        context_query = (
            f"이전 리서치 주제: {record.query}\n\n"
            f"이전 리서치 결과:\n"
            f"핵심 요약: {record.summary}\n"
            f"비교: {record.comparison}\n"
            f"다음 행동: {record.next_actions}\n\n"
            f"후속 질문: {req.question}"
        )

        request = ResearchRequest(
            query=context_query,
            followup_from=record.request_id,
        )
        LOGGER.info(
            "API followup request=%s from=%s",
            request.request_id,
            record.request_id,
        )

        try:
            response = await ctx.supervisor.handle(request)
        except Exception as exc:
            LOGGER.exception("Followup error")
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        # Save with original question
        ctx.store.save(
            ResearchRequest(
                query=req.question,
                request_id=request.request_id,
                followup_from=record.request_id,
            ),
            response,
        )

        total_tokens = sum(r.prompt_tokens + r.completion_tokens for r in response.agent_results)
        return ResearchAPIResponse(
            request_id=response.request_id,
            summary=response.summary,
            comparison=response.comparison,
            next_actions=response.next_actions,
            sources=response.sources,
            total_elapsed_seconds=response.total_elapsed_seconds,
            total_tokens=total_tokens,
        )

    @app.get("/api/history")
    async def history(
        search: str | None = None,
        page: int = Query(default=1, ge=1),
        record_id: int | None = None,
    ) -> dict:
        if record_id is not None:
            record = ctx.store.get_by_id(record_id)
            if record is None:
                raise HTTPException(
                    status_code=404, detail=f"기록 #{record_id}을 찾을 수 없습니다."
                )
            return {
                "id": record.id,
                "query": record.query,
                "summary": record.summary,
                "comparison": record.comparison,
                "next_actions": record.next_actions,
                "sources": record.sources,
                "created_at": record.created_at,
            }

        limit = 10
        offset = (page - 1) * limit
        records = ctx.store.list_recent(limit=limit, offset=offset, search=search)
        total = ctx.store.count(search=search)
        total_pages = (total + limit - 1) // limit if total > 0 else 1

        return {
            "records": [
                {"id": r.id, "query": r.query, "created_at": r.created_at} for r in records
            ],
            "total": total,
            "page": page,
            "total_pages": total_pages,
        }

    @app.get("/api/providers", response_model=list[ProviderStatus])
    async def providers() -> list[ProviderStatus]:
        return [ProviderStatus(**p) for p in list_available_providers(ctx.settings)]

    # --- Conversations ---

    def _conv_to_out(c) -> ConversationOut:
        return ConversationOut(
            id=c.id,
            session_id=c.session_id,
            title=c.title,
            title_locked=c.title_locked,
            platform=c.platform,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )

    @app.post("/api/conversations", response_model=ConversationOut)
    async def create_conversation(req: ConversationCreate) -> ConversationOut:
        c = ctx.conversations.create(
            platform=req.platform,
            session_id=req.session_id,
            title=req.title,
        )
        return _conv_to_out(c)

    @app.get("/api/conversations", response_model=list[ConversationOut])
    async def list_conversations(
        platform: str | None = None,
        limit: int = Query(default=20, ge=1, le=200),
    ) -> list[ConversationOut]:
        rows = ctx.conversations.list_recent(limit=limit, platform=platform)
        return [_conv_to_out(c) for c in rows]

    @app.get("/api/conversations/{conversation_id}", response_model=ConversationDetail)
    async def get_conversation(conversation_id: int) -> ConversationDetail:
        c = ctx.conversations.get(conversation_id)
        if c is None:
            raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")
        messages = ctx.conversations.list_messages(conversation_id)
        return ConversationDetail(
            **_conv_to_out(c).model_dump(),
            messages=[
                ConversationMessageOut(
                    id=m.id,
                    role=m.role,
                    content=m.content,
                    provider_used=m.provider_used,
                    created_at=m.created_at,
                )
                for m in messages
            ],
        )

    @app.patch("/api/conversations/{conversation_id}", response_model=ConversationOut)
    async def rename_conversation(conversation_id: int, req: ConversationRename) -> ConversationOut:
        if not ctx.conversations.rename(conversation_id, req.title, locked=True):
            raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")
        c = ctx.conversations.get(conversation_id)
        return _conv_to_out(c)

    @app.delete("/api/conversations/{conversation_id}")
    async def delete_conversation(conversation_id: int) -> dict:
        if not ctx.conversations.delete(conversation_id):
            raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")
        return {"deleted": conversation_id}

    @app.post(
        "/api/conversations/{conversation_id}/chat",
        response_model=ConversationChatResponse,
    )
    async def chat_in_conversation(
        conversation_id: int, req: ConversationChatRequest
    ) -> ConversationChatResponse:
        conv = ctx.conversations.get(conversation_id)
        if conv is None:
            raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")

        if req.provider == "auto":
            provider = ctx.supervisor._provider
        else:
            try:
                provider = get_provider_by_name(req.provider, ctx.settings)
            except RuntimeError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

        prior = ctx.conversations.list_messages(
            conversation_id, limit=ctx.settings.chat_history_turns * 2
        )
        history = [{"role": m.role, "content": m.content} for m in prior]

        ctx.conversations.append_message(conversation_id, "user", req.message)

        try:
            result = await asyncio.to_thread(
                provider.chat_with_history,
                history,
                req.message,
                system_prompt=req.system_prompt,
            )
        except Exception as exc:
            LOGGER.exception("Conversation chat error")
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        used = getattr(provider, "last_provider_name", provider.name)
        stored = ctx.conversations.append_message(
            conversation_id, "assistant", result, provider_used=used
        )

        asyncio.create_task(
            maybe_generate_title(ctx.conversations, ctx.supervisor._provider, conversation_id)
        )

        return ConversationChatResponse(
            response=result,
            provider_requested=req.provider,
            provider_used=used,
            conversation_id=conversation_id,
            message_id=stored.id,
        )

    return app
