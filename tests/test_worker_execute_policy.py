from __future__ import annotations

from typing import Any

from src.mcp.tools.helpers.functions import writefile
from src.mcp_client.agentic.policies import RoleRuntimeView, ToolAccessPolicy
from src.mcp_client.agentic.roles import AgentRole, WORKER_SPEC
from src.mcp_shared.agent_contracts import EXECUTE, READ, WRITE


def test_worker_full_access_includes_execute_tools_when_runtime_exposes_them() -> None:
    policy = ToolAccessPolicy(
        {
            "readfile": READ,
            "writefile": WRITE,
            "python": EXECUTE,
            "python_interpreter": EXECUTE,
            "run_python_file": EXECUTE,
        }
    )

    allowed = policy.allowed_tools_for(WORKER_SPEC, sandbox_only=True)

    assert allowed is not None
    assert {
        "readfile",
        "writefile",
        "python",
        "python_interpreter",
        "run_python_file",
    } <= allowed


def test_role_runtime_view_reports_runtime_unavailable_tool_not_role_block() -> None:
    runtime = FakeRuntime(["readfile", "writefile"])
    view = RoleRuntimeView(
        runtime,
        role=AgentRole.WORKER,
        directive="",
        allowed_tools={"readfile", "writefile"},
    )

    result = view.call_tool("python_interpreter", {"code": "print('ok')"})

    assert result["success"] is False
    assert "runtime actual" in str(result["error"])
    assert "rol 'worker'" not in str(result["error"])


def test_writefile_x_mode_existing_file_gives_actionable_error(tmp_path) -> None:
    target = tmp_path / "alumnos.csv"
    target.write_text("viejo", encoding="utf-8")

    try:
        writefile(str(target), "nuevo", modo="x")
    except FileExistsError as exc:
        message = str(exc)
    else:
        raise AssertionError("writefile modo x debio fallar cuando el archivo existe")

    assert "modo='w'" in message
    assert "nombre alternativo" in message


class FakeRuntime:
    def __init__(self, tool_names: list[str]) -> None:
        self.tool_names = tool_names

    def list_ollama_tools(self) -> list[dict[str, object]]:
        return [{"function": {"name": name}} for name in self.tool_names]

    def build_context(self) -> dict[str, object]:
        return {"available_tools": self.tool_names, "tool_categories": {}}

    def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "success": True,
            "result": {"name": name, "arguments": arguments},
            "error": None,
        }
