from __future__ import annotations

from pathlib import Path
from typing import Any

from src.mcp.cache.store import SQLiteKVCacheStore
from src.mcp.cache.embedder import EmbeddingClient, EmbeddingUnavailableError

_NAMESPACE = "memories"


class MemoryStore:
    """Almacén de memoria persistente (proyecto o usuario) sobre SQLiteKVCacheStore."""

    def __init__(
        self,
        db_path: str | Path,
        *,
        embedding_enabled: bool = False,
        ollama_url: str = "http://127.0.0.1:11434",
        embedding_model: str = "nomic-embed-text",
    ) -> None:
        self._store = SQLiteKVCacheStore(db_path, embedding_enabled=embedding_enabled)
        self._embedder: EmbeddingClient | None = (
            EmbeddingClient(base_url=ollama_url, model=embedding_model)
            if embedding_enabled
            else None
        )

    def remember(
        self,
        key: str,
        value: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = self._store.set(_NAMESPACE, key, value, metadata=metadata)
        if self._embedder is not None:
            try:
                from src.mcp.cache.embedder import build_embed_text
                text = build_embed_text(_NAMESPACE, key, value)
                vector = self._embedder.embed(text)
                self._store.set_embedding(
                    _NAMESPACE, key, vector, model=self._embedder.model
                )
                result = {**result, "embedded": True}
            except EmbeddingUnavailableError:
                result = {**result, "embedded": False}
        return result

    def forget(self, key: str) -> dict[str, Any]:
        return self._store.delete(_NAMESPACE, key)

    def list_memories(self, *, limit: int = 100) -> list[dict[str, Any]]:
        result = self._store.list(namespace=_NAMESPACE, limit=limit)
        return result.get("entries", [])

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        if self._embedder is not None and self._store.has_embeddings(namespace=_NAMESPACE):
            try:
                vector = self._embedder.embed(query)
                result = self._store.search_by_embedding(
                    vector,
                    namespace=_NAMESPACE,
                    top_k=top_k,
                    min_score=min_score,
                    model=self._embedder.model,
                )
                return self._flatten_results(result.get("results", []))
            except EmbeddingUnavailableError:
                pass
        result = self._store.search_by_bm25(
            query,
            namespace=_NAMESPACE,
            top_k=top_k,
            min_score=min_score,
        )
        return self._flatten_results(result.get("results", []))

    @staticmethod
    def _flatten_results(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Aplana el campo 'entry' al nivel superior para acceso uniforme a key/value."""
        out = []
        for item in raw:
            entry = item.get("entry") or {}
            flat: dict[str, Any] = {
                "key": item.get("key", entry.get("key", "")),
                "value": entry.get("value", item.get("value", "")),
                "score": item.get("score", 0.0),
                "namespace": item.get("namespace", entry.get("namespace", "")),
            }
            out.append(flat)
        return out
