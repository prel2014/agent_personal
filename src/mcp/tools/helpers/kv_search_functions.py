from __future__ import annotations

from typing import Any

from src.mcp.cache.embedder import EmbeddingUnavailableError
from .kv_functions import _get_embedder, _get_store, _require_store


def kv_search(
    query: str,
    namespace: str | None = None,
    top_k: int = 5,
    min_score: float = 0.0,
) -> dict[str, Any]:
    """Busca entradas del KV cache por similitud semantica o texto (BM25 fallback)."""
    store = _require_store()
    embedder = _get_embedder()

    if embedder is not None and store.has_embeddings(namespace=namespace):
        try:
            vector = embedder.embed(query)
            return store.search_by_embedding(
                vector,
                namespace=namespace,
                top_k=top_k,
                min_score=min_score,
                model=embedder.model,
            )
        except EmbeddingUnavailableError:
            pass

    return store.search_by_bm25(
        query,
        namespace=namespace,
        top_k=top_k,
        min_score=min_score,
    )
