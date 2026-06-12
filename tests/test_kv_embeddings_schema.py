from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

from src.mcp.cache.store import SQLiteKVCacheStore


@pytest.fixture
def db_path() -> Path:
    with tempfile.TemporaryDirectory() as d:
        yield Path(d) / "test_kv.sqlite"


def test_schema_creates_kv_embeddings_table(db_path: Path) -> None:
    SQLiteKVCacheStore(db_path, embedding_enabled=True)
    conn = sqlite3.connect(db_path)
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    finally:
        conn.close()
    assert "kv_embeddings" in tables


def test_schema_creates_kv_embeddings_columns(db_path: Path) -> None:
    SQLiteKVCacheStore(db_path, embedding_enabled=True)
    conn = sqlite3.connect(db_path)
    try:
        cols = {
            row[1]
            for row in conn.execute("PRAGMA table_info(kv_embeddings)").fetchall()
        }
    finally:
        conn.close()
    assert {"namespace", "key", "model", "dims", "vector_json", "embedded_at"} <= cols


def test_delete_entry_removes_embedding(db_path: Path) -> None:
    store = SQLiteKVCacheStore(db_path, embedding_enabled=True)
    store.set("ns", "k1", "valor")
    store.set_embedding("ns", "k1", [0.1, 0.2, 0.3], model="test-model")

    assert store.get_embedding("ns", "k1") is not None
    store.delete("ns", "k1")
    assert store.get_embedding("ns", "k1") is None


def test_clear_namespace_removes_embeddings(db_path: Path) -> None:
    store = SQLiteKVCacheStore(db_path, embedding_enabled=True)
    store.set("ns", "k1", "a")
    store.set("ns", "k2", "b")
    store.set_embedding("ns", "k1", [0.1, 0.2], model="m")
    store.set_embedding("ns", "k2", [0.3, 0.4], model="m")

    store.clear(namespace="ns")

    assert store.get_embedding("ns", "k1") is None
    assert store.get_embedding("ns", "k2") is None


def test_schema_creates_without_embedding_flag(db_path: Path) -> None:
    store = SQLiteKVCacheStore(db_path, embedding_enabled=False)
    store.set("ns", "k1", "val")
    result = store.get("ns", "k1")
    assert result["hit"] is True
