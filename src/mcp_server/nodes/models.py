from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DEFAULT_AUTO_PROMOTE_ROLES = ("planner", "worker", "reviewer")

@dataclass(frozen=True)
class OllamaNodeConfig:
    node_id: str
    base_url: str
    model: str
    roles: tuple[str, ...] = ()
    keep_alive: str | None = None
    think: str | bool | None = None
    enabled: bool = True
    priority: int = 100
    is_local: bool = False
    source: str = "configured"
    auto_promoted: bool = False
    promotion_reason: str | None = None

    def handles_role(self, role: str | None) -> bool:
        if not role:
            return False
        if not self.roles:
            return False
        return role in self.roles or "*" in self.roles

    def to_dict(self) -> dict[str, object]:
        return {
            "node_id": self.node_id,
            "base_url": self.base_url,
            "model": self.model,
            "roles": list(self.roles),
            "keep_alive": self.keep_alive,
            "think": self.think,
            "enabled": self.enabled,
            "priority": self.priority,
            "is_local": self.is_local,
            "source": self.source,
            "auto_promoted": self.auto_promoted,
            "promotion_reason": self.promotion_reason,
        }

@dataclass(frozen=True)
class NodeSelection:
    node: OllamaNodeConfig
    reason: str
    used_fallback: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "node_id": self.node.node_id,
            "base_url": self.node.base_url,
            "model": self.node.model,
            "reason": self.reason,
            "used_fallback": self.used_fallback,
            "is_local": self.node.is_local,
        }

@dataclass(frozen=True)
class NodeDiscoverySettings:
    enabled: bool = False
    hosts: tuple[str, ...] = ()
    cidrs: tuple[str, ...] = ()
    port: int = 11434
    timeout: float = 1.5
    ttl_seconds: float = 30.0
    max_hosts: int = 64
    auto_lan: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "hosts": list(self.hosts),
            "cidrs": list(self.cidrs),
            "port": self.port,
            "timeout": self.timeout,
            "ttl_seconds": self.ttl_seconds,
            "max_hosts": self.max_hosts,
            "auto_lan": self.auto_lan,
        }

@dataclass(frozen=True)
class NodeAutoPromotionSettings:
    enabled: bool = False
    roles: tuple[str, ...] = DEFAULT_AUTO_PROMOTE_ROLES
    priority: int = 200
    max_nodes: int = 16

    def normalized_roles(self) -> tuple[str, ...]:
        roles: list[str] = []
        for role in self.roles:
            normalized = role.strip().lower()
            if normalized and normalized not in roles:
                roles.append(normalized)
        return tuple(roles)

    def to_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "roles": list(self.normalized_roles()),
            "priority": self.priority,
            "max_nodes": self.max_nodes,
        }

@dataclass(frozen=True)
class NodeProbeResult:
    base_url: str
    reachable: bool
    available_models: tuple[str, ...] = ()
    error: str | None = None
    source: str = "discovery"

    def to_dict(self) -> dict[str, object]:
        return {
            "base_url": self.base_url,
            "reachable": self.reachable,
            "available_models": list(self.available_models),
            "error": self.error,
            "source": self.source,
        }

def _normalize_roles(raw_roles: Any) -> tuple[str, ...]:
    if raw_roles is None:
        return ()
    if not isinstance(raw_roles, list):
        raise ValueError("'roles' debe ser una lista de strings.")

    roles: list[str] = []
    for item in raw_roles:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("Cada rol debe ser un string no vacio.")
        roles.append(item.strip().lower())
    return tuple(roles)
