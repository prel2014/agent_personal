from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.mcp_shared.sqlite import connect_sqlite, fetch_all, fetch_one
from src.mcp_shared.storage import from_json_dict, new_uuid_text, to_json, utc_now_text


DEFAULT_SESSION_DB_PATH = ".mcp_sessions/client_sessions.sqlite"


def new_session_id() -> str:
    return new_uuid_text()


def title_from_prompt(prompt: str | None) -> str:
    normalized = " ".join((prompt or "").split())
    if not normalized:
        return f"Sesion {utc_now_text()}"

    if len(normalized) <= 60:
        return normalized

    return normalized[:57].rstrip() + "..."


@dataclass(frozen=True)
class SessionRecord:
    id: str
    title: str
    created_at: str
    updated_at: str
    status: str
    metadata: dict[str, Any]
    message_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
            "metadata": dict(self.metadata),
            "message_count": self.message_count,
        }


class SQLiteSessionStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self._ensure_schema()

    def create_session(
        self,
        *,
        title: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SessionRecord:
        now = utc_now_text()
        resolved_id = session_id or new_session_id()
        resolved_title = title or f"Sesion {now}"
        self._execute(
            """
            INSERT INTO sessions (
                id, title, created_at, updated_at, status, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                resolved_id,
                resolved_title,
                now,
                now,
                "active",
                to_json(metadata or {}),
            ),
        )
        record = self.get_session(resolved_id)
        if record is None:
            raise RuntimeError("No se pudo crear la sesion.")
        return record

    def get_session(self, session_id: str) -> SessionRecord | None:
        row = fetch_one(self.db_path,
            """
            SELECT s.id, s.title, s.created_at, s.updated_at, s.status,
                   s.metadata_json, COUNT(m.id) AS message_count
            FROM sessions s
            LEFT JOIN session_messages m ON m.session_id = s.id
            WHERE s.id = ?
            GROUP BY s.id
            """,
            (session_id,),
        )
        return _record_from_row(row) if row is not None else None

    def latest_session(self) -> SessionRecord | None:
        row = fetch_one(self.db_path,
            """
            SELECT s.id, s.title, s.created_at, s.updated_at, s.status,
                   s.metadata_json, COUNT(m.id) AS message_count
            FROM sessions s
            LEFT JOIN session_messages m ON m.session_id = s.id
            WHERE s.status != 'closed'
            GROUP BY s.id
            ORDER BY s.updated_at DESC
            LIMIT 1
            """,
            (),
        )
        return _record_from_row(row) if row is not None else None

    def list_sessions(self, *, limit: int = 20) -> list[SessionRecord]:
        rows = fetch_all(self.db_path,
            """
            SELECT s.id, s.title, s.created_at, s.updated_at, s.status,
                   s.metadata_json, COUNT(m.id) AS message_count
            FROM sessions s
            LEFT JOIN session_messages m ON m.session_id = s.id
            GROUP BY s.id
            ORDER BY s.updated_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [_record_from_row(row) for row in rows]

    def load_messages(self, session_id: str) -> list[dict[str, Any]]:
        self.require_session(session_id)
        rows = fetch_all(self.db_path,
            """
            SELECT role, content, metadata_json
            FROM session_messages
            WHERE session_id = ?
            ORDER BY sequence ASC
            """,
            (session_id,),
        )
        messages: list[dict[str, Any]] = []
        for row in rows:
            metadata = from_json_dict(row["metadata_json"])
            message = metadata.get("message")
            if isinstance(message, dict):
                messages.append(_sanitize_message(message))
                continue

            messages.append(
                {
                    "role": row["role"],
                    "content": row["content"] or "",
                }
            )
        return messages

    def append_messages(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
    ) -> None:
        self.require_session(session_id)
        start = self._next_sequence(session_id)
        self._insert_messages(session_id, messages, start_sequence=start)
        self._touch_session(session_id)

    def replace_messages(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
    ) -> None:
        self.require_session(session_id)
        with closing(connect_sqlite(self.db_path)) as conn:
            conn.execute(
                "DELETE FROM session_messages WHERE session_id = ?",
                (session_id,),
            )
            self._insert_messages(
                session_id,
                messages,
                start_sequence=1,
                conn=conn,
            )
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (utc_now_text(), session_id),
            )
            conn.commit()

    def rename_session(self, session_id: str, title: str) -> None:
        self.require_session(session_id)
        cleaned = " ".join(title.split())
        if not cleaned:
            raise ValueError("El titulo de sesion no puede estar vacio.")
        self._execute(
            "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
            (cleaned, utc_now_text(), session_id),
        )

    def close_session(self, session_id: str) -> None:
        self.require_session(session_id)
        self._execute(
            "UPDATE sessions SET status = 'closed', updated_at = ? WHERE id = ?",
            (utc_now_text(), session_id),
        )

    def record_error(self, session_id: str, error: str) -> None:
        record = self.require_session(session_id)
        metadata = dict(record.metadata)
        metadata["last_error"] = error
        metadata["last_error_at"] = utc_now_text()
        self._execute(
            """
            UPDATE sessions
            SET metadata_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (to_json(metadata), utc_now_text(), session_id),
        )

    def require_session(self, session_id: str) -> SessionRecord:
        record = self.get_session(session_id)
        if record is None:
            raise ValueError(f"No existe la sesion: {session_id}")
        return record

    def _ensure_schema(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(connect_sqlite(self.db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS session_messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_session_messages_sequence
                ON session_messages(session_id, sequence)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sessions_updated_at
                ON sessions(updated_at)
                """
            )
            conn.commit()

    def _insert_messages(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
        *,
        start_sequence: int,
        conn: sqlite3.Connection | None = None,
    ) -> None:
        active_conn = conn or connect_sqlite(self.db_path)
        should_close = conn is None
        try:
            for offset, raw_message in enumerate(messages):
                message = _sanitize_message(raw_message)
                active_conn.execute(
                    """
                    INSERT INTO session_messages (
                        id, session_id, sequence, role, content, metadata_json, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        new_session_id(),
                        session_id,
                        start_sequence + offset,
                        str(message.get("role") or "assistant"),
                        str(message.get("content") or ""),
                        to_json({"message": message}),
                        utc_now_text(),
                    ),
                )
            if should_close:
                active_conn.commit()
        finally:
            if should_close:
                active_conn.close()

    def _next_sequence(self, session_id: str) -> int:
        row = fetch_one(self.db_path,
            """
            SELECT COALESCE(MAX(sequence), 0) + 1 AS next_sequence
            FROM session_messages
            WHERE session_id = ?
            """,
            (session_id,),
        )
        return int(row["next_sequence"] if row is not None else 1)

    def _touch_session(self, session_id: str) -> None:
        self._execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (utc_now_text(), session_id),
        )

    def _execute(self, query: str, params: tuple[Any, ...]) -> None:
        with closing(connect_sqlite(self.db_path)) as conn:
            conn.execute(query, params)
            conn.commit()


def _sanitize_message(message: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(message or {})
    sanitized.setdefault("role", "assistant")
    sanitized["content"] = sanitized.get("content") or ""
    sanitized.pop("thinking", None)
    return sanitized


def _record_from_row(row: sqlite3.Row) -> SessionRecord:
    return SessionRecord(
        id=row["id"],
        title=row["title"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        status=row["status"],
        metadata=from_json_dict(row["metadata_json"]),
        message_count=int(row["message_count"] or 0),
    )
