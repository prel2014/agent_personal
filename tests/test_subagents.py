from __future__ import annotations

from pathlib import Path
from typing import Any

from src.mcp.settings.model import Config as RuntimeConfig
from src.mcp_client.agentic.policies import ToolAccessPolicy
from src.mcp_client.agentic.roles import WORKER_SPEC
from src.mcp_client.agentic.subagents.registry import SubagentRegistry, load_subagent_file
from src.mcp_client.agentic.subagents.runtime import SelectableToolRuntimeView
from src.mcp_client.agentic.team.factory import RoleWorkflowFactory
from src.mcp_client.config.model import ClientConfig
from src.mcp_client.render.null import NullRenderer
from src.mcp_shared.agent_contracts import EXECUTE, READ, WRITE


def test_load_subagent_markdown_frontmatter(tmp_path: Path) -> None:
    path = tmp_path / "inspector.md"
    path.write_text(
        """---
name: inspector
description: Lee archivos puntuales.
tools: readfile, read_lines
tool_access: read_only
---
Inspecciona solo lo necesario.
""",
        encoding="utf-8",
    )

    spec = load_subagent_file(path)

    assert spec.name == "inspector"
    assert spec.description == "Lee archivos puntuales."
    assert spec.tools == ("readfile", "read_lines")
    assert spec.tool_access == "read_only"
    assert spec.directive == "Inspecciona solo lo necesario."


def test_registry_project_subagent_overrides_builtin(tmp_path: Path) -> None:
    agents = tmp_path / ".mcp_agents"
    agents.mkdir()
    (agents / "worker.md").write_text(
        """---
name: worker
description: Worker personalizado.
tools: readfile
---
Directiva local.
""",
        encoding="utf-8",
    )

    registry = SubagentRegistry.from_paths([agents])

    worker = registry.get("worker")
    assert worker is not None
    assert worker.description == "Worker personalizado."
    assert worker.directive == "Directiva local."


def test_selectable_runtime_activates_requested_tools_without_replanning() -> None:
    runtime = FakeRuntime(["readfile", "writefile", "python_interpreter"])
    view = SelectableToolRuntimeView(
        runtime,
        initial_tools={"readfile"},
        subagent_catalog=[],
        allow_delegate=False,
    )

    initial_names = _tool_names(view.list_ollama_tools())
    assert "readfile" in initial_names
    assert "python_interpreter" not in initial_names
    assert "request_tools" in initial_names

    result = view.call_tool(
        "request_tools",
        {"tools": ["python_interpreter"], "reason": "validar CSV"},
    )

    assert result["success"] is True
    names_after_request = _tool_names(view.list_ollama_tools())
    assert "python_interpreter" in names_after_request


def test_factory_gives_worker_small_initial_tool_catalog(tmp_path: Path) -> None:
    runtime = FakeRuntime(["readfile", "writefile", "python_interpreter"])
    factory = RoleWorkflowFactory(
        config=_client_config(tmp_path),
        runtime=runtime,
        api=FakeApi(),
        tool_policy=ToolAccessPolicy(
            {
                "readfile": READ,
                "writefile": WRITE,
                "python_interpreter": EXECUTE,
            }
        ),
        subagent_registry=SubagentRegistry(),
    )

    workflow = factory.build(
        spec=WORKER_SPEC,
        directive=WORKER_SPEC.directive,
        renderer=NullRenderer(),
        auto_write=False,
        max_steps=2,
    )

    names = _tool_names(workflow.runtime.list_ollama_tools())
    assert "readfile" in names
    assert "writefile" in names
    assert "request_tools" in names
    assert "delegate_agent" in names
    assert "python_interpreter" not in names


class FakeRuntime:
    def __init__(self, tool_names: list[str]) -> None:
        self.tool_names = tool_names

    def list_ollama_tools(self) -> list[dict[str, object]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": name,
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            }
            for name in self.tool_names
        ]

    def build_context(self) -> dict[str, object]:
        return {
            "available_tools": self.tool_names,
            "tool_categories": {name: READ for name in self.tool_names},
        }

    def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {"success": True, "result": arguments or {}, "error": None}


class FakeApi:
    def chat(self, **_: Any) -> dict[str, Any]:
        raise AssertionError("No deberia llamar al API en este test")

    def chat_stream(self, **_: Any) -> Any:
        raise AssertionError("No deberia llamar al API en este test")


def _client_config(tmp_path: Path) -> ClientConfig:
    runtime_config = RuntimeConfig(
        server_name="test",
        server_version="0",
        transport="stdio",
        base_dir=tmp_path,
        encoding="utf-8",
        read_only=False,
        allow_read=True,
        allow_write=True,
        allow_execute=True,
        allow_delete=False,
        allowed_tools=None,
        blocked_tools=(),
        protected_paths=(),
    )
    return ClientConfig(
        runtime_config=runtime_config,
        server_url="http://127.0.0.1:8000",
        client_name="test",
        client_version="0",
        max_steps=2,
        request_timeout=1.0,
        stream_responses=False,
        show_thinking=False,
        auto_write_code=False,
        rich_output=False,
        orchestrate_agents=True,
        planner_max_steps=1,
        reviewer_max_steps=1,
        review_retries=0,
    )


def _tool_names(tools: list[dict[str, object]]) -> set[str]:
    names: set[str] = set()
    for tool in tools:
        function = tool.get("function")
        if isinstance(function, dict) and isinstance(function.get("name"), str):
            names.add(function["name"])
    return names
