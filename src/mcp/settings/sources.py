from __future__ import annotations

import argparse
import os
from typing import TypeVar

from src.mcp_shared.env import read_bool_env

from ..cache import DEFAULT_KV_CACHE_DB_PATH
from ..path_policies import (
    DEFAULT_PROTECTED_PATH_PATTERNS,
    DEFAULT_PROTECTED_READ_PATH_PATTERNS,
)
from .parsing import (
    parse_required_csv_values,
    parse_tool_list,
    resolve_base_dir,
)


ConfigT = TypeVar("ConfigT")


def build_runtime_config(
    config_cls: type[ConfigT],
    args: argparse.Namespace | None = None,
) -> ConfigT:
    args = args or argparse.Namespace()

    server_name = (
        getattr(args, "server_name", None)
        or os.getenv("MCP_SERVER_NAME")
        or "mcp-patolin"
    )
    server_version = (
        getattr(args, "server_version", None)
        or os.getenv("MCP_SERVER_VERSION")
        or "0.1.0"
    )
    transport = (
        getattr(args, "transport", None)
        or os.getenv("MCP_TRANSPORT")
        or "stdio"
    )
    encoding = (
        getattr(args, "encoding", None)
        or os.getenv("MCP_ENCODING")
        or "utf-8"
    )
    read_only = (
        getattr(args, "read_only", None)
        if getattr(args, "read_only", None) is not None
        else read_bool_env("MCP_READ_ONLY", default=False)
    )
    allow_read = (
        getattr(args, "allow_read", None)
        if getattr(args, "allow_read", None) is not None
        else read_bool_env("MCP_ALLOW_READ", default=True)
    )
    allow_write = (
        getattr(args, "allow_write", None)
        if getattr(args, "allow_write", None) is not None
        else read_bool_env("MCP_ALLOW_WRITE", default=True)
    )
    allow_execute = (
        getattr(args, "allow_execute", None)
        if getattr(args, "allow_execute", None) is not None
        else read_bool_env("MCP_ALLOW_EXECUTE", default=True)
    )
    allow_delete = (
        getattr(args, "allow_delete", None)
        if getattr(args, "allow_delete", None) is not None
        else read_bool_env("MCP_ALLOW_DELETE", default=False)
    )
    allow_hardware = (
        getattr(args, "allow_hardware", None)
        if getattr(args, "allow_hardware", None) is not None
        else read_bool_env("MCP_ALLOW_HARDWARE", default=False)
    )
    allow_media_input = (
        getattr(args, "allow_media_input", None)
        if getattr(args, "allow_media_input", None) is not None
        else read_bool_env("MCP_ALLOW_MEDIA_INPUT", default=False)
    )
    vision_model = _optional_str(
        getattr(args, "vision_model", None)
        or os.getenv("MCP_VISION_MODEL")
        or os.getenv("OLLAMA_VISION_MODEL")
    )
    vision_ollama_base_url = _optional_str(
        getattr(args, "vision_ollama_base_url", None)
        or os.getenv("MCP_VISION_OLLAMA_BASE_URL")
        or os.getenv("OLLAMA_BASE_URL")
    )
    allow_web = (
        getattr(args, "allow_web", None)
        if getattr(args, "allow_web", None) is not None
        else read_bool_env("MCP_ALLOW_WEB", default=False)
    )
    allow_sandbox_execute = (
        getattr(args, "allow_sandbox_execute", None)
        if getattr(args, "allow_sandbox_execute", None) is not None
        else read_bool_env("MCP_ALLOW_SANDBOX_EXECUTE", default=False)
    )
    if read_only:
        allow_write = False
        allow_execute = False
        allow_delete = False
        allow_hardware = False
        allow_media_input = False
        allow_web = False
        allow_sandbox_execute = False

    allowed_tools = parse_tool_list(
        getattr(args, "allowed_tools", None) or os.getenv("MCP_ALLOWED_TOOLS")
    )
    blocked_tools = parse_tool_list(
        getattr(args, "blocked_tools", None) or os.getenv("MCP_BLOCKED_TOOLS")
    ) or ()
    protected_paths = parse_tool_list(
        getattr(args, "protected_paths", None) or os.getenv("MCP_PROTECTED_PATHS")
    ) or DEFAULT_PROTECTED_PATH_PATTERNS
    protected_read_paths = parse_tool_list(
        getattr(args, "protected_read_paths", None) or os.getenv("MCP_PROTECTED_READ_PATHS")
    ) or DEFAULT_PROTECTED_READ_PATH_PATTERNS
    tool_confirmation_mode = (
        getattr(args, "tool_confirmation_mode", None)
        or os.getenv("MCP_TOOL_CONFIRMATION_MODE")
        or "off"
    ).strip().lower()
    if tool_confirmation_mode not in {"off", "sensitive"}:
        raise ValueError("MCP_TOOL_CONFIRMATION_MODE debe ser off o sensitive.")
    approved_sensitive_tools = parse_required_csv_values(
        getattr(args, "approved_sensitive_tools", None)
        or os.getenv("MCP_APPROVED_SENSITIVE_TOOLS")
    )
    kv_cache_enabled = (
        getattr(args, "kv_cache_enabled", None)
        if getattr(args, "kv_cache_enabled", None) is not None
        else read_bool_env("MCP_CLIENT_KV_CACHE_ENABLED", default=True)
    )
    kv_cache_db_path = (
        getattr(args, "kv_cache_db_path", None)
        or os.getenv("MCP_CLIENT_KV_CACHE_DB_PATH")
        or DEFAULT_KV_CACHE_DB_PATH
    )
    sandbox_backend = (
        getattr(args, "sandbox_backend", None)
        or os.getenv("MCP_SANDBOX_BACKEND")
        or "docker"
    ).strip().lower()
    sandbox_image = (
        getattr(args, "sandbox_image", None)
        or os.getenv("MCP_SANDBOX_IMAGE")
        or "mcp-sandbox:local"
    )
    sandbox_timeout = float(
        getattr(args, "sandbox_timeout", None)
        or os.getenv("MCP_SANDBOX_TIMEOUT")
        or 30.0
    )
    web_allowed_domains = parse_required_csv_values(
        getattr(args, "web_allowed_domains", None)
        or os.getenv("MCP_WEB_ALLOWED_DOMAINS")
    )
    web_denied_domains = parse_required_csv_values(
        getattr(args, "web_denied_domains", None)
        or os.getenv("MCP_WEB_DENIED_DOMAINS")
    )
    web_block_private_networks = (
        getattr(args, "web_block_private_networks", None)
        if getattr(args, "web_block_private_networks", None) is not None
        else read_bool_env("MCP_WEB_BLOCK_PRIVATE_NETWORKS", default=True)
    )
    web_max_response_bytes = int(
        getattr(args, "web_max_response_bytes", None)
        or os.getenv("MCP_WEB_MAX_RESPONSE_BYTES")
        or 2_000_000
    )
    web_search_provider = (
        getattr(args, "web_search_provider", None)
        or os.getenv("MCP_WEB_SEARCH_PROVIDER")
        or "searxng"
    ).strip().lower()
    web_search_base_url = (
        getattr(args, "web_search_base_url", None)
        or os.getenv("MCP_WEB_SEARCH_BASE_URL")
        or None
    )
    base_dir_value = getattr(args, "base_dir", None) or os.getenv("MCP_BASE_DIR")
    base_dir = resolve_base_dir(base_dir_value)

    return config_cls(
        server_name=server_name,
        server_version=server_version,
        transport=transport,
        base_dir=base_dir,
        encoding=encoding,
        read_only=read_only,
        allow_read=allow_read,
        allow_write=allow_write,
        allow_execute=allow_execute,
        allow_delete=allow_delete,
        allow_hardware=allow_hardware,
        allow_media_input=allow_media_input,
        vision_model=vision_model,
        vision_ollama_base_url=vision_ollama_base_url,
        allow_web=allow_web,
        allow_sandbox_execute=allow_sandbox_execute,
        sandbox_backend=sandbox_backend,
        sandbox_image=sandbox_image,
        sandbox_timeout=sandbox_timeout,
        web_allowed_domains=web_allowed_domains,
        web_denied_domains=web_denied_domains,
        web_block_private_networks=web_block_private_networks,
        web_max_response_bytes=web_max_response_bytes,
        web_search_provider=web_search_provider,
        web_search_base_url=web_search_base_url,
        allowed_tools=allowed_tools,
        blocked_tools=blocked_tools,
        protected_paths=protected_paths,
        protected_read_paths=protected_read_paths,
        tool_confirmation_mode=tool_confirmation_mode,
        approved_sensitive_tools=approved_sensitive_tools,
        kv_cache_enabled=kv_cache_enabled,
        kv_cache_db_path=kv_cache_db_path,
    )


def _optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
