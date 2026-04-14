"""Tests for the FastAPI API server."""

from unittest.mock import AsyncMock, MagicMock

from conftest import make_settings
from fastapi.testclient import TestClient

from interfaces.api_server import create_api_app
from schemas.research import AgentResult, ResearchResponse
from services.shared import AppContext


def _mock_ctx() -> AppContext:
    settings = make_settings()
    supervisor = MagicMock()
    store = MagicMock()
    return AppContext(settings=settings, supervisor=supervisor, store=store)


def _mock_response(request_id="abc123") -> ResearchResponse:
    return ResearchResponse(
        request_id=request_id,
        summary="요약",
        comparison="비교",
        next_actions="행동",
        sources="출처",
        agent_results=[
            AgentResult(
                agent_name="research",
                output="ok",
                elapsed_seconds=1.0,
                success=True,
                prompt_tokens=10,
                completion_tokens=5,
            )
        ],
        total_elapsed_seconds=3.0,
    )


class TestChatEndpoint:
    def test_chat_auto_provider(self):
        ctx = _mock_ctx()
        provider = MagicMock()
        provider.chat.return_value = "답변"
        provider.last_usage = MagicMock(prompt_tokens=10, completion_tokens=5)
        provider.last_provider_name = "ollama"
        provider.name = "fallback"
        ctx.supervisor._provider = provider

        client = TestClient(create_api_app(ctx))
        resp = client.post("/api/chat", json={"message": "질문"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["response"] == "답변"
        assert data["prompt_tokens"] == 10
        assert data["provider_requested"] == "auto"
        assert data["provider_used"] == "ollama"

    def test_chat_unknown_provider_returns_400(self):
        ctx = _mock_ctx()
        client = TestClient(create_api_app(ctx))
        resp = client.post("/api/chat", json={"message": "질문", "provider": "groq"})

        assert resp.status_code == 400


class TestResearchEndpoint:
    def test_research_success(self):
        ctx = _mock_ctx()
        ctx.supervisor.handle = AsyncMock(return_value=_mock_response())

        client = TestClient(create_api_app(ctx))
        resp = client.post("/api/research", json={"query": "테스트 주제"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"] == "요약"
        assert data["total_tokens"] == 15
        ctx.store.save.assert_called_once()


class TestFollowupEndpoint:
    def test_followup_no_history_returns_404(self):
        ctx = _mock_ctx()
        ctx.store.get_latest.return_value = None

        client = TestClient(create_api_app(ctx))
        resp = client.post("/api/followup", json={"question": "후속"})

        assert resp.status_code == 404

    def test_followup_with_history(self):
        ctx = _mock_ctx()
        record = MagicMock()
        record.query = "원래 주제"
        record.request_id = "prev123"
        record.summary = "요약"
        record.comparison = "비교"
        record.next_actions = "행동"
        ctx.store.get_latest.return_value = record
        ctx.supervisor.handle = AsyncMock(return_value=_mock_response())

        client = TestClient(create_api_app(ctx))
        resp = client.post("/api/followup", json={"question": "후속 질문"})

        assert resp.status_code == 200


class TestHistoryEndpoint:
    def test_history_list(self):
        ctx = _mock_ctx()
        record = MagicMock()
        record.id = 1
        record.query = "주제"
        record.created_at = "2026-04-12"
        ctx.store.list_recent.return_value = [record]
        ctx.store.count.return_value = 1

        client = TestClient(create_api_app(ctx))
        resp = client.get("/api/history")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["records"]) == 1

    def test_history_by_id(self):
        ctx = _mock_ctx()
        record = MagicMock()
        record.id = 5
        record.query = "주제"
        record.summary = "요약"
        record.comparison = "비교"
        record.next_actions = "행동"
        record.sources = "출처"
        record.created_at = "2026-04-12"
        ctx.store.get_by_id.return_value = record

        client = TestClient(create_api_app(ctx))
        resp = client.get("/api/history", params={"record_id": 5})

        assert resp.status_code == 200
        assert resp.json()["id"] == 5

    def test_history_by_id_not_found(self):
        ctx = _mock_ctx()
        ctx.store.get_by_id.return_value = None

        client = TestClient(create_api_app(ctx))
        resp = client.get("/api/history", params={"record_id": 999})

        assert resp.status_code == 404


class TestProvidersEndpoint:
    def test_providers_default(self):
        ctx = _mock_ctx()
        client = TestClient(create_api_app(ctx))
        resp = client.get("/api/providers")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["name"] == "ollama"
