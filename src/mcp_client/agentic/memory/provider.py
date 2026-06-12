from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .store import MemoryStore


@dataclass
class MemoryContextProvider:
    """Combina memorias de proyecto y usuario para inyectar en el contexto del agente."""

    project_store: MemoryStore | None = None
    user_store: MemoryStore | None = None
    top_k: int = 3

    def recall(self, query: str) -> list[dict[str, Any]]:
        """Devuelve hasta top_k memorias relevantes, deduplicando por key (proyecto tiene prioridad)."""
        seen_keys: set[str] = set()
        combined: list[dict[str, Any]] = []

        for store in (self.project_store, self.user_store):
            if store is None:
                continue
            results = store.search(query, top_k=self.top_k)
            for entry in results:
                key = entry.get("key", "")
                if key and key not in seen_keys:
                    seen_keys.add(key)
                    combined.append(entry)

        combined.sort(key=lambda e: e.get("score", 0.0), reverse=True)
        return combined[: self.top_k]

    def is_empty(self) -> bool:
        return self.project_store is None and self.user_store is None

    def to_context_entries(self, query: str) -> list[dict[str, Any]]:
        """Retorna entradas simplificadas para inyectar en el wire context."""
        memories = self.recall(query)
        return [
            {"key": m.get("key", ""), "value": m.get("value", "")}
            for m in memories
            if m.get("key") and m.get("value")
        ]
