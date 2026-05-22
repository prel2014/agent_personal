from __future__ import annotations

import argparse

from src.mcp.runtime.local import LocalToolRuntime
from src.mcp.settings.model import Config
from src.mcp_shared.agent_contracts import AgentExecutionContext


def test_agent_execution_context_omits_default_empty_fields() -> None:
    payload = AgentExecutionContext(base_dir="C:/repo").to_wire()

    assert payload == {"base_dir": "C:/repo"}


def test_runtime_context_does_not_eagerly_embed_prompt_catalog(tmp_path) -> None:
    config = Config.from_sources(argparse.Namespace(base_dir=str(tmp_path)))
    runtime = LocalToolRuntime(config)

    context = runtime.build_context()

    assert "prompts" not in context
    assert "runtime_policy" not in context
    assert "language_markers" not in context
    assert "language_file_counts" not in context
    assert "kv_cache" not in context
    assert runtime.list_prompts()


def test_runtime_context_keeps_minimum_prompting_metadata(tmp_path) -> None:
    config = Config.from_sources(argparse.Namespace(base_dir=str(tmp_path)))
    runtime = LocalToolRuntime(config)

    context = runtime.build_context()

    assert context["base_dir"] == str(tmp_path)
    assert context["available_tools"]
    assert context["tool_categories"]
    assert "permissions" in context
