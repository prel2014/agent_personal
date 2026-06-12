from __future__ import annotations

import json
import math
import re
import socket
import urllib.request
from collections import Counter
from typing import Any
from urllib.error import HTTPError, URLError


class EmbeddingUnavailableError(RuntimeError):
    """Ollama no accesible o fallo al generar embedding. El caller la captura silenciosamente."""


class EmbeddingClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "nomic-embed-text",
        timeout: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def embed(self, text: str) -> list[float]:
        url = self._embeddings_url()
        body = json.dumps({"model": self.model, "prompt": text}).encode("utf-8")
        request = urllib.request.Request(
            url=url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            vector = payload.get("embedding")
            if not isinstance(vector, list) or not vector:
                raise EmbeddingUnavailableError(
                    f"Respuesta inesperada del endpoint de embeddings: {list(payload.keys())}"
                )
            return vector
        except (HTTPError, URLError, socket.timeout, TimeoutError) as exc:
            raise EmbeddingUnavailableError(f"Ollama no disponible ({url}): {exc}") from exc
        except (KeyError, json.JSONDecodeError, ValueError) as exc:
            raise EmbeddingUnavailableError(f"Respuesta invalida de Ollama: {exc}") from exc

    def _embeddings_url(self) -> str:
        if self.base_url.endswith("/api"):
            return f"{self.base_url}/embeddings"
        return f"{self.base_url}/api/embeddings"


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class BM25Ranker:
    """BM25 minimalista — solo stdlib, sin numpy."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b

    def rank(
        self,
        query: str,
        documents: list[tuple[str, str, str]],
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[tuple[str, str, float]]:
        """Rankea documentos por BM25.

        Args:
            documents: lista de (namespace, key, text_to_rank)
            Returns: [(namespace, key, score), ...] ordenado desc, filtrado por min_score
        """
        if not documents:
            return []

        query_tokens = self.tokenize(query)
        if not query_tokens:
            return []

        tokenized_docs = [self.tokenize(doc[2]) for doc in documents]
        avg_dl = sum(len(tokens) for tokens in tokenized_docs) / len(tokenized_docs)

        df: Counter[str] = Counter()
        for tokens in tokenized_docs:
            for term in set(tokens):
                df[term] += 1

        n = len(documents)
        scores: list[tuple[str, str, float]] = []
        for i, (ns, key, _) in enumerate(documents):
            tokens = tokenized_docs[i]
            tf_map = Counter(tokens)
            dl = len(tokens)
            score = 0.0
            for term in query_tokens:
                if term not in tf_map:
                    continue
                tf = tf_map[term]
                idf = math.log((n - df[term] + 0.5) / (df[term] + 0.5) + 1.0)
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * dl / avg_dl)
                score += idf * (numerator / denominator)
            if score >= min_score:
                scores.append((ns, key, score))

        scores.sort(key=lambda x: x[2], reverse=True)
        return scores[:top_k]

    @staticmethod
    def tokenize(text: str) -> list[str]:
        return [t for t in re.split(r"[^a-zA-Z0-9À-ɏ]+", text.lower()) if len(t) >= 2]


def build_embed_text(namespace: str, key: str, value: Any) -> str:
    value_str = (
        value
        if isinstance(value, str)
        else json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    )
    return f"namespace: {namespace} | key: {key} | value: {value_str}"
