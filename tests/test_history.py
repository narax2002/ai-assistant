"""Tests for storage/history.py."""

import os

import pytest

from schemas.research import ResearchRequest, ResearchResponse
from storage.history import HistoryStore


def _make_response(request_id: str = "req-001", **overrides) -> tuple:
    req = ResearchRequest(
        query=overrides.pop("query", "테스트 쿼리"),
        request_id=request_id,
        followup_from=overrides.pop("followup_from", None),
    )
    resp = ResearchResponse(
        request_id=request_id,
        summary=overrides.pop("summary", "요약 내용"),
        comparison=overrides.pop("comparison", "비교 내용"),
        next_actions=overrides.pop("next_actions", "행동 내용"),
        sources=overrides.pop("sources", "출처 내용"),
        agent_results=[],
        total_elapsed_seconds=overrides.pop("total_elapsed_seconds", 1.5),
    )
    return req, resp


@pytest.fixture()
def store(tmp_path):
    db_path = str(tmp_path / "test.db")
    s = HistoryStore(db_path)
    yield s
    s.close()


def test_save_and_get_latest(store):
    req, resp = _make_response()
    store.save(req, resp)
    record = store.get_latest()

    assert record is not None
    assert record.request_id == "req-001"
    assert record.query == "테스트 쿼리"
    assert record.summary == "요약 내용"
    assert record.comparison == "비교 내용"
    assert record.next_actions == "행동 내용"
    assert record.sources == "출처 내용"
    assert record.total_elapsed_seconds == 1.5
    assert record.created_at


def test_save_duplicate_request_id_is_ignored(store):
    req, resp = _make_response()
    store.save(req, resp)
    store.save(req, resp)  # should not crash
    assert store.count() == 1


def test_list_recent_order(store):
    for i in range(3):
        req, resp = _make_response(request_id=f"req-{i}", query=f"쿼리 {i}")
        store.save(req, resp)

    records = store.list_recent(limit=2)
    assert len(records) == 2
    assert records[0].request_id == "req-2"  # newest first
    assert records[1].request_id == "req-1"


def test_list_recent_with_search(store):
    store.save(*_make_response(request_id="r1", query="RAG 비교"))
    store.save(*_make_response(request_id="r2", query="LangChain 분석"))
    store.save(*_make_response(request_id="r3", query="RAG 구현"))

    results = store.list_recent(search="RAG")
    assert len(results) == 2
    assert all("RAG" in r.query for r in results)


def test_get_by_request_id(store):
    store.save(*_make_response(request_id="abc123"))
    record = store.get_by_request_id("abc123")
    assert record is not None
    assert record.request_id == "abc123"


def test_get_by_request_id_not_found(store):
    assert store.get_by_request_id("nonexistent") is None


def test_get_by_id(store):
    store.save(*_make_response(request_id="r1"))
    record = store.get_latest()
    assert record is not None

    fetched = store.get_by_id(record.id)
    assert fetched is not None
    assert fetched.request_id == "r1"


def test_pagination(store):
    for i in range(5):
        store.save(*_make_response(request_id=f"r{i}", query=f"쿼리 {i}"))

    page1 = store.list_recent(limit=2, offset=0)
    page2 = store.list_recent(limit=2, offset=2)
    assert len(page1) == 2
    assert len(page2) == 2
    assert page1[0].request_id != page2[0].request_id


def test_count(store):
    for i in range(3):
        store.save(*_make_response(request_id=f"r{i}"))
    assert store.count() == 3


def test_count_with_search(store):
    store.save(*_make_response(request_id="r1", query="RAG 비교"))
    store.save(*_make_response(request_id="r2", query="LLM 분석"))
    assert store.count(search="RAG") == 1


def test_db_created_automatically(tmp_path):
    db_path = str(tmp_path / "subdir" / "test.db")
    store = HistoryStore(db_path)
    assert os.path.exists(db_path)
    store.close()


def test_followup_from_stored(store):
    req, resp = _make_response(request_id="follow-001", followup_from="req-001")
    store.save(req, resp)
    record = store.get_latest()
    assert record is not None
    assert record.followup_from == "req-001"


def test_format_discord(store):
    store.save(*_make_response())
    record = store.get_latest()
    text = record.format_discord()
    assert "**핵심 요약**" in text
    assert "**비교**" in text
    assert "**다음 행동**" in text
    assert "**출처**" in text


def test_get_latest_empty(store):
    assert store.get_latest() is None


def test_delete_single(store):
    store.save(*_make_response(request_id="r1"))
    record = store.get_latest()
    assert store.delete(record.id) is True
    assert store.count() == 0


def test_delete_nonexistent(store):
    assert store.delete(999) is False


def test_delete_all(store):
    for i in range(5):
        store.save(*_make_response(request_id=f"r{i}"))
    deleted = store.delete_all()
    assert deleted == 5
    assert store.count() == 0


def test_prune_on_save(tmp_path):
    db_path = str(tmp_path / "prune.db")
    store = HistoryStore(db_path, max_records=3)

    for i in range(5):
        store.save(*_make_response(request_id=f"r{i}", query=f"쿼리 {i}"))

    assert store.count() == 3
    # Oldest records should be pruned, newest kept
    records = store.list_recent()
    request_ids = {r.request_id for r in records}
    assert "r0" not in request_ids
    assert "r1" not in request_ids
    assert "r4" in request_ids
    store.close()
