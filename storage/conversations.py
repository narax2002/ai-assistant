"""SQLite-backed conversation/session store for multi-turn chat."""

import logging
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path

LOGGER = logging.getLogger(__name__)


_CREATE_CONVERSATIONS = """\
CREATE TABLE IF NOT EXISTS conversations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    TEXT NOT NULL UNIQUE,
    title         TEXT,
    title_locked  INTEGER NOT NULL DEFAULT 0,
    platform      TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
    updated_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime'))
)
"""

_CREATE_MESSAGES = """\
CREATE TABLE IF NOT EXISTS conversation_messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    provider_used   TEXT,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
)
"""

_CREATE_INDEX = (
    "CREATE INDEX IF NOT EXISTS idx_messages_conv ON conversation_messages(conversation_id, id)"
)


@dataclass(frozen=True)
class Conversation:
    id: int
    session_id: str
    title: str | None
    title_locked: bool
    platform: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class ConversationMessage:
    id: int
    conversation_id: int
    role: str
    content: str
    provider_used: str | None
    created_at: str


class ConversationStore:
    def __init__(self, db_path: str) -> None:
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute(_CREATE_CONVERSATIONS)
        self._conn.execute(_CREATE_MESSAGES)
        self._conn.execute(_CREATE_INDEX)
        self._conn.commit()
        LOGGER.info("Conversation store ready: %s", db_path)

    def create(
        self,
        *,
        platform: str,
        session_id: str | None = None,
        title: str | None = None,
    ) -> Conversation:
        sid = session_id or str(uuid.uuid4())
        title_locked = 1 if title else 0
        cursor = self._conn.execute(
            "INSERT INTO conversations (session_id, title, title_locked, platform) "
            "VALUES (?, ?, ?, ?)",
            (sid, title, title_locked, platform),
        )
        self._conn.commit()
        row = self._conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return self._row_to_conversation(row)

    def get(self, conversation_id: int) -> Conversation | None:
        row = self._conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        return self._row_to_conversation(row) if row else None

    def get_by_session(self, session_id: str) -> Conversation | None:
        row = self._conn.execute(
            "SELECT * FROM conversations WHERE session_id = ?", (session_id,)
        ).fetchone()
        return self._row_to_conversation(row) if row else None

    def list_recent(self, limit: int = 20, platform: str | None = None) -> list[Conversation]:
        if platform:
            rows = self._conn.execute(
                "SELECT * FROM conversations WHERE platform = ? ORDER BY updated_at DESC LIMIT ?",
                (platform, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row_to_conversation(r) for r in rows]

    def rename(self, conversation_id: int, title: str, *, locked: bool = True) -> bool:
        cursor = self._conn.execute(
            "UPDATE conversations SET title = ?, title_locked = ?, "
            "updated_at = strftime('%Y-%m-%dT%H:%M:%S','now','localtime') WHERE id = ?",
            (title, 1 if locked else 0, conversation_id),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def delete(self, conversation_id: int) -> bool:
        cursor = self._conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    def append_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        *,
        provider_used: str | None = None,
    ) -> ConversationMessage:
        cursor = self._conn.execute(
            "INSERT INTO conversation_messages (conversation_id, role, content, provider_used) "
            "VALUES (?, ?, ?, ?)",
            (conversation_id, role, content, provider_used),
        )
        self._conn.execute(
            "UPDATE conversations SET updated_at = strftime('%Y-%m-%dT%H:%M:%S','now','localtime') "
            "WHERE id = ?",
            (conversation_id,),
        )
        self._conn.commit()
        row = self._conn.execute(
            "SELECT * FROM conversation_messages WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return self._row_to_message(row)

    def list_messages(
        self, conversation_id: int, limit: int | None = None
    ) -> list[ConversationMessage]:
        if limit is None:
            rows = self._conn.execute(
                "SELECT * FROM conversation_messages WHERE conversation_id = ? ORDER BY id ASC",
                (conversation_id,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM (SELECT * FROM conversation_messages WHERE conversation_id = ? "
                "ORDER BY id DESC LIMIT ?) ORDER BY id ASC",
                (conversation_id, limit),
            ).fetchall()
        return [self._row_to_message(r) for r in rows]

    def count_messages(self, conversation_id: int) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM conversation_messages WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
        return row[0] if row else 0

    def close(self) -> None:
        self._conn.close()

    @staticmethod
    def _row_to_conversation(row: sqlite3.Row) -> Conversation:
        return Conversation(
            id=row["id"],
            session_id=row["session_id"],
            title=row["title"],
            title_locked=bool(row["title_locked"]),
            platform=row["platform"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_to_message(row: sqlite3.Row) -> ConversationMessage:
        return ConversationMessage(
            id=row["id"],
            conversation_id=row["conversation_id"],
            role=row["role"],
            content=row["content"],
            provider_used=row["provider_used"],
            created_at=row["created_at"],
        )
