from __future__ import annotations

import json
import socket
from typing import Any, Iterator
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class OllamaAPIError(RuntimeError):
    def __init__(
        self,
        message: str,
        status_code: int = 502,
        *,
        retryable: bool = False,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


class OllamaHTTPTransport:
    def __init__(self, timeout: float) -> None:
        self.timeout = timeout

    def post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            url=url,
            data=body,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise OllamaAPIError(
                f"Ollama respondio {exc.code}: {detail}",
                retryable=False,
            ) from exc
        except (TimeoutError, socket.timeout) as exc:
            raise OllamaAPIError(
                f"Ollama no respondio en {self.timeout:.0f} segundos.",
                status_code=504,
                retryable=True,
            ) from exc
        except URLError as exc:
            raise OllamaAPIError(
                f"No se pudo conectar a Ollama: {exc.reason}",
                retryable=True,
            ) from exc

    def post_ndjson(self, url: str, payload: dict[str, Any]) -> Iterator[dict[str, Any]]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            url=url,
            data=body,
            headers={
                "Accept": "application/x-ndjson, application/json",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue

                    yield json.loads(line)
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise OllamaAPIError(
                f"Ollama respondio {exc.code}: {detail}",
                retryable=False,
            ) from exc
        except (TimeoutError, socket.timeout) as exc:
            raise OllamaAPIError(
                f"Ollama no respondio en {self.timeout:.0f} segundos.",
                status_code=504,
                retryable=True,
            ) from exc
        except URLError as exc:
            raise OllamaAPIError(
                f"No se pudo conectar a Ollama: {exc.reason}",
                retryable=True,
            ) from exc
