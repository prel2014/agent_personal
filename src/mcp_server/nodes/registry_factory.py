from __future__ import annotations

from .config_loader import load_extra_nodes
from .models import (
    DEFAULT_AUTO_PROMOTE_ROLES,
    NodeAutoPromotionSettings,
    NodeDiscoverySettings,
    OllamaNodeConfig,
)
from .probe import OllamaNodeProbe
from .selection import _resolve_local_model


def registry_from_server_config(
    registry_cls,
    config,
    *,
    probe: OllamaNodeProbe | None = None,
):
    node_probe = probe or OllamaNodeProbe(
        timeout=getattr(config, "discovery_timeout", 1.5)
    )
    local_model, local_probe_result, local_source, local_reason = _resolve_local_model(
        requested_model=config.ollama_model,
        base_url=config.ollama_base_url,
        probe=node_probe,
    )
    local_node = OllamaNodeConfig(
        node_id="local",
        base_url=config.ollama_base_url,
        model=local_model,
        roles=("worker",),
        keep_alive=config.ollama_keep_alive,
        think=config.ollama_think,
        enabled=True,
        priority=1000,
        is_local=True,
        source=local_source,
        promotion_reason=local_reason,
    )
    discovery_settings = NodeDiscoverySettings(
        enabled=getattr(config, "discovery_enabled", False),
        hosts=tuple(getattr(config, "discovery_hosts", ()) or ()),
        cidrs=tuple(getattr(config, "discovery_cidrs", ()) or ()),
        port=getattr(config, "discovery_port", 11434),
        timeout=getattr(config, "discovery_timeout", 1.5),
        ttl_seconds=getattr(config, "discovery_ttl_seconds", 30.0),
        max_hosts=getattr(config, "discovery_max_hosts", 64),
        auto_lan=getattr(config, "discovery_auto_lan", True),
    )
    auto_promotion_settings = NodeAutoPromotionSettings(
        enabled=getattr(config, "auto_promote_discovered_nodes", False),
        roles=tuple(
            getattr(config, "auto_promote_roles", DEFAULT_AUTO_PROMOTE_ROLES)
            or DEFAULT_AUTO_PROMOTE_ROLES
        ),
        priority=getattr(config, "auto_promote_priority", 200),
        max_nodes=getattr(config, "auto_promote_max_nodes", 16),
    )
    return registry_cls(
        local_node=local_node,
        extra_nodes=load_extra_nodes(config.nodes_config_path),
        allow_local_fallback=config.allow_local_fallback,
        discovery_settings=discovery_settings,
        auto_promotion_settings=auto_promotion_settings,
        probe=node_probe,
        local_probe_result=local_probe_result,
    )
