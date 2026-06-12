from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import src.mcp.tools.helpers.kv_functions as kv_mod
from src.mcp.cache.embedder import EmbeddingUnavailableError
from src.mcp.cache.store import SQLiteKVCacheStore
from src.mcp.tools.helpers.kv_functions import kv_delete, kv_set


@pytest.fixture(autouse=True)
def reset_globals():
    original_store = kv_mod._store
    original_embedder = kv_mod._embedder
    yield
    kv_mod._store = original_store
    kv_mod._embedder = original_embedder


def test_kv_set_embeds_when_embedder_available() -> None:
    with tempfile.TemporaryDirectory() as d:
        embedder = MagicMock()
        embedder.embed.return_value = [0.1, 0.2, 0.3]
        embedder.model = "test-model"

        store = SQLiteKVCacheStore(Path(d) / "kv.sqlite", embedding_enabled=True)
        kv_mod._store = store
        kv_mod._embedder = embedder

        result = kv_set("ns", "k1", "valor")
        assert result["stored"] is True
        assert result.get("embedded") is True
        assert store.get_embedding("ns", "k1") == pytest.approx([0.1, 0.2, 0.3])


def test_kv_set_embedded_false_when_ollama_unavailable() -> None:
    with tempfile.TemporaryDirectory() as d:
        embedder = MagicMock()
        embedder.embed.side_effect = EmbeddingUnavailableError("offline")
        embedder.model = "m"

        store = SQLiteKVCacheStore(Path(d) / "kv.sqlite", embedding_enabled=True)
        kv_mod._store = store
        kv_mod._embedder = embedder

        result = kv_set("ns", "k1", "valor")
        assert result["stored"] is True
        assert result.get("embedded") is False
        assert result.get("embedding_error") == "ollama_unavailable"


def test_kv_set_no_embedded_field_when_no_embedder() -> None:
    with tempfile.TemporaryDirectory() as d:
        store = SQLiteKVCacheStore(Path(d) / "kv.sqlite", embedding_enabled=False)
        kv_mod._store = store
        kv_mod._embedder = None

        result = kv_set("ns", "k1", "valor")
        assert result["stored"] is True
        assert "embedded" not in result


def test_kv_set_updates_embedding_on_reset() -> None:
    with tempfile.TemporaryDirectory() as d:
        embedder = MagicMock()
        embedder.model = "m"
        embedder.embed.return_value = [0.5, 0.5]

        store = SQLiteKVCacheStore(Path(d) / "kv.sqlite", embedding_enabled=True)
        kv_mod._store = store
        kv_mod._embedder = embedder

        kv_set("ns", "k1", "original")
        embedder.embed.return_value = [0.9, 0.1]
        kv_set("ns", "k1", "actualizado")

        vector = store.get_embedding("ns", "k1")
        assert vector == pytest.approx([0.9, 0.1])


def test_kv_delete_removes_embedding() -> None:
    with tempfile.TemporaryDirectory() as d:
        store = SQLiteKVCacheStore(Path(d) / "kv.sqlite", embedding_enabled=True)
        store.set("ns", "k1", "valor")
        store.set_embedding("ns", "k1", [0.1, 0.2], model="m")
        kv_mod._store = store
        kv_mod._embedder = None

        kv_delete("ns", "k1")
        assert store.get_embedding("ns", "k1") is None
