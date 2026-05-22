from __future__ import annotations

from typing import Any, Callable

from .config_loader import load_extra_nodes
from .discovery import NodeDiscoveryCache
from .models import (
    NodeAutoPromotionSettings,
    NodeDiscoverySettings,
    NodeProbeResult,
    NodeSelection,
    OllamaNodeConfig,
)
from .probe import OllamaNodeProbe
from .registry_factory import registry_from_server_config

class OllamaNodeRegistry:
    def __init__(
        self,
        *,
        local_node: OllamaNodeConfig,
        extra_nodes: list[OllamaNodeConfig] | None = None,
        allow_local_fallback: bool = True,
        discovery_settings: NodeDiscoverySettings | None = None,
        auto_promotion_settings: NodeAutoPromotionSettings | None = None,
        probe: OllamaNodeProbe | None = None,
        local_probe_result: NodeProbeResult | None = None,
    ) -> None:
        self.local_node = local_node
        self.allow_local_fallback = allow_local_fallback
        self.discovery_settings = discovery_settings or NodeDiscoverySettings()
        self.auto_promotion_settings = auto_promotion_settings or NodeAutoPromotionSettings()
        self._local_probe_result = local_probe_result
        self.discovery = NodeDiscoveryCache(
            settings=self.discovery_settings,
            probe=probe,
        )
        self.probe = self.discovery.probe
        self._configured_nodes = [local_node, *(extra_nodes or [])]
        self._round_robin_indices: dict[str, int] = {}

    @classmethod
    def from_server_config(
        cls,
        config,
        *,
        probe: OllamaNodeProbe | None = None,
    ) -> "OllamaNodeRegistry":
        return registry_from_server_config(cls, config, probe=probe)

    @staticmethod
    def _load_extra_nodes(config_path: str | None) -> list[OllamaNodeConfig]:
        return load_extra_nodes(config_path)

    def list_nodes(self) -> list[dict[str, object]]:
        self._ensure_discovery()
        active_nodes = self._active_nodes()
        nodes = [self._node_with_status(node) for node in active_nodes]
        nodes.extend(self.discovery.unmanaged_nodes(active_nodes))
        return nodes

    def resolve(self, client_context: dict[str, Any] | None = None) -> NodeSelection:
        self._ensure_discovery()
        context = client_context or {}
        requested_node_id = context.get("agent_node_id")
        if isinstance(requested_node_id, str) and requested_node_id.strip():
            selection = self._select_by_id(requested_node_id.strip())
            if selection is not None:
                return selection

        requested_role = context.get("agent_role")
        if isinstance(requested_role, str) and requested_role.strip():
            selection = self._select_by_role(requested_role.strip().lower())
            if selection is not None:
                return selection

        return NodeSelection(
            node=self.local_node,
            reason="default_local",
        )

    def fallback_for(self, reason: str) -> NodeSelection | None:
        if not self.allow_local_fallback:
            return None
        return NodeSelection(
            node=self.local_node,
            reason=reason,
            used_fallback=True,
        )

    def _select_by_id(self, node_id: str) -> NodeSelection | None:
        for node in self._active_nodes():
            if node.node_id == node_id and node.enabled and self._is_available(node):
                return NodeSelection(node=node, reason=f"explicit_node:{node_id}")
        return None

    def _select_by_role(self, role: str) -> NodeSelection | None:
        candidates = [
            node
            for node in self._active_nodes()
            if node.enabled
            and not node.is_local
            and node.handles_role(role)
            and self._is_available(node)
        ]
        if not candidates:
            return None

        candidates.sort(key=lambda node: (node.priority, node.node_id))
        index = self._round_robin_indices.get(role, 0) % len(candidates)
        self._round_robin_indices[role] = index + 1
        selected = candidates[index]
        return NodeSelection(node=selected, reason=f"role:{role}")

    def summary(self) -> dict[str, object]:
        self._ensure_discovery()
        return {
            "allow_local_fallback": self.allow_local_fallback,
            "node_count": len(self.list_nodes()),
            "configured_node_count": len(self._configured_nodes),
            "discovery": self.discovery.summary(),
            "auto_promotion": {
                **self.auto_promotion_settings.to_dict(),
                "promoted_node_count": len(self._auto_promoted_nodes()),
            },
            "nodes": self.list_nodes(),
        }

    def refresh_discovery(
        self,
        *,
        force: bool = False,
        progress_callback: Callable[[str, str, NodeProbeResult | None], None] | None = None,
    ) -> list[NodeProbeResult]:
        return self.discovery.refresh(
            force=force,
            progress_callback=progress_callback,
        )

    def candidate_base_urls(self) -> list[str]:
        return self.discovery.candidate_base_urls()

    def _ensure_discovery(self) -> None:
        self.discovery.ensure()

    def _probe_state(self, base_url: str) -> NodeProbeResult | None:
        if (
            self._local_probe_result is not None
            and base_url == self.local_node.base_url
        ):
            return self._local_probe_result
        return self.discovery.probe_state(base_url)

    def _active_nodes(self) -> list[OllamaNodeConfig]:
        return [*self._configured_nodes, *self._auto_promoted_nodes()]

    def _auto_promoted_nodes(self) -> list[OllamaNodeConfig]:
        return self.discovery.auto_promoted_nodes(
            self._configured_nodes,
            self.auto_promotion_settings,
        )

    def _is_available(self, node: OllamaNodeConfig) -> bool:
        if not self.discovery_settings.enabled or node.is_local:
            return True

        probe_result = self._probe_state(node.base_url)
        if probe_result is None:
            return True
        return probe_result.reachable

    def _node_with_status(self, node: OllamaNodeConfig) -> dict[str, object]:
        probe_result = self._probe_state(node.base_url)
        payload = node.to_dict()
        payload["managed"] = True
        payload["reachable"] = probe_result.reachable if probe_result is not None else None
        payload["available_models"] = list(probe_result.available_models) if probe_result is not None else []
        payload["last_error"] = probe_result.error if probe_result is not None else None
        payload["source"] = (
            "auto_promoted"
            if node.auto_promoted
            else node.source if node.source != "configured"
            else probe_result.source if probe_result is not None else node.source
        )
        return payload
