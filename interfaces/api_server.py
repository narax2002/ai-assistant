"""FastAPI server for the LLM gateway and research pipeline."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from fastapi import FastAPI, HTTPException, Query

from schemas.api import (
    ChatRequest,
    ChatResponse,
    FollowupAPIRequest,
    ProviderStatus,
    ResearchAPIRequest,
    ResearchAPIResponse,
)
from schemas.research import ResearchRequest
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

    return app
