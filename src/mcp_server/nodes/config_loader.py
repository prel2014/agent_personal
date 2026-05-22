from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.mcp_shared.urls import normalize_http_url

from ..settings import parse_think
from .models import OllamaNodeConfig, _normalize_roles


def load_extra_nodes(config_path: str | None) -> list[OllamaNodeConfig]:
    if not config_path:
        return []

    path = Path(config_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_nodes = payload.get("nodes") if isinstance(payload, dict) else payload
    if not isinstance(raw_nodes, list):
        raise ValueError("El archivo de nodos debe contener una lista o {'nodes': [...]}.")

    return [_node_from_payload(raw_node) for raw_node in raw_nodes]


def _node_from_payload(raw_node: Any) -> OllamaNodeConfig:
    if not isinstance(raw_node, dict):
        raise ValueError("Cada nodo debe ser un objeto JSON.")

    node_id = raw_node.get("id") or raw_node.get("node_id")
    if not isinstance(node_id, str) or not node_id.strip():
        raise ValueError("Cada nodo debe definir 'id'.")

    model = raw_node.get("model")
    if not isinstance(model, str) or not model.strip():
        raise ValueError(f"El nodo '{node_id}' debe definir 'model'.")

    raw_base_url = raw_node.get("base_url")
    if not isinstance(raw_base_url, str) or not raw_base_url.strip():
        raise ValueError(f"El nodo '{node_id}' debe definir 'base_url'.")

    keep_alive = raw_node.get("keep_alive")
    think = parse_think(raw_node.get("think")) if "think" in raw_node else None
    return OllamaNodeConfig(
        node_id=node_id.strip(),
        base_url=normalize_http_url(
            raw_base_url,
            default="http://127.0.0.1:11434",
            label="URL de nodo Ollama",
        ),
        model=model.strip(),
        roles=_normalize_roles(raw_node.get("roles")),
        keep_alive=keep_alive if isinstance(keep_alive, str) else None,
        think=think,
        enabled=bool(raw_node.get("enabled", True)),
        priority=int(raw_node.get("priority", 100)),
        is_local=False,
    )
