"""Tests for auto-title generation."""

import asyncio
from unittest.mock import MagicMock

import pytest

from services.auto_title import maybe_generate_title
from storage.conversations import ConversationStore


@pytest.fixture()
def store() -> ConversationStore:
    s = ConversationStore(":memory:")
    yield s
    s.close()


def _mock_provider(reply: str = "짧은 제목"):
    p = MagicMock()
    p.chat.return_value = reply
    return p


def _run(coro):
    return asyncio.run(coro)


def test_generates_title_after_first_exchange(store):
    c = store.create(platform="web")
    store.append_message(c.id, "user", "안녕")
    store.append_message(c.id, "assistant", "반가워요")

    _run(maybe_generate_title(store, _mock_provider("인사 대화"), c.id))

    updated = store.get(c.id)
    assert updated.title == "인사 대화"
    assert updated.title_locked is False


def test_skips_if_title_locked(store):
    c = store.create(platform="web", title="수동 제목")
    store.append_message(c.id, "user", "안녕")
    store.append_message(c.id, "assistant", "반가워요")

    provider = _mock_provider("자동 제목")
    _run(maybe_generate_title(store, provider, c.id))

    assert store.get(c.id).title == "수동 제목"
    provider.chat.assert_not_called()


def test_skips_if_title_already_set(store):
    c = store.create(platform="web")
    store.rename(c.id, "이전 자동 제목", locked=False)
    store.append_message(c.id, "user", "안녕")
    store.append_message(c.id, "assistant", "반가워요")

    provider = _mock_provider("새 제목")
    _run(maybe_generate_title(store, provider, c.id))

    assert store.get(c.id).title == "이전 자동 제목"
    provider.chat.assert_not_called()


def test_skips_if_not_enough_messages(store):
    c = store.create(platform="web")
    store.append_message(c.id, "user", "안녕")

    provider = _mock_provider("제목")
    _run(maybe_generate_title(store, provider, c.id))

    assert store.get(c.id).title is None
    provider.chat.assert_not_called()


def test_strips_quotes_and_trims(store):
    c = store.create(platform="web")
    store.append_message(c.id, "user", "질문")
    store.append_message(c.id, "assistant", "답변")

    _run(maybe_generate_title(store, _mock_provider('  "날씨 문의"  '), c.id))
    assert store.get(c.id).title == "날씨 문의"


def test_swallows_provider_error(store):
    c = store.create(platform="web")
    store.append_message(c.id, "user", "a")
    store.append_message(c.id, "assistant", "b")

    provider = MagicMock()
    provider.chat.side_effect = RuntimeError("boom")
    _run(maybe_generate_title(store, provider, c.id))  # must not raise

    assert store.get(c.id).title is None
