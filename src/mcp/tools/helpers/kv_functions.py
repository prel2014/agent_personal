from __future__ import annotations

from typing import Any

from src.mcp.cache import SQLiteKVCacheStore
from src.mcp.cache.embedder import EmbeddingClient, EmbeddingUnavailableError, build_embed_text


_store: SQLiteKVCacheStore | None = None
_embedder: EmbeddingClient | None = None


def configure_kv_store(
    db_path: str | None,
    *,
    enabled: bool = True,
    embedding_enabled: bool = False,
    embedding_model: str = "nomic-embed-text",
    embedding_ollama_url: str | None = None,
) -> None:
    global _store, _embedder
    if enabled and db_path:
        _store = SQLiteKVCacheStore(db_path, embedding_enabled=embedding_enabled)
        if embedding_enabled:
            _embedder = EmbeddingClient(
                base_url=embedding_ollama_url or "http://127.0.0.1:11434",
                model=embedding_model,
            )
        else:
            _embedder = None
    else:
        _store = None
        _embedder = None


def _get_store() -> SQLiteKVCacheStore | None:
    return _store


def _get_embedder() -> EmbeddingClient | None:
    return _embedder


def _require_store() -> SQLiteKVCacheStore:
    if _store is None:
        raise RuntimeError("KV cache no esta configurado o esta deshabilitado.")
    return _store


def kv_get(namespace: str, key: str) -> dict[str, Any]:
    return _require_store().get(namespace, key)


def kv_list(
    namespace: str | None = None,
    prefix: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    return _require_store().list(namespace=namespace, prefix=prefix, limit=limit)


def kv_set(
    namespace: str,
    key: str,
    value: Any,
    ttl_seconds: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    store = _require_store()
    result = store.set(namespace, key, value, ttl_seconds=ttl_seconds, metadata=metadata)

    if _embedder is not None:
        try:
            text = build_embed_text(namespace, key, value)
            vector = _embedder.embed(text)
            store.set_embedding(namespace, key, vector, model=_embedder.model)
            result["embedded"] = True
        except EmbeddingUnavailableError:
            result["embedded"] = False
            result["embedding_error"] = "ollama_unavailable"
        except Exception:
            result["embedded"] = False

    return result


def kv_delete(namespace: str, key: str) -> dict[str, Any]:
    return _require_store().delete(namespace, key)


def kv_clear_expired(namespace: str | None = None) -> dict[str, Any]:
    return _require_store().clear(namespace=namespace, expired_only=True)
