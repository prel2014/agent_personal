from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from pathlib import Path

from ..cache import DEFAULT_KV_CACHE_DB_PATH
from ..path_policies import DEFAULT_PROTECTED_READ_PATH_PATTERNS
from .sources import build_runtime_config


@dataclass(frozen=True)
class Config:
    server_name: str
    server_version: str
    transport: str
    base_dir: Path
    encoding: str
    read_only: bool
    allow_read: bool
    allow_write: bool
    allow_execute: bool
    allow_delete: bool
    allowed_tools: tuple[str, ...] | None
    blocked_tools: tuple[str, ...]
    protected_paths: tuple[str, ...]
    protected_read_paths: tuple[str, ...] = DEFAULT_PROTECTED_READ_PATH_PATTERNS
    tool_confirmation_mode: str = "off"
    approved_sensitive_tools: tuple[str, ...] = ()
    kv_cache_enabled: bool = True
    kv_cache_db_path: str = DEFAULT_KV_CACHE_DB_PATH
    allow_hardware: bool = False
    allow_media_input: bool = False
    vision_model: str | None = None
    vision_ollama_base_url: str | None = None
    allow_web: bool = False
    allow_sandbox_execute: bool = False
    sandbox_backend: str = "docker"
    sandbox_image: str = "mcp-sandbox:local"
    sandbox_timeout: float = 30.0
    web_allowed_domains: tuple[str, ...] = ()
    web_denied_domains: tuple[str, ...] = ()
    web_block_private_networks: bool = True
    web_max_response_bytes: int = 2_000_000
    web_search_provider: str = "searxng"
    web_search_base_url: str | None = None

    @classmethod
    def from_sources(cls, args: argparse.Namespace | None = None) -> "Config":
        return build_runtime_config(cls, args)

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["base_dir"] = str(self.base_dir)
        data["allowed_tools"] = list(self.allowed_tools) if self.allowed_tools is not None else None
        data["blocked_tools"] = list(self.blocked_tools)
        data["protected_paths"] = list(self.protected_paths)
        data["protected_read_paths"] = list(self.protected_read_paths)
        data["approved_sensitive_tools"] = list(self.approved_sensitive_tools)
        data["kv_cache_enabled"] = self.kv_cache_enabled
        data["kv_cache_db_path"] = self.kv_cache_db_path
        return data


def load_config(args: argparse.Namespace | None = None) -> Config:
    return Config.from_sources(args)
