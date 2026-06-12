from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import src.mcp.tools.helpers.kv_functions as kv_mod
from src.mcp.cache.embedder import EmbeddingUnavailableError
from src.mcp.cache.store import SQLiteKVCacheStore
from src.mcp.tools.helpers.kv_search_functions import kv_search


@pytest.fixture(autouse=True)
def reset_globals():
    original_store = kv_mod._store
    original_embedder = kv_mod._embedder
    yield
    kv_mod._store = original_store
    kv_mod._embedder = original_embedder


@pytest.fixture
def populated_store() -> SQLiteKVCacheStore:
    with tempfile.TemporaryDirectory() as d:
        store = SQLiteKVCacheStore(Path(d) / "kv.sqlite", embedding_enabled=True)
        store.set("ns", "k1", "tests pasan en main")
        store.set("ns", "k2", "docker version 24")
        yield store


def test_kv_search_raises_without_store() -> None:
    kv_mod._store = None
    kv_mod._embedder = None
    with pytest.raises(RuntimeError):
        kv_search("algo")


def test_kv_search_uses_bm25_when_no_embedder(populated_store: SQLiteKVCacheStore) -> None:
    kv_mod._store = populated_store
    kv_mod._embedder = None
    result = kv_search("tests")
    assert result["method"] == "bm25"
    assert any(r["key"] == "k1" for r in result["results"])


def test_kv_search_uses_embedding_when_available(populated_store: SQLiteKVCacheStore) -> None:
    populated_store.set_embedding("ns", "k1", [1.0, 0.0], model="m")
    populated_store.set_embedding("ns", "k2", [0.0, 1.0], model="m")

    embedder = MagicMock()
    embedder.embed.return_value = [1.0, 0.0]
    embedder.model = "m"

    kv_mod._store = populated_store
    kv_mod._embedder = embedder

    result = kv_search("tests pasan")
    assert result["method"] == "embedding"
    assert result["results"][0]["key"] == "k1"


def test_kv_search_falls_back_to_bm25_on_embedding_error(populated_store: SQLiteKVCacheStore) -> None:
    populated_store.set_embedding("ns", "k1", [1.0, 0.0], model="m")

    embedder = MagicMock()
    embedder.embed.side_effect = EmbeddingUnavailableError("offline")
    embedder.model = "m"

    kv_mod._store = populated_store
    kv_mod._embedder = embedder

    result = kv_search("tests")
    assert result["method"] == "bm25"


def test_kv_search_respects_namespace(populated_store: SQLiteKVCacheStore) -> None:
    populated_store.set("otro", "k9", "aislado")
    kv_mod._store = populated_store
    kv_mod._embedder = None

    result = kv_search("aislado", namespace="otro")
    namespaces = {r["namespace"] for r in result["results"]}
    assert namespaces <= {"otro"}
