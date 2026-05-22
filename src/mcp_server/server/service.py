from __future__ import annotations

from queue import Empty, Queue
from threading import Thread
from typing import Any, Callable

from src.mcp_shared.contracts import ChatRequest, ChatResponse

from ..nodes import NodeProbeResult
from ..ollama import OllamaChatClient
from .streaming import _heartbeat_chunk, _stream_heartbeat_interval

DiscoveryProgressCallback = Callable[[str, str, NodeProbeResult | None], None]


class OrchestratorService:
    def __init__(self, config):
        self.config = config
        self.ollama = OllamaChatClient(config)

    def startup_discovery_report(
        self,
        progress_callback: DiscoveryProgressCallback | None = None,
    ) -> dict[str, object]:
        registry = self.ollama.node_registry
        if not registry.discovery_settings.enabled:
            return {
                "enabled": False,
                "candidate_count": 0,
                "reachable_count": 0,
                "promoted_count": 0,
                "reachable": [],
            }

        candidates = registry.candidate_base_urls()
        results = registry.refresh_discovery(
            force=True,
            progress_callback=progress_callback,
        )
        reachable = [result for result in results if result.reachable]
        promoted_count = int(
            registry.summary().get("auto_promotion", {}).get("promoted_node_count", 0)
        )
        return {
            "enabled": True,
            "candidate_count": len(candidates),
            "reachable_count": len(reachable),
            "promoted_count": promoted_count,
            "reachable": [result.to_dict() for result in reachable],
        }

    def info(self) -> dict[str, object]:
        return {
            **self.config.to_dict(),
            "nodes": self.ollama.node_registry.list_nodes(),
            "routing": self.ollama.node_registry.summary(),
        }

    def health(self) -> dict[str, object]:
        return {
            "ok": True,
            "service": "mcp_server",
            "model": self.ollama.node_registry.local_node.model,
            "configured_model": self.config.ollama_model,
            "ollama_base_url": self.config.ollama_base_url,
            "nodes": self.ollama.node_registry.list_nodes(),
        }

    def nodes(self) -> dict[str, object]:
        return {
            "ok": True,
            "discovery": self.ollama.node_registry.summary().get("discovery"),
            "nodes": self.ollama.node_registry.list_nodes(),
            "routing": self.ollama.node_registry.summary(),
        }

    def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = ChatRequest.from_wire(payload)
        response = self.ollama.chat(
            messages=[message.to_wire() for message in request.messages],
            tools=request.tools,
            client_context=request.client_context,
        )
        return ChatResponse.from_ollama(
            response,
            default_model=self.config.ollama_model,
        ).to_wire()

    def chat_stream(self, payload: dict[str, Any]):
        request = ChatRequest.from_wire(payload)
        yield _heartbeat_chunk()

        queue: Queue[tuple[str, Any]] = Queue()

        def worker() -> None:
            try:
                for chunk in self.ollama.chat_stream(
                    messages=[message.to_wire() for message in request.messages],
                    tools=request.tools,
                    client_context=request.client_context,
                ):
                    queue.put(
                        (
                            "chunk",
                            ChatResponse.from_ollama(
                                chunk,
                                default_model=self.config.ollama_model,
                            ).to_wire(),
                        )
                    )
            except Exception as exc:
                queue.put(("error", exc))
            finally:
                queue.put(("done", None))

        Thread(target=worker, daemon=True).start()

        heartbeat_interval = _stream_heartbeat_interval(self.config.request_timeout)
        while True:
            try:
                event, value = queue.get(timeout=heartbeat_interval)
            except Empty:
                yield _heartbeat_chunk()
                continue

            if event == "chunk":
                yield value
                continue

            if event == "error":
                raise value

            if event == "done":
                break
