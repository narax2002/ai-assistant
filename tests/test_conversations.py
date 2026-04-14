"""Tests for ConversationStore."""

import pytest

from storage.conversations import ConversationStore


@pytest.fixture()
def store() -> ConversationStore:
    s = ConversationStore(":memory:")
    yield s
    s.close()


class TestCreate:
    def test_create_generates_uuid_session_id(self, store):
        c = store.create(platform="web")
        assert c.session_id
        assert c.platform == "web"
        assert c.title is None
        assert c.title_locked is False

    def test_create_with_explicit_session_id(self, store):
        c = store.create(platform="discord", session_id="thread-123")
        assert c.session_id == "thread-123"

    def test_create_with_title_locks_it(self, store):
        c = store.create(platform="web", title="My chat")
        assert c.title == "My chat"
        assert c.title_locked is True

    def test_session_id_uniqueness(self, store):
        store.create(platform="web", session_id="dup")
        with pytest.raises(Exception):
            store.create(platform="web", session_id="dup")


class TestLookup:
    def test_get_by_id(self, store):
        c = store.create(platform="web")
        found = store.get(c.id)
        assert found.id == c.id

    def test_get_by_session(self, store):
        store.create(platform="api", session_id="abc")
        found = store.get_by_session("abc")
        assert found.session_id == "abc"

    def test_missing_returns_none(self, store):
        assert store.get(999) is None
        assert store.get_by_session("no") is None

    def test_list_filters_by_platform(self, store):
        store.create(platform="web")
        store.create(platform="discord")
        store.create(platform="web")
        web = store.list_recent(platform="web")
        assert len(web) == 2
        assert all(c.platform == "web" for c in web)


class TestRename:
    def test_rename_locks_by_default(self, store):
        c = store.create(platform="web")
        assert store.rename(c.id, "New title") is True
        updated = store.get(c.id)
        assert updated.title == "New title"
        assert updated.title_locked is True

    def test_rename_unlocked(self, store):
        c = store.create(platform="web")
        store.rename(c.id, "auto-name", locked=False)
        updated = store.get(c.id)
        assert updated.title_locked is False


class TestMessages:
    def test_append_and_list(self, store):
        c = store.create(platform="web")
        store.append_message(c.id, "user", "안녕")
        store.append_message(c.id, "assistant", "반가워요", provider_used="ollama")
        msgs = store.list_messages(c.id)
        assert len(msgs) == 2
        assert msgs[0].role == "user"
        assert msgs[1].provider_used == "ollama"

    def test_list_messages_limit_returns_most_recent_in_chronological_order(self, store):
        c = store.create(platform="web")
        for i in range(5):
            store.append_message(c.id, "user", f"msg{i}")
        recent = store.list_messages(c.id, limit=3)
        assert [m.content for m in recent] == ["msg2", "msg3", "msg4"]

    def test_count_messages(self, store):
        c = store.create(platform="web")
        store.append_message(c.id, "user", "a")
        store.append_message(c.id, "assistant", "b")
        assert store.count_messages(c.id) == 2

    def test_delete_cascades_messages(self, store):
        c = store.create(platform="web")
        store.append_message(c.id, "user", "a")
        store.delete(c.id)
        assert store.count_messages(c.id) == 0
