from __future__ import annotations

import argparse
from dataclasses import dataclass

from .argparse import add_server_arguments
from .defaults import DEFAULT_SYSTEM_PROMPT
from .sources import build_server_config


@dataclass(frozen=True)
class ServerConfig:
    host: str
    port: int
    auth_mode: str
    auth_static_tokens: tuple[str, ...]
    require_auth_for_info: bool
    public_health: bool
    ollama_base_url: str
    ollama_model: str
    ollama_keep_alive: str | None
    ollama_think: str | bool | None
    request_timeout: float
    system_prompt: str
    nodes_config_path: str | None
    allow_local_fallback: bool
    discovery_enabled: bool
    discovery_hosts: tuple[str, ...]
    discovery_cidrs: tuple[str, ...]
    discovery_port: int
    discovery_timeout: float
    discovery_ttl_seconds: float
    discovery_max_hosts: int
    discovery_auto_lan: bool
    auto_promote_discovered_nodes: bool
    auto_promote_roles: tuple[str, ...]
    auto_promote_priority: int
    auto_promote_max_nodes: int

    @classmethod
    def from_sources(cls, args: argparse.Namespace | None = None) -> "ServerConfig":
        return build_server_config(cls, args)

    def to_dict(self) -> dict[str, object]:
        return {
            "host": self.host,
            "port": self.port,
            "auth_mode": self.auth_mode,
            "auth_configured": bool(self.auth_static_tokens),
            "require_auth_for_info": self.require_auth_for_info,
            "public_health": self.public_health,
            "ollama_base_url": self.ollama_base_url,
            "ollama_model": self.ollama_model,
            "ollama_keep_alive": self.ollama_keep_alive,
            "ollama_think": self.ollama_think,
            "request_timeout": self.request_timeout,
            "nodes_config_path": self.nodes_config_path,
            "allow_local_fallback": self.allow_local_fallback,
            "discovery_enabled": self.discovery_enabled,
            "discovery_hosts": list(self.discovery_hosts),
            "discovery_cidrs": list(self.discovery_cidrs),
            "discovery_port": self.discovery_port,
            "discovery_timeout": self.discovery_timeout,
            "discovery_ttl_seconds": self.discovery_ttl_seconds,
            "discovery_max_hosts": self.discovery_max_hosts,
            "discovery_auto_lan": self.discovery_auto_lan,
            "auto_promote_discovered_nodes": self.auto_promote_discovered_nodes,
            "auto_promote_roles": list(self.auto_promote_roles),
            "auto_promote_priority": self.auto_promote_priority,
            "auto_promote_max_nodes": self.auto_promote_max_nodes,
        }


def load_server_config(args: argparse.Namespace | None = None) -> ServerConfig:
    return ServerConfig.from_sources(args)


__all__ = [
    "DEFAULT_SYSTEM_PROMPT",
    "ServerConfig",
    "add_server_arguments",
    "load_server_config",
]
