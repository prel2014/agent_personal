from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

from src.mcp_shared.sqlite import connect_sqlite, fetch_all, fetch_one
from src.mcp_shared.storage import from_json_dict, to_json, utc_now, utc_now_text

from .embedder import BM25Ranker, build_embed_text, cosine_similarity


DEFAULT_KV_CACHE_DB_PATH = ".mcp_cache/kv_cache.sqlite"
RESERVED_NAMESPACES = frozenset({"secrets", "auth", "tokens", "credentials"})


@dataclass(frozen=True)
class KVEntry:
    namespace: str
    key: str
    value: Any
    metadata: dict[str, Any]
    created_at: str
    updated_at: str
    expires_at: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "namespace": self.namespace,
            "key": self.key,
            "value": self.value,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
        }


class SQLiteKVCacheStore:
    def __init__(self, db_path: str | Path, *, embedding_enabled: bool = False) -> None:
        self.db_path = Path(db_path)
        self._embedding_enabled = embedding_enabled
        self._ensure_schema()

    def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        *,
        ttl_seconds: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        namespace = self._clean_namespace(namespace)
        key = self._clean_key(key)
        if ttl_seconds is not None and ttl_seconds <= 0:
            raise ValueError("ttl_seconds debe ser mayor a 0.")

        now = utc_now_text()
        expires_at = (
            (utc_now() + timedelta(seconds=ttl_seconds)).isoformat()
            if ttl_seconds is not None
            else None
        )
        value_json = to_json(value)
        metadata_json = to_json(metadata or {})

        with closing(connect_sqlite(self.db_path)) as conn:
            conn.execute(
                """
                INSERT INTO kv_entries (
                    namespace, key, value_json, metadata_json,
                    created_at, updated_at, expires_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(namespace, key) DO UPDATE SET
                    value_json = excluded.value_json,
                    metadata_json = excluded.metadata_json,
                    updated_at = excluded.updated_at,
                    expires_at = excluded.expires_at
                """,
                (namespace, key, value_json, metadata_json, now, now, expires_at),
            )
            conn.commit()

        return {
            "namespace": namespace,
            "key": key,
            "stored": True,
            "expires_at": expires_at,
        }

    def get(self, namespace: str, key: str) -> dict[str, Any]:
        namespace = self._clean_namespace(namespace)
        key = self._clean_key(key)
        row = fetch_one(self.db_path,
            """
            SELECT namespace, key, value_json, metadata_json, created_at, updated_at, expires_at
            FROM kv_entries
            WHERE namespace = ? AND key = ?
            """,
            (namespace, key),
        )
        if row is None:
            return {"hit": False, "namespace": namespace, "key": key, "entry": None}

        entry = self._entry_from_row(row)
        if self._is_expired(entry):
            self.delete(namespace, key)
            return {
                "hit": False,
                "namespace": namespace,
                "key": key,
                "entry": None,
                "expired": True,
            }

        return {"hit": True, "namespace": namespace, "key": key, "entry": entry.to_dict()}

    def delete(self, namespace: str, key: str) -> dict[str, Any]:
        namespace = self._clean_namespace(namespace)
        key = self._clean_key(key)
        with closing(connect_sqlite(self.db_path)) as conn:
            if self._embedding_enabled:
                conn.execute(
                    "DELETE FROM kv_embeddings WHERE namespace = ? AND key = ?",
                    (namespace, key),
                )
            cursor = conn.execute(
                "DELETE FROM kv_entries WHERE namespace = ? AND key = ?",
                (namespace, key),
            )
            conn.commit()
        return {"namespace": namespace, "key": key, "deleted": cursor.rowcount}

    def list(
        self,
        *,
        namespace: str | None = None,
        prefix: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        if limit < 1:
            raise ValueError("limit debe ser mayor o igual a 1.")
        if limit > 1000:
            raise ValueError("limit no puede ser mayor a 1000.")

        filters: list[str] = []
        params: list[Any] = []
        clean_namespace = None
        if namespace is not None:
            clean_namespace = self._clean_namespace(namespace)
            filters.append("namespace = ?")
            params.append(clean_namespace)
        if prefix:
            filters.append("key LIKE ?")
            params.append(f"{prefix}%")

        query = """
            SELECT namespace, key, value_json, metadata_json, created_at, updated_at, expires_at
            FROM kv_entries
        """
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY namespace ASC, key ASC LIMIT ?"
        params.append(limit)

        entries: list[dict[str, Any]] = []
        expired: list[tuple[str, str]] = []
        for row in fetch_all(self.db_path, query, tuple(params)):
            entry = self._entry_from_row(row)
            if self._is_expired(entry):
                expired.append((entry.namespace, entry.key))
                continue
            entries.append(entry.to_dict())

        for entry_namespace, entry_key in expired:
            self.delete(entry_namespace, entry_key)

        return {
            "namespace": clean_namespace,
            "prefix": prefix,
            "limit": limit,
            "entries": entries,
            "expired_removed": len(expired),
        }

    def clear(
        self,
        *,
        namespace: str | None = None,
        expired_only: bool = False,
    ) -> dict[str, Any]:
        clean_namespace = self._clean_namespace(namespace) if namespace is not None else None
        filters: list[str] = []
        params: list[Any] = []
        if clean_namespace is not None:
            filters.append("namespace = ?")
            params.append(clean_namespace)
        if expired_only:
            filters.append("expires_at IS NOT NULL AND expires_at <= ?")
            params.append(utc_now_text())

        query = "DELETE FROM kv_entries"
        if filters:
            query += " WHERE " + " AND ".join(filters)

        with closing(connect_sqlite(self.db_path)) as conn:
            if self._embedding_enabled:
                self._clear_embeddings_in_conn(conn, clean_namespace, expired_only)
            cursor = conn.execute(query, tuple(params))
            conn.commit()

        return {
            "namespace": clean_namespace,
            "expired_only": expired_only,
            "deleted": cursor.rowcount,
        }

    # ------------------------------------------------------------------
    # Métodos de embedding
    # ------------------------------------------------------------------

    def set_embedding(
        self,
        namespace: str,
        key: str,
        vector: list[float],
        *,
        model: str,
    ) -> None:
        now = utc_now_text()
        vector_json = json.dumps(vector)
        with closing(connect_sqlite(self.db_path)) as conn:
            conn.execute(
                """
                INSERT INTO kv_embeddings (namespace, key, model, dims, vector_json, embedded_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(namespace, key) DO UPDATE SET
                    model = excluded.model,
                    dims = excluded.dims,
                    vector_json = excluded.vector_json,
                    embedded_at = excluded.embedded_at
                """,
                (namespace, key, model, len(vector), vector_json, now),
            )
            conn.commit()

    def get_embedding(self, namespace: str, key: str) -> list[float] | None:
        row = fetch_one(
            self.db_path,
            "SELECT vector_json FROM kv_embeddings WHERE namespace = ? AND key = ?",
            (namespace, key),
        )
        if row is None:
            return None
        return json.loads(row["vector_json"])

    def delete_embedding(self, namespace: str, key: str) -> None:
        with closing(connect_sqlite(self.db_path)) as conn:
            conn.execute(
                "DELETE FROM kv_embeddings WHERE namespace = ? AND key = ?",
                (namespace, key),
            )
            conn.commit()

    def has_embeddings(self, *, namespace: str | None = None) -> bool:
        if namespace is not None:
            row = fetch_one(
                self.db_path,
                "SELECT 1 FROM kv_embeddings WHERE namespace = ? LIMIT 1",
                (namespace,),
            )
        else:
            row = fetch_one(self.db_path, "SELECT 1 FROM kv_embeddings LIMIT 1", ())
        return row is not None

    def search_by_embedding(
        self,
        query_vector: list[float],
        *,
        namespace: str | None = None,
        top_k: int = 5,
        min_score: float = 0.0,
        model: str | None = None,
    ) -> dict[str, Any]:
        query = "SELECT namespace, key, model, dims, vector_json FROM kv_embeddings"
        params: list[Any] = []
        if namespace is not None:
            query += " WHERE namespace = ?"
            params.append(namespace)

        rows = fetch_all(self.db_path, query, tuple(params))
        q_dims = len(query_vector)

        scored: list[tuple[str, str, float]] = []
        skipped_model = 0
        for row in rows:
            if model is not None and row["model"] != model:
                skipped_model += 1
                continue
            if row["dims"] != q_dims:
                skipped_model += 1
                continue
            vector = json.loads(row["vector_json"])
            score = cosine_similarity(query_vector, vector)
            if score >= min_score:
                scored.append((row["namespace"], row["key"], score))

        scored.sort(key=lambda x: x[2], reverse=True)
        top = scored[:top_k]

        results: list[dict[str, Any]] = []
        for ns, k, score in top:
            entry_result = self.get(ns, k)
            results.append({
                "namespace": ns,
                "key": k,
                "score": round(score, 6),
                "entry": entry_result.get("entry"),
            })

        total_embedded = len(rows)
        return {
            "method": "embedding",
            "results": results,
            "total_embedded": total_embedded,
            "skipped_incompatible": skipped_model,
            "partial_coverage": skipped_model > 0,
        }

    def search_by_bm25(
        self,
        query: str,
        *,
        namespace: str | None = None,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> dict[str, Any]:
        list_result = self.list(namespace=namespace, limit=1000)
        entries = list_result["entries"]

        corpus = [
            (e["namespace"], e["key"], build_embed_text(e["namespace"], e["key"], e["value"]))
            for e in entries
        ]

        ranked = BM25Ranker().rank(query, corpus, top_k=top_k, min_score=min_score)

        entry_map = {(e["namespace"], e["key"]): e for e in entries}
        results: list[dict[str, Any]] = []
        for ns, key, score in ranked:
            results.append({
                "namespace": ns,
                "key": key,
                "score": round(score, 6),
                "entry": entry_map.get((ns, key)),
            })

        return {
            "method": "bm25",
            "results": results,
            "total_scanned": len(entries),
        }

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _ensure_schema(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(connect_sqlite(self.db_path)) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS kv_entries (
                    namespace TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    expires_at TEXT,
                    PRIMARY KEY(namespace, key)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_kv_entries_expires_at
                ON kv_entries(expires_at)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS kv_embeddings (
                    namespace    TEXT    NOT NULL,
                    key          TEXT    NOT NULL,
                    model        TEXT    NOT NULL,
                    dims         INTEGER NOT NULL,
                    vector_json  TEXT    NOT NULL,
                    embedded_at  TEXT    NOT NULL,
                    PRIMARY KEY (namespace, key),
                    FOREIGN KEY (namespace, key)
                        REFERENCES kv_entries(namespace, key)
                        ON DELETE CASCADE
                        DEFERRABLE INITIALLY DEFERRED
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_kv_embeddings_namespace
                ON kv_embeddings(namespace)
                """
            )
            conn.commit()

    def _clear_embeddings_in_conn(
        self,
        conn: sqlite3.Connection,
        namespace: str | None,
        expired_only: bool,
    ) -> None:
        if expired_only:
            now = utc_now_text()
            if namespace is not None:
                conn.execute(
                    """
                    DELETE FROM kv_embeddings
                    WHERE namespace || char(0) || key IN (
                        SELECT namespace || char(0) || key FROM kv_entries
                        WHERE namespace = ? AND expires_at IS NOT NULL AND expires_at <= ?
                    )
                    """,
                    (namespace, now),
                )
            else:
                conn.execute(
                    """
                    DELETE FROM kv_embeddings
                    WHERE namespace || char(0) || key IN (
                        SELECT namespace || char(0) || key FROM kv_entries
                        WHERE expires_at IS NOT NULL AND expires_at <= ?
                    )
                    """,
                    (now,),
                )
        else:
            if namespace is not None:
                conn.execute(
                    "DELETE FROM kv_embeddings WHERE namespace = ?",
                    (namespace,),
                )
            else:
                conn.execute("DELETE FROM kv_embeddings")

    def _entry_from_row(self, row: sqlite3.Row) -> KVEntry:
        return KVEntry(
            namespace=row["namespace"],
            key=row["key"],
            value=json.loads(row["value_json"]),
            metadata=from_json_dict(row["metadata_json"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            expires_at=row["expires_at"],
        )

    @staticmethod
    def _is_expired(entry: KVEntry) -> bool:
        return entry.expires_at is not None and entry.expires_at <= utc_now_text()

    @staticmethod
    def _clean_namespace(value: str | None) -> str:
        namespace = (value or "default").strip()
        if not namespace:
            raise ValueError("namespace no puede estar vacio.")
        if namespace.lower() in RESERVED_NAMESPACES:
            raise ValueError(f"namespace reservado: {namespace}")
        if len(namespace) > 120:
            raise ValueError("namespace no puede superar 120 caracteres.")
        return namespace

    @staticmethod
    def _clean_key(value: str | None) -> str:
        key = (value or "").strip()
        if not key:
            raise ValueError("key no puede estar vacia.")
        if len(key) > 512:
            raise ValueError("key no puede superar 512 caracteres.")
        return key
