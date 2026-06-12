import argparse
import os

from src.mcp.settings import load_config as load_runtime_config
from src.mcp.cache import DEFAULT_KV_CACHE_DB_PATH
from src.mcp_client.agentic.context_meter import DEFAULT_CONTEXT_WINDOW_TOKENS
from src.mcp_shared.env import read_bool_env
from src.mcp_shared.urls import is_loopback_url, normalize_http_url
from src.mcp_client.presentation.policy import normalize_output_mode

from .model import DEFAULT_SESSION_DB_PATH, ClientConfig
from ..agentic.trace_store import DEFAULT_TRACE_DB_PATH


def load_client_config(args: argparse.Namespace | None = None) -> ClientConfig:
    args = args or argparse.Namespace()
    runtime_config = load_runtime_config(args)

    server_url = normalize_http_url(
        getattr(args, "server_url", None),
        env_name="MCP_SERVER_URL",
        default="http://127.0.0.1:8000",
        label="URL para el servidor",
    )
    server_bearer_token = (
        getattr(args, "server_bearer_token", None)
        or os.getenv("MCP_SERVER_BEARER_TOKEN")
        or None
    )
    client_name = (
        getattr(args, "client_name", None)
        or os.getenv("MCP_CLIENT_NAME")
        or "mcp-cli"
    )
    client_version = (
        getattr(args, "client_version", None)
        or os.getenv("MCP_CLIENT_VERSION")
        or "0.1.0"
    )
    max_steps = int(
        getattr(args, "max_steps", None)
        or os.getenv("MCP_CLIENT_MAX_STEPS")
        or 8
    )
    request_timeout = float(
        getattr(args, "request_timeout", None)
        or os.getenv("MCP_CLIENT_REQUEST_TIMEOUT")
        or 360.0
    )
    stream_responses = (
        getattr(args, "stream_responses", None)
        if getattr(args, "stream_responses", None) is not None
        else read_bool_env("MCP_CLIENT_STREAM_RESPONSES", default=True)
    )
    show_thinking = (
        getattr(args, "show_thinking", None)
        if getattr(args, "show_thinking", None) is not None
        else read_bool_env("MCP_CLIENT_SHOW_THINKING", default=False)
    )
    auto_write_code = (
        getattr(args, "auto_write_code", None)
        if getattr(args, "auto_write_code", None) is not None
        else read_bool_env("MCP_CLIENT_AUTO_WRITE_CODE", default=True)
    )
    rich_output = (
        getattr(args, "rich_output", None)
        if getattr(args, "rich_output", None) is not None
        else read_bool_env("MCP_CLIENT_RICH_OUTPUT", default=True)
    )
    output_mode = normalize_output_mode(
        getattr(args, "output_mode", None)
        or os.getenv("MCP_CLIENT_OUTPUT_MODE")
        or "normal"
    )
    orchestrate_agents = (
        getattr(args, "orchestrate_agents", None)
        if getattr(args, "orchestrate_agents", None) is not None
        else read_bool_env("MCP_CLIENT_ORCHESTRATE_AGENTS", default=True)
    )
    planning_mode = (
        getattr(args, "planning_mode", None)
        or os.getenv("MCP_CLIENT_PLANNING_MODE")
        or "auto"
    ).strip().lower()
    if planning_mode not in {"auto", "always", "never"}:
        raise ValueError("MCP_CLIENT_PLANNING_MODE debe ser auto, always o never.")
    if getattr(args, "orchestrate_agents", None) is False:
        planning_mode = "never"
    elif planning_mode == "always":
        orchestrate_agents = True
    elif planning_mode == "never":
        orchestrate_agents = False
    planner_max_steps = int(
        getattr(args, "planner_max_steps", None)
        or os.getenv("MCP_CLIENT_PLANNER_MAX_STEPS")
        or min(5, max_steps)
    )
    reviewer_max_steps = int(
        getattr(args, "reviewer_max_steps", None)
        or os.getenv("MCP_CLIENT_REVIEWER_MAX_STEPS")
        or min(3, max_steps)
    )
    review_retries = int(
        getattr(args, "review_retries", None)
        or os.getenv("MCP_CLIENT_REVIEW_RETRIES")
        or 1
    )
    trace_capture = (
        getattr(args, "trace_capture", None)
        or os.getenv("MCP_CLIENT_TRACE_CAPTURE")
        or os.getenv("MCP_TRACE_CAPTURE")
        or "off"
    ).strip().lower()
    if trace_capture not in {"off", "metadata", "full"}:
        raise ValueError("MCP_CLIENT_TRACE_CAPTURE debe ser off, metadata o full.")

    raw_trace_thinking = (
        getattr(args, "trace_thinking", None)
        or os.getenv("MCP_CLIENT_TRACE_THINKING")
        or os.getenv("MCP_TRACE_THINKING")
    )
    if isinstance(raw_trace_thinking, str) and not raw_trace_thinking.strip():
        raw_trace_thinking = None
    trace_thinking = (
        raw_trace_thinking
        if raw_trace_thinking is not None
        else ("raw" if trace_capture != "off" else "off")
    ).strip().lower()
    if trace_thinking not in {"off", "summary", "raw"}:
        raise ValueError("MCP_CLIENT_TRACE_THINKING debe ser off, summary o raw.")

    trace_db_path = (
        getattr(args, "trace_db_path", None)
        or os.getenv("MCP_CLIENT_TRACE_DB_PATH")
        or os.getenv("MCP_TRACE_DB_PATH")
        or (DEFAULT_TRACE_DB_PATH if trace_capture != "off" else None)
    )
    session_db_path = (
        getattr(args, "session_db_path", None)
        or os.getenv("MCP_CLIENT_SESSION_DB_PATH")
        or DEFAULT_SESSION_DB_PATH
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
    context_window_tokens = int(
        getattr(args, "context_window_tokens", None)
        or os.getenv("MCP_CLIENT_CONTEXT_WINDOW_TOKENS")
        or DEFAULT_CONTEXT_WINDOW_TOKENS
    )
    if context_window_tokens <= 0:
        raise ValueError("MCP_CLIENT_CONTEXT_WINDOW_TOKENS debe ser mayor a 0.")
    show_context_meter = (
        getattr(args, "show_context_meter", None)
        if getattr(args, "show_context_meter", None) is not None
        else read_bool_env(
            "MCP_CLIENT_SHOW_CONTEXT_METER",
            default=(output_mode == "debug"),
        )
    )
    context_auto_trim = (
        getattr(args, "context_auto_trim", None)
        if getattr(args, "context_auto_trim", None) is not None
        else read_bool_env("MCP_CLIENT_CONTEXT_AUTO_TRIM", default=True)
    )
    context_trim_ratio = float(
        getattr(args, "context_trim_ratio", None)
        or os.getenv("MCP_CLIENT_CONTEXT_TRIM_RATIO")
        or 0.75
    )
    if not (0.0 < context_trim_ratio <= 1.0):
        raise ValueError("MCP_CLIENT_CONTEXT_TRIM_RATIO debe estar en (0.0, 1.0].")
    context_trim_min_turns = int(
        getattr(args, "context_trim_min_turns", None)
        or os.getenv("MCP_CLIENT_CONTEXT_TRIM_MIN_TURNS")
        or 2
    )
    if context_trim_min_turns < 1:
        raise ValueError("MCP_CLIENT_CONTEXT_TRIM_MIN_TURNS debe ser mayor o igual a 1.")
    auto_session_title = read_bool_env("MCP_CLIENT_AUTO_SESSION_TITLE", default=True)
    allow_remote_sensitive_tracing = (
        getattr(args, "allow_remote_sensitive_tracing", None)
        if getattr(args, "allow_remote_sensitive_tracing", None) is not None
        else read_bool_env("MCP_CLIENT_ALLOW_REMOTE_SENSITIVE_TRACING", default=False)
    )
    if not is_loopback_url(server_url) and not allow_remote_sensitive_tracing:
        if trace_capture == "full":
            raise ValueError(
                "trace_capture=full contra un servidor remoto requiere "
                "--allow-remote-sensitive-tracing."
            )
        if trace_thinking == "raw":
            raise ValueError(
                "trace_thinking=raw contra un servidor remoto requiere "
                "--allow-remote-sensitive-tracing."
            )

    return ClientConfig(
        runtime_config=runtime_config,
        server_url=server_url,
        client_name=client_name,
        client_version=client_version,
        max_steps=max_steps,
        request_timeout=request_timeout,
        stream_responses=stream_responses,
        show_thinking=show_thinking,
        auto_write_code=auto_write_code,
        rich_output=rich_output,
        orchestrate_agents=orchestrate_agents,
        planner_max_steps=planner_max_steps,
        reviewer_max_steps=reviewer_max_steps,
        review_retries=review_retries,
        planning_mode=planning_mode,
        server_bearer_token=server_bearer_token,
        trace_db_path=trace_db_path,
        trace_capture=trace_capture,
        trace_thinking=trace_thinking,
        session_db_path=session_db_path,
        auto_session_title=auto_session_title,
        allow_remote_sensitive_tracing=allow_remote_sensitive_tracing,
        kv_cache_enabled=kv_cache_enabled,
        kv_cache_db_path=kv_cache_db_path,
        context_window_tokens=context_window_tokens,
        show_context_meter=show_context_meter,
        output_mode=output_mode,
        context_auto_trim=context_auto_trim,
        context_trim_ratio=context_trim_ratio,
        context_trim_min_turns=context_trim_min_turns,
    )
