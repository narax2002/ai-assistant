"""SQLite-backed research history store."""

import logging
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from schemas.research import ResearchRequest, ResearchResponse

LOGGER = logging.getLogger(__name__)

_DEFAULT_MAX_RECORDS = 200
_DEFAULT_MAX_SIZE_MB = 50

_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS research_history (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id            TEXT NOT NULL UNIQUE,
    query                 TEXT NOT NULL,
    summary               TEXT NOT NULL,
    comparison            TEXT NOT NULL,
    next_actions          TEXT NOT NULL,
    sources               TEXT NOT NULL,
    total_elapsed_seconds REAL NOT NULL DEFAULT 0.0,
    followup_from         TEXT,
    created_at            TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime'))
)
"""

_INSERT = """\
INSERT OR IGNORE INTO research_history
    (request_id, query, summary, comparison, next_actions, sources,
     total_elapsed_seconds, followup_from)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""


@dataclass(frozen=True)
class ResearchRecord:
    id: int
    request_id: str
    query: str
    summary: str
    comparison: str
    next_actions: str
    sources: str
    total_elapsed_seconds: float
    followup_from: str | None
    created_at: str

    def format_discord(self) -> str:
        return (
            f"**핵심 요약**\n{self.summary}\n\n"
            f"**비교**\n{self.comparison}\n\n"
            f"**다음 행동**\n{self.next_actions}\n\n"
            f"**출처**\n{self.sources}"
        )


class HistoryStore:
    def __init__(
        self,
        db_path: str,
        *,
        max_records: int = _DEFAULT_MAX_RECORDS,
        max_size_mb: int = _DEFAULT_MAX_SIZE_MB,
    ) -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._max_records = max_records
        self._max_size_mb = max_size_mb
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(_CREATE_TABLE)
        self._conn.commit()
        LOGGER.info(
            "History store ready: %s (max=%d records, %dMB)",
            db_path,
            max_records,
            max_size_mb,
        )

    def save(self, request: ResearchRequest, response: ResearchResponse) -> None:
        self._conn.execute(
            _INSERT,
            (
                request.request_id,
                request.query,
                response.summary,
                response.comparison,
                response.next_actions,
                response.sources,
                response.total_elapsed_seconds,
                getattr(request, "followup_from", None),
            ),
        )
        self._conn.commit()
        self._prune()
        self._check_size()

    def get_latest(self) -> ResearchRecord | None:
        row = self._conn.execute(
            "SELECT * FROM research_history ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return self._row_to_record(row) if row else None

    def get_by_request_id(self, request_id: str) -> ResearchRecord | None:
        row = self._conn.execute(
            "SELECT * FROM research_history WHERE request_id = ?", (request_id,)
        ).fetchone()
        return self._row_to_record(row) if row else None

    def get_by_id(self, record_id: int) -> ResearchRecord | None:
        row = self._conn.execute(
            "SELECT * FROM research_history WHERE id = ?", (record_id,)
        ).fetchone()
        return self._row_to_record(row) if row else None

    def list_recent(
        self,
        limit: int = 10,
        offset: int = 0,
        search: str | None = None,
    ) -> list[ResearchRecord]:
        if search:
            rows = self._conn.execute(
                "SELECT * FROM research_history WHERE query LIKE ? "
                "ORDER BY id DESC LIMIT ? OFFSET ?",
                (f"%{search}%", limit, offset),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM research_history ORDER BY id DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def count(self, search: str | None = None) -> int:
        if search:
            row = self._conn.execute(
                "SELECT COUNT(*) FROM research_history WHERE query LIKE ?",
                (f"%{search}%",),
            ).fetchone()
        else:
            row = self._conn.execute("SELECT COUNT(*) FROM research_history").fetchone()
        return row[0] if row else 0

    def delete(self, record_id: int) -> bool:
        cursor = self._conn.execute("DELETE FROM research_history WHERE id = ?", (record_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    def delete_all(self) -> int:
        cursor = self._conn.execute("DELETE FROM research_history")
        self._conn.commit()
        self._conn.execute("VACUUM")
        return cursor.rowcount

    def _prune(self) -> None:
        total = self.count()
        if total <= self._max_records:
            return
        excess = total - self._max_records
        self._conn.execute(
            "DELETE FROM research_history WHERE id IN "
            "(SELECT id FROM research_history ORDER BY id ASC LIMIT ?)",
            (excess,),
        )
        self._conn.commit()
        LOGGER.info("Pruned %d old records (max=%d)", excess, self._max_records)

    def _check_size(self) -> None:
        if self._db_path == ":memory:":
            return
        try:
            size_mb = os.path.getsize(self._db_path) / (1024 * 1024)
        except OSError:
            return
        if size_mb > self._max_size_mb:
            LOGGER.warning(
                "History DB size %.1fMB exceeds limit %dMB — consider running /history clear",
                size_mb,
                self._max_size_mb,
            )

    def close(self) -> None:
        self._conn.close()

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> ResearchRecord:
        return ResearchRecord(
            id=row["id"],
            request_id=row["request_id"],
            query=row["query"],
            summary=row["summary"],
            comparison=row["comparison"],
            next_actions=row["next_actions"],
            sources=row["sources"],
            total_elapsed_seconds=row["total_elapsed_seconds"],
            followup_from=row["followup_from"],
            created_at=row["created_at"],
        )
