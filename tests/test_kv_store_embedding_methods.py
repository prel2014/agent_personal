from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.mcp.cache.store import SQLiteKVCacheStore


@pytest.fixture
def store() -> SQLiteKVCacheStore:
    with tempfile.TemporaryDirectory() as d:
        s = SQLiteKVCacheStore(Path(d) / "kv.sqlite", embedding_enabled=True)
        s.set("ns", "k1", "valor uno")
        s.set("ns", "k2", "valor dos")
        s.set("ns2", "k3", "otro")
        yield s


def test_set_get_embedding_roundtrip(store: SQLiteKVCacheStore) -> None:
    vector = [0.1, 0.2, 0.3]
    store.set_embedding("ns", "k1", vector, model="m")
    result = store.get_embedding("ns", "k1")
    assert result == pytest.approx(vector)


def test_get_embedding_returns_none_for_missing(store: SQLiteKVCacheStore) -> None:
    assert store.get_embedding("ns", "noexiste") is None


def test_delete_embedding_removes_it(store: SQLiteKVCacheStore) -> None:
    store.set_embedding("ns", "k1", [0.1, 0.2], model="m")
    store.delete_embedding("ns", "k1")
    assert store.get_embedding("ns", "k1") is None


def test_has_embeddings_false_when_empty(store: SQLiteKVCacheStore) -> None:
    assert store.has_embeddings() is False


def test_has_embeddings_true_after_set(store: SQLiteKVCacheStore) -> None:
    store.set_embedding("ns", "k1", [0.1, 0.2], model="m")
    assert store.has_embeddings() is True


def test_has_embeddings_namespace_filter(store: SQLiteKVCacheStore) -> None:
    store.set_embedding("ns", "k1", [0.1, 0.2], model="m")
    assert store.has_embeddings(namespace="ns") is True
    assert store.has_embeddings(namespace="ns2") is False


def test_set_embedding_updates_existing(store: SQLiteKVCacheStore) -> None:
    store.set_embedding("ns", "k1", [0.1, 0.2], model="m1")
    store.set_embedding("ns", "k1", [0.9, 0.8], model="m2")
    result = store.get_embedding("ns", "k1")
    assert result == pytest.approx([0.9, 0.8])


def test_search_by_embedding_returns_ranked(store: SQLiteKVCacheStore) -> None:
    store.set_embedding("ns", "k1", [1.0, 0.0], model="m")
    store.set_embedding("ns", "k2", [0.0, 1.0], model="m")
    result = store.search_by_embedding([0.99, 0.01], namespace="ns", top_k=2, model="m")
    assert result["method"] == "embedding"
    assert len(result["results"]) >= 1
    assert result["results"][0]["key"] == "k1"


def test_search_by_embedding_respects_top_k(store: SQLiteKVCacheStore) -> None:
    store.set_embedding("ns", "k1", [1.0, 0.0], model="m")
    store.set_embedding("ns", "k2", [0.9, 0.1], model="m")
    result = store.search_by_embedding([1.0, 0.0], namespace="ns", top_k=1, model="m")
    assert len(result["results"]) == 1


def test_search_by_embedding_respects_min_score(store: SQLiteKVCacheStore) -> None:
    store.set_embedding("ns", "k1", [1.0, 0.0], model="m")
    store.set_embedding("ns", "k2", [0.0, 1.0], model="m")
    result = store.search_by_embedding([1.0, 0.0], namespace="ns", min_score=0.99, model="m")
    keys = [r["key"] for r in result["results"]]
    assert "k2" not in keys


def test_search_by_embedding_respects_namespace(store: SQLiteKVCacheStore) -> None:
    store.set_embedding("ns", "k1", [1.0, 0.0], model="m")
    store.set_embedding("ns2", "k3", [1.0, 0.0], model="m")
    result = store.search_by_embedding([1.0, 0.0], namespace="ns", model="m")
    namespaces = {r["namespace"] for r in result["results"]}
    assert namespaces == {"ns"}


def test_search_by_bm25_ranks_by_relevance(store: SQLiteKVCacheStore) -> None:
    result = store.search_by_bm25("valor uno")
    assert result["method"] == "bm25"
    assert len(result["results"]) >= 1
    assert result["results"][0]["key"] == "k1"


def test_search_by_bm25_respects_namespace(store: SQLiteKVCacheStore) -> None:
    result = store.search_by_bm25("valor", namespace="ns2")
    namespaces = {r["namespace"] for r in result["results"]}
    assert namespaces <= {"ns2"}
