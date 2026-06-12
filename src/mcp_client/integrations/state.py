from __future__ import annotations

from pathlib import Path
from typing import Any

from src.mcp.cache import SQLiteKVCacheStore
from ..transport import MCPOrchestratorAPI


class ClientCacheMixin:
    kv_cache: SQLiteKVCacheStore | None

    def cache_get(self, namespace: str, key: str) -> dict[str, Any]:
        return self._require_kv_cache().get(namespace, key)

    def cache_set(
        self,
        namespace: str,
        key: str,
        value: Any,
        *,
        ttl_seconds: int | None = None,
    ) -> dict[str, Any]:
        return self._require_kv_cache().set(namespace, key, value, ttl_seconds=ttl_seconds)

    def cache_delete(self, namespace: str, key: str) -> dict[str, Any]:
        return self._require_kv_cache().delete(namespace, key)

    def cache_list(
        self,
        *,
        namespace: str | None = None,
        prefix: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        return self._require_kv_cache().list(
            namespace=namespace,
            prefix=prefix,
            limit=limit,
        )

    def cache_clear(
        self,
        *,
        namespace: str | None = None,
        expired_only: bool = False,
    ) -> dict[str, Any]:
        return self._require_kv_cache().clear(
            namespace=namespace,
            expired_only=expired_only,
        )

    def cache_search(
        self,
        query: str,
        *,
        namespace: str | None = None,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> dict[str, Any]:
        return self.runtime.call_tool(
            "kv_search",
            {"query": query, "namespace": namespace, "top_k": top_k, "min_score": min_score},
        )

    def _require_kv_cache(self) -> SQLiteKVCacheStore:
        if self.kv_cache is None:
            raise RuntimeError("KV cache esta deshabilitado.")
        return self.kv_cache


class ClientSessionsMixin:
    def list_sessions(self, *, limit: int = 20) -> list[dict[str, Any]]:
        return [
            session.to_dict()
            for session in self.session_store.list_sessions(limit=limit)
        ]

    def show_session(self, session_id: str) -> dict[str, Any]:
        session = self.session_store.require_session(session_id)
        return {
            **session.to_dict(),
            "messages": self.session_store.load_messages(session_id),
        }

    def rename_session(self, session_id: str, title: str) -> dict[str, Any]:
        self.session_store.rename_session(session_id, title)
        return self.session_store.require_session(session_id).to_dict()

    def close_session(self, session_id: str) -> dict[str, Any]:
        self.session_store.close_session(session_id)
        return self.session_store.require_session(session_id).to_dict()


class ClientLifecycleMixin:
    def setup(self) -> dict[str, Any]:
        trace_dir = None
        if self.config.trace_db_path:
            trace_dir = str(Path(self.config.trace_db_path).expanduser().parent)
            Path(trace_dir).mkdir(parents=True, exist_ok=True)
        kv_cache_dir = None
        if self.config.kv_cache_enabled:
            kv_cache = SQLiteKVCacheStore(self.config.kv_cache_db_path)
            kv_cache_dir = str(kv_cache.db_path.parent)
        return {
            "ok": True,
            "session_db_path": str(self.session_store.db_path),
            "session_dir": str(self.session_store.db_path.parent),
            "trace_db_path": self.config.trace_db_path,
            "trace_dir": trace_dir,
            "kv_cache_enabled": self.config.kv_cache_enabled,
            "kv_cache_db_path": self.config.kv_cache_db_path,
            "kv_cache_dir": kv_cache_dir,
        }

    def doctor(self) -> dict[str, Any]:
        checks: list[dict[str, Any]] = []
        checks.append(
            {
                "name": "session_db",
                "ok": self.session_store.db_path.exists(),
                "detail": str(self.session_store.db_path),
            }
        )
        checks.append(
            {
                "name": "base_dir",
                "ok": self.runtime.config.base_dir.exists(),
                "detail": str(self.runtime.config.base_dir),
            }
        )
        checks.append(
            {
                "name": "permissions",
                "ok": True,
                "detail": self.runtime.info()["permissions"],
            }
        )
        try:
            probe = MCPOrchestratorAPI(
                self.config.server_url,
                timeout=min(float(self.config.request_timeout), 3.0),
                bearer_token=self.config.server_bearer_token,
            ).health()
            checks.append(
                {
                    "name": "server",
                    "ok": bool(probe.get("ok", True)),
                    "detail": probe,
                }
            )
        except Exception as exc:
            checks.append(
                {
                    "name": "server",
                    "ok": False,
                    "detail": str(exc),
                }
            )

        if self.config.trace_db_path:
            trace_parent = Path(self.config.trace_db_path).expanduser().parent
            checks.append(
                {
                    "name": "trace_db_parent",
                    "ok": trace_parent.exists(),
                    "detail": str(trace_parent),
                }
            )

        if self.config.kv_cache_enabled:
            try:
                kv_cache = SQLiteKVCacheStore(self.config.kv_cache_db_path)
                checks.append(
                    {
                        "name": "kv_cache",
                        "ok": kv_cache.db_path.exists(),
                        "detail": str(kv_cache.db_path),
                    }
                )
            except Exception as exc:
                checks.append(
                    {
                        "name": "kv_cache",
                        "ok": False,
                        "detail": str(exc),
                    }
                )

        return {
            "ok": all(bool(check["ok"]) for check in checks),
            "checks": checks,
        }
