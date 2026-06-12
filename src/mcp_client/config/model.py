from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Literal

from src.mcp.settings import Config as RuntimeConfig
from src.mcp.cache import DEFAULT_KV_CACHE_DB_PATH
from src.mcp_client.agentic.context_meter import DEFAULT_CONTEXT_WINDOW_TOKENS
from src.mcp_client.presentation import OutputMode


DEFAULT_SESSION_DB_PATH = ".mcp_sessions/client_sessions.sqlite"


@dataclass(frozen=True)
class ClientConfig:
    runtime_config: RuntimeConfig
    server_url: str
    client_name: str
    client_version: str
    max_steps: int
    request_timeout: float
    stream_responses: bool
    show_thinking: bool
    auto_write_code: bool
    rich_output: bool
    orchestrate_agents: bool
    planner_max_steps: int
    reviewer_max_steps: int
    review_retries: int
    planning_mode: Literal["auto", "always", "never"] = "auto"
    server_bearer_token: str | None = None
    trace_db_path: str | None = None
    trace_capture: Literal["off", "metadata", "full"] = "off"
    trace_thinking: Literal["off", "summary", "raw"] = "raw"
    session_db_path: str = DEFAULT_SESSION_DB_PATH
    auto_session_title: bool = True
    allow_remote_sensitive_tracing: bool = False
    kv_cache_enabled: bool = True
    kv_cache_db_path: str = DEFAULT_KV_CACHE_DB_PATH
    context_window_tokens: int = DEFAULT_CONTEXT_WINDOW_TOKENS
    show_context_meter: bool = True
    output_mode: OutputMode = "normal"
    context_auto_trim: bool = True
    context_trim_ratio: float = 0.75
    context_trim_min_turns: int = 2
    active_skill: str | None = None
    memory_project_enabled: bool = True
    memory_project_db_path: str = ".mcp_memory/project.sqlite"
    memory_user_enabled: bool = True
    memory_user_db_path: str = "~/.mcp_memory/user.sqlite"
    memory_embedding_enabled: bool = False
    memory_top_k: int = 3

    @classmethod
    def from_sources(cls, args: argparse.Namespace | None = None) -> "ClientConfig":
        from .loader import load_client_config

        return load_client_config(args)

    def to_dict(self) -> dict[str, object]:
        return {
            "client_name": self.client_name,
            "client_version": self.client_version,
            "server_url": self.server_url,
            "max_steps": self.max_steps,
            "request_timeout": self.request_timeout,
            "stream_responses": self.stream_responses,
            "show_thinking": self.show_thinking,
            "auto_write_code": self.auto_write_code,
            "rich_output": self.rich_output,
            "orchestrate_agents": self.orchestrate_agents,
            "planning_mode": self.planning_mode,
            "server_auth_configured": self.server_bearer_token is not None,
            "planner_max_steps": self.planner_max_steps,
            "reviewer_max_steps": self.reviewer_max_steps,
            "review_retries": self.review_retries,
            "trace_db_path": self.trace_db_path,
            "trace_capture": self.trace_capture,
            "trace_thinking": self.trace_thinking,
            "session_db_path": self.session_db_path,
            "auto_session_title": self.auto_session_title,
            "allow_remote_sensitive_tracing": self.allow_remote_sensitive_tracing,
            "kv_cache_enabled": self.kv_cache_enabled,
            "kv_cache_db_path": self.kv_cache_db_path,
            "context_window_tokens": self.context_window_tokens,
            "show_context_meter": self.show_context_meter,
            "output_mode": self.output_mode,
            "context_auto_trim": self.context_auto_trim,
            "context_trim_ratio": self.context_trim_ratio,
            "context_trim_min_turns": self.context_trim_min_turns,
            "runtime": self.runtime_config.to_dict(),
        }
