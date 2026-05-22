from __future__ import annotations

import argparse
import os
from typing import TypeVar

from src.mcp_shared.env import read_bool_env
from src.mcp_shared.urls import detect_local_lan_cidrs, is_loopback_host, normalize_http_url

from .defaults import DEFAULT_SYSTEM_PROMPT
from .parsing import parse_csv_values, parse_think

ConfigT = TypeVar("ConfigT")


def build_server_config(
    config_cls: type[ConfigT],
    args: argparse.Namespace | None = None,
) -> ConfigT:
    args = args or argparse.Namespace()

    host = getattr(args, "host", None) or os.getenv("MCP_API_HOST") or "127.0.0.1"
    port = int(getattr(args, "port", None) or os.getenv("MCP_API_PORT") or 8000)
    auth_mode = (
        getattr(args, "auth_mode", None)
        or os.getenv("MCP_SERVER_AUTH_MODE")
        or "off"
    ).strip().lower()
    if auth_mode not in {"off", "bearer_static"}:
        raise ValueError("MCP_SERVER_AUTH_MODE debe ser off o bearer_static.")
    auth_static_tokens = parse_csv_values(
        getattr(args, "auth_static_tokens", None)
        or os.getenv("MCP_SERVER_AUTH_TOKENS")
    )
    require_auth_for_info = (
        getattr(args, "require_auth_for_info", None)
        if getattr(args, "require_auth_for_info", None) is not None
        else read_bool_env("MCP_SERVER_REQUIRE_AUTH_FOR_INFO", default=True)
    )
    public_health = (
        getattr(args, "public_health", None)
        if getattr(args, "public_health", None) is not None
        else read_bool_env("MCP_SERVER_PUBLIC_HEALTH", default=True)
    )
    if auth_mode == "bearer_static" and not auth_static_tokens:
        raise ValueError(
            "MCP_SERVER_AUTH_MODE=bearer_static requiere MCP_SERVER_AUTH_TOKENS."
        )
    if not is_loopback_host(host) and auth_mode == "off":
        raise ValueError(
            "No se puede exponer mcp_server fuera de loopback sin autenticacion. "
            "Configura MCP_SERVER_AUTH_MODE=bearer_static."
        )
    ollama_base_url = normalize_http_url(
        getattr(args, "ollama_base_url", None),
        env_name="OLLAMA_BASE_URL",
        default="http://127.0.0.1:11434",
        label="URL para Ollama",
    )
    ollama_model = (
        getattr(args, "model", None)
        or os.getenv("OLLAMA_MODEL")
        or "auto"
    )
    ollama_keep_alive = (
        getattr(args, "keep_alive", None)
        or os.getenv("OLLAMA_KEEP_ALIVE")
        or None
    )
    request_timeout = float(
        getattr(args, "request_timeout", None)
        or os.getenv("OLLAMA_REQUEST_TIMEOUT")
        or 300.0
    )
    system_prompt = (
        getattr(args, "system_prompt", None)
        or os.getenv("MCP_SERVER_SYSTEM_PROMPT")
        or DEFAULT_SYSTEM_PROMPT
    )
    nodes_config_path = (
        getattr(args, "nodes_config", None)
        or os.getenv("MCP_SERVER_NODES_CONFIG")
        or None
    )
    allow_local_fallback = (
        getattr(args, "allow_local_fallback", None)
        if getattr(args, "allow_local_fallback", None) is not None
        else read_bool_env("MCP_SERVER_ALLOW_LOCAL_FALLBACK", default=True)
    )
    discovery_enabled = (
        getattr(args, "discovery_enabled", None)
        if getattr(args, "discovery_enabled", None) is not None
        else read_bool_env("MCP_SERVER_DISCOVERY_ENABLED", default=False)
    )
    discovery_auto_lan = (
        getattr(args, "discovery_auto_lan", None)
        if getattr(args, "discovery_auto_lan", None) is not None
        else read_bool_env("MCP_SERVER_DISCOVERY_AUTO_LAN", default=True)
    )
    discovery_hosts = parse_csv_values(
        getattr(args, "discovery_hosts", None)
        or os.getenv("MCP_SERVER_DISCOVERY_HOSTS")
    )
    discovery_cidrs = parse_csv_values(
        getattr(args, "discovery_cidrs", None)
        or os.getenv("MCP_SERVER_DISCOVERY_CIDRS")
    )
    if discovery_enabled and discovery_auto_lan and not discovery_hosts and not discovery_cidrs:
        discovery_cidrs = detect_local_lan_cidrs()
    discovery_port = int(
        getattr(args, "discovery_port", None)
        or os.getenv("MCP_SERVER_DISCOVERY_PORT")
        or 11434
    )
    discovery_timeout = float(
        getattr(args, "discovery_timeout", None)
        or os.getenv("MCP_SERVER_DISCOVERY_TIMEOUT")
        or 1.5
    )
    discovery_ttl_seconds = float(
        getattr(args, "discovery_ttl_seconds", None)
        or os.getenv("MCP_SERVER_DISCOVERY_TTL_SECONDS")
        or 30.0
    )
    discovery_max_hosts = int(
        getattr(args, "discovery_max_hosts", None)
        or os.getenv("MCP_SERVER_DISCOVERY_MAX_HOSTS")
        or 64
    )
    auto_promote_discovered_nodes = (
        getattr(args, "auto_promote_discovered_nodes", None)
        if getattr(args, "auto_promote_discovered_nodes", None) is not None
        else read_bool_env("MCP_SERVER_AUTO_PROMOTE_DISCOVERED_NODES", default=False)
    )
    auto_promote_roles = parse_csv_values(
        getattr(args, "auto_promote_roles", None)
        or os.getenv("MCP_SERVER_AUTO_PROMOTE_ROLES")
        or "planner,worker,reviewer"
    )
    auto_promote_priority = int(
        getattr(args, "auto_promote_priority", None)
        or os.getenv("MCP_SERVER_AUTO_PROMOTE_PRIORITY")
        or 200
    )
    auto_promote_max_nodes = int(
        getattr(args, "auto_promote_max_nodes", None)
        or os.getenv("MCP_SERVER_AUTO_PROMOTE_MAX_NODES")
        or 16
    )

    return config_cls(
        host=host,
        port=port,
        auth_mode=auth_mode,
        auth_static_tokens=auth_static_tokens,
        require_auth_for_info=require_auth_for_info,
        public_health=public_health,
        ollama_base_url=ollama_base_url,
        ollama_model=ollama_model,
        ollama_keep_alive=ollama_keep_alive,
        ollama_think=parse_think(getattr(args, "think", None)),
        request_timeout=request_timeout,
        system_prompt=system_prompt,
        nodes_config_path=nodes_config_path,
        allow_local_fallback=allow_local_fallback,
        discovery_enabled=discovery_enabled,
        discovery_hosts=discovery_hosts,
        discovery_cidrs=discovery_cidrs,
        discovery_port=discovery_port,
        discovery_timeout=discovery_timeout,
        discovery_ttl_seconds=discovery_ttl_seconds,
        discovery_max_hosts=discovery_max_hosts,
        discovery_auto_lan=discovery_auto_lan,
        auto_promote_discovered_nodes=auto_promote_discovered_nodes,
        auto_promote_roles=auto_promote_roles,
        auto_promote_priority=auto_promote_priority,
        auto_promote_max_nodes=auto_promote_max_nodes,
    )
