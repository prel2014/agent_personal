from __future__ import annotations

import json
import socket
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .models import NodeProbeResult

class OllamaNodeProbe:
    def __init__(self, timeout: float = 1.5):
        self.timeout = timeout

    def probe(self, base_url: str) -> NodeProbeResult:
        tags_url = self._tags_url(base_url)
        request = Request(
            url=tags_url,
            headers={"Accept": "application/json"},
            method="GET",
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            return NodeProbeResult(
                base_url=base_url,
                reachable=False,
                error=f"HTTP {exc.code}",
            )
        except (TimeoutError, socket.timeout):
            return NodeProbeResult(
                base_url=base_url,
                reachable=False,
                error="timeout",
            )
        except URLError as exc:
            return NodeProbeResult(
                base_url=base_url,
                reachable=False,
                error=str(exc.reason),
            )
        except json.JSONDecodeError:
            return NodeProbeResult(
                base_url=base_url,
                reachable=False,
                error="invalid_json",
            )

        raw_models = payload.get("models", [])
        available_models: list[str] = []
        if isinstance(raw_models, list):
            for item in raw_models:
                if isinstance(item, dict):
                    name = item.get("name")
                    if isinstance(name, str) and name.strip():
                        available_models.append(name.strip())

        return NodeProbeResult(
            base_url=base_url,
            reachable=True,
            available_models=tuple(available_models),
        )

    @staticmethod
    def _tags_url(base_url: str) -> str:
        normalized = base_url.rstrip("/")
        if normalized.endswith("/api"):
            return f"{normalized}/tags"
        return f"{normalized}/api/tags"
