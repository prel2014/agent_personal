import json
import socket
from typing import Any, Iterator
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .errors import (
    MCPServerConnectionError,
    MCPServerResponseError,
    MCPServerTimeoutError,
)


class MCPOrchestratorAPI:
    def __init__(
        self,
        server_url: str,
        timeout: float = 120.0,
        bearer_token: str | None = None,
    ):
        self.server_url = server_url.rstrip("/")
        self.timeout = timeout
        self.bearer_token = bearer_token

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def nodes(self) -> dict[str, Any]:
        return self._request("GET", "/nodes")

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        client_context: dict[str, Any],
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/chat",
            {
                "messages": messages,
                "tools": tools,
                "client_context": client_context,
            },
        )

    def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        client_context: dict[str, Any],
    ) -> Iterator[dict[str, Any]]:
        payload = {
            "messages": messages,
            "tools": tools,
            "client_context": client_context,
            "stream": True,
        }
        yield from self._stream_request("POST", "/v1/chat", payload)

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._open_request(
            method=method,
            path=path,
            payload=payload,
            accept="application/json",
        ) as response:
            return json.loads(response.read().decode("utf-8"))

    def _stream_request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> Iterator[dict[str, Any]]:
        with self._open_request(
            method=method,
            path=path,
            payload=payload,
            accept="application/x-ndjson, application/json",
        ) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue

                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    raise MCPServerResponseError(
                        f"Servidor devolvio una linea de streaming invalida: {line[:200]}"
                    ) from exc

    def _open_request(
        self,
        *,
        method: str,
        path: str,
        accept: str,
        payload: dict[str, Any] | None = None,
    ):
        body = None
        headers = {"Accept": accept}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"

        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = Request(
            url=f"{self.server_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )

        try:
            return urlopen(request, timeout=self.timeout)
        except HTTPError as exc:
            raise MCPServerResponseError(
                f"Servidor respondio {exc.code}: {self._read_http_error(exc)}"
            ) from exc
        except (TimeoutError, socket.timeout) as exc:
            raise MCPServerTimeoutError(
                f"mcp_server no respondio en {self.timeout:.0f} segundos. "
                "Aumenta --request-timeout o revisa el timeout del servidor/Ollama."
            ) from exc
        except URLError as exc:
            raise MCPServerConnectionError(
                f"No se pudo conectar al servidor: {exc.reason}"
            ) from exc

    @staticmethod
    def _read_http_error(exc: HTTPError) -> Any:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(detail)
        except json.JSONDecodeError:
            return detail

        return payload.get("error") or payload
