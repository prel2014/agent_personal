from __future__ import annotations

from typing import Any

from src.mcp.cache import SQLiteKVCacheStore


_store: SQLiteKVCacheStore | None = None


def configure_kv_store(db_path: str | None, *, enabled: bool = True) -> None:
    global _store
    _store = SQLiteKVCacheStore(db_path) if enabled and db_path else None


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
    return _require_store().set(
        namespace,
        key,
        value,
        ttl_seconds=ttl_seconds,
        metadata=metadata,
    )


def kv_delete(namespace: str, key: str) -> dict[str, Any]:
    return _require_store().delete(namespace, key)


def kv_clear_expired(namespace: str | None = None) -> dict[str, Any]:
    return _require_store().clear(namespace=namespace, expired_only=True)
