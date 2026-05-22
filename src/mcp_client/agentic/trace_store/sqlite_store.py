from __future__ import annotations

import json
from contextlib import closing
from pathlib import Path
from typing import Any

from src.mcp_shared.sqlite import connect_sqlite
from src.mcp_shared.storage import to_json as encode_json, utc_now_text

from .models import TraceStoreSettings, new_trace_id
from .redaction import redact_payload, redact_text

class SQLiteTraceStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self._ensure_schema()

    @classmethod
    def from_settings(cls, settings: TraceStoreSettings) -> "SQLiteTraceStore | None":
        if not settings.enabled:
            return None
        return cls(settings.resolved_db_path)

    def create_run(
        self,
        *,
        run_id: str,
        user_prompt: str | None,
        mode: str,
        parent_run_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._execute(
            """
            INSERT OR IGNORE INTO runs (
                id, parent_run_id, started_at, user_prompt, mode, status, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                parent_run_id,
                utc_now_text(),
                redact_text(user_prompt) if user_prompt is not None else None,
                mode,
                "running",
                redacted_json(metadata or {}),
            ),
        )

    def complete_run(
        self,
        *,
        run_id: str,
        final_answer: str | None,
        status: str = "completed",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._execute(
            """
            UPDATE runs
            SET completed_at = ?,
                final_answer = ?,
                status = ?,
                metadata_json = ?
            WHERE id = ?
            """,
            (
                utc_now_text(),
                redact_text(final_answer) if final_answer is not None else None,
                status,
                redacted_json(metadata or {}),
                run_id,
            ),
        )

    def create_phase(
        self,
        *,
        phase_id: str,
        run_id: str,
        role: str,
        attempt: int = 1,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._execute(
            """
            INSERT OR IGNORE INTO phases (
                id, run_id, role, attempt, started_at, status, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                phase_id,
                run_id,
                role,
                attempt,
                utc_now_text(),
                "running",
                redacted_json(metadata or {}),
            ),
        )

    def complete_phase(
        self,
        *,
        phase_id: str,
        model: str | None,
        node_id: str | None,
        node_model: str | None,
        status: str = "completed",
    ) -> None:
        self._execute(
            """
            UPDATE phases
            SET completed_at = ?,
                model = COALESCE(?, model),
                node_id = COALESCE(?, node_id),
                node_model = COALESCE(?, node_model),
                status = ?
            WHERE id = ?
            """,
            (utc_now_text(), model, node_id, node_model, status, phase_id),
        )

    def record_event(
        self,
        *,
        run_id: str,
        event_type: str,
        phase_id: str | None = None,
        step: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self._execute(
            """
            INSERT INTO events (
                id, run_id, phase_id, step, event_type, created_at, payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_trace_id(),
                run_id,
                phase_id,
                step,
                event_type,
                utc_now_text(),
                redacted_json(payload or {}),
            ),
        )

    def record_message(
        self,
        *,
        run_id: str,
        phase_id: str | None,
        step: int | None,
        sequence: int,
        role: str,
        source: str,
        content: str | None,
        thinking: str | None = None,
        tool_name: str | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        model: str | None = None,
        node_id: str | None = None,
        node_model: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._execute(
            """
            INSERT INTO messages (
                id, run_id, phase_id, step, sequence, role, source, content,
                thinking, tool_name, tool_calls_json, model, node_id, node_model,
                created_at, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_trace_id(),
                run_id,
                phase_id,
                step,
                sequence,
                role,
                source,
                redact_text(content) if content is not None else None,
                redact_text(thinking) if thinking is not None else None,
                tool_name,
                redacted_json(tool_calls or []),
                model,
                node_id,
                node_model,
                utc_now_text(),
                redacted_json(metadata or {}),
            ),
        )

    def record_artifact(
        self,
        *,
        run_id: str,
        phase_id: str | None,
        artifact_type: str,
        path: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._execute(
            """
            INSERT INTO artifacts (
                id, run_id, phase_id, artifact_type, path, created_at, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_trace_id(),
                run_id,
                phase_id,
                artifact_type,
                path,
                utc_now_text(),
                redacted_json(metadata or {}),
            ),
        )

    def record_dataset_example(
        self,
        *,
        run_id: str,
        phase_id: str | None,
        example_type: str,
        input_payload: dict[str, Any],
        output_payload: dict[str, Any],
        quality_score: float | None = None,
        tags: list[str] | None = None,
    ) -> None:
        self._execute(
            """
            INSERT INTO dataset_examples (
                id, run_id, phase_id, example_type, input_json, output_json,
                quality_score, tags, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_trace_id(),
                run_id,
                phase_id,
                example_type,
                redacted_json(input_payload),
                redacted_json(output_payload),
                quality_score,
                ",".join(tags or []),
                utc_now_text(),
            ),
        )

    def export_dataset_jsonl(
        self,
        *,
        output_path: str | Path,
        example_type: str = "sft_conversation",
        limit: int | None = None,
    ) -> int:
        query = """
            SELECT id, run_id, phase_id, example_type, input_json, output_json,
                   quality_score, tags
            FROM dataset_examples
            WHERE example_type = ?
            ORDER BY created_at ASC
        """
        params: tuple[Any, ...]
        if limit is not None:
            query += " LIMIT ?"
            params = (example_type, limit)
        else:
            params = (example_type,)

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        count = 0
        with closing(connect_sqlite(self.db_path, timeout=30.0, foreign_keys=True)) as conn, output.open("w", encoding="utf-8") as handle:
            for row in conn.execute(query, params):
                item = {
                    "id": row[0],
                    "run_id": row[1],
                    "phase_id": row[2],
                    "example_type": row[3],
                    "input": json.loads(row[4]),
                    "output": json.loads(row[5]),
                    "quality_score": row[6],
                    "tags": [tag for tag in (row[7] or "").split(",") if tag],
                }
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
                count += 1
        return count

    def _ensure_schema(self) -> None:
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with closing(connect_sqlite(self.db_path, timeout=30.0, foreign_keys=True)) as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;

                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    parent_run_id TEXT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    user_prompt TEXT,
                    mode TEXT NOT NULL,
                    final_answer TEXT,
                    status TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS phases (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    attempt INTEGER NOT NULL DEFAULT 1,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    model TEXT,
                    node_id TEXT,
                    node_model TEXT,
                    status TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY (run_id) REFERENCES runs(id)
                );

                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    phase_id TEXT,
                    step INTEGER,
                    event_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY (run_id) REFERENCES runs(id),
                    FOREIGN KEY (phase_id) REFERENCES phases(id)
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    phase_id TEXT,
                    step INTEGER,
                    sequence INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    source TEXT NOT NULL,
                    content TEXT,
                    thinking TEXT,
                    tool_name TEXT,
                    tool_calls_json TEXT NOT NULL DEFAULT '[]',
                    model TEXT,
                    node_id TEXT,
                    node_model TEXT,
                    created_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY (run_id) REFERENCES runs(id),
                    FOREIGN KEY (phase_id) REFERENCES phases(id)
                );

                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    phase_id TEXT,
                    artifact_type TEXT NOT NULL,
                    path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY (run_id) REFERENCES runs(id),
                    FOREIGN KEY (phase_id) REFERENCES phases(id)
                );

                CREATE TABLE IF NOT EXISTS dataset_examples (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    phase_id TEXT,
                    example_type TEXT NOT NULL,
                    input_json TEXT NOT NULL,
                    output_json TEXT NOT NULL,
                    quality_score REAL,
                    tags TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    exported_at TEXT,
                    FOREIGN KEY (run_id) REFERENCES runs(id),
                    FOREIGN KEY (phase_id) REFERENCES phases(id)
                );

                CREATE INDEX IF NOT EXISTS idx_phases_run_id ON phases(run_id);
                CREATE INDEX IF NOT EXISTS idx_events_run_id ON events(run_id);
                CREATE INDEX IF NOT EXISTS idx_messages_run_id ON messages(run_id);
                CREATE INDEX IF NOT EXISTS idx_dataset_type ON dataset_examples(example_type);
                """
            )
            conn.commit()

    def _execute(self, sql: str, params: tuple[Any, ...]) -> None:
        with closing(connect_sqlite(self.db_path, timeout=30.0, foreign_keys=True)) as conn:
            conn.execute(sql, params)
            conn.commit()

def redacted_json(payload: Any) -> str:
    return encode_json(redact_payload(payload))
