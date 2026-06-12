from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

from src.mcp.cache.embedder import EmbeddingClient, EmbeddingUnavailableError


def _mock_response(vector: list[float]):
    body = json.dumps({"embedding": vector}).encode()
    resp = MagicMock()
    resp.read.return_value = body
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def test_embeddings_url_without_api_suffix() -> None:
    client = EmbeddingClient(base_url="http://localhost:11434")
    assert client._embeddings_url() == "http://localhost:11434/api/embeddings"


def test_embeddings_url_with_api_suffix() -> None:
    client = EmbeddingClient(base_url="http://localhost:11434/api")
    assert client._embeddings_url() == "http://localhost:11434/api/embeddings"


def test_embed_returns_vector_on_success() -> None:
    client = EmbeddingClient()
    with patch("urllib.request.urlopen", return_value=_mock_response([0.1, 0.2, 0.3])):
        result = client.embed("hola mundo")
    assert result == pytest.approx([0.1, 0.2, 0.3])


def test_embed_raises_on_http_error() -> None:
    client = EmbeddingClient()
    with patch("urllib.request.urlopen", side_effect=HTTPError(None, 500, "Error", {}, None)):
        with pytest.raises(EmbeddingUnavailableError):
            client.embed("texto")


def test_embed_raises_on_url_error() -> None:
    client = EmbeddingClient()
    with patch("urllib.request.urlopen", side_effect=URLError("connection refused")):
        with pytest.raises(EmbeddingUnavailableError):
            client.embed("texto")


def test_embed_raises_on_missing_embedding_key() -> None:
    body = json.dumps({"other_key": []}).encode()
    resp = MagicMock()
    resp.read.return_value = body
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    client = EmbeddingClient()
    with patch("urllib.request.urlopen", return_value=resp):
        with pytest.raises(EmbeddingUnavailableError):
            client.embed("texto")


def test_embed_raises_on_empty_vector() -> None:
    client = EmbeddingClient()
    with patch("urllib.request.urlopen", return_value=_mock_response([])):
        with pytest.raises(EmbeddingUnavailableError):
            client.embed("texto")
