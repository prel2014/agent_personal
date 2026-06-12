from __future__ import annotations

import pytest

from src.mcp.cache.embedder import BM25Ranker


def _docs(*texts: str) -> list[tuple[str, str, str]]:
    return [("ns", f"k{i}", t) for i, t in enumerate(texts)]


def test_tokenizer_lowercases() -> None:
    tokens = BM25Ranker.tokenize("Hello World")
    assert "hello" in tokens
    assert "world" in tokens


def test_tokenizer_excludes_short_tokens() -> None:
    tokens = BM25Ranker.tokenize("a ab abc")
    assert "a" not in tokens
    assert "ab" in tokens


def test_ranks_relevant_doc_higher() -> None:
    docs = _docs("python tests pasan", "docker version 24")
    result = BM25Ranker().rank("python tests", docs, top_k=2)
    assert result[0][1] == "k0"


def test_respects_top_k() -> None:
    docs = _docs("alpha", "beta", "gamma")
    result = BM25Ranker().rank("alpha", docs, top_k=1)
    assert len(result) == 1


def test_respects_min_score() -> None:
    docs = _docs("completamente irrelevante xyz", "python test")
    result = BM25Ranker().rank("python", docs, min_score=0.5)
    keys = [r[1] for r in result]
    assert "k1" in keys


def test_empty_corpus_returns_empty() -> None:
    assert BM25Ranker().rank("query", []) == []


def test_no_matching_terms_score_zero() -> None:
    docs = _docs("xyz abc")
    result = BM25Ranker().rank("python", docs, min_score=0.001)
    assert result == []
