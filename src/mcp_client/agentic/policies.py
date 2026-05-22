from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from src.mcp_shared.agent_contracts import (
    AgentExecutionContext,
    EXECUTE,
    READ_ONLY_TOOL_CATEGORIES,
    SANDBOX_TOOL_CATEGORIES,
)

from .ports import ToolRuntimePort
from .roles import AgentRole, RoleSpec


@dataclass(frozen=True)
class ToolAccessPolicy:
    tool_categories: Mapping[str, str]
    read_only_categories: frozenset[str] = field(
        default_factory=lambda: READ_ONLY_TOOL_CATEGORIES
    )

    def allowed_tools_for(
        self,
        spec: RoleSpec,
        *,
        sandbox_only: bool = True,
    ) -> set[str] | None:
        if spec.tool_access == "full":
            if not sandbox_only:
                return None
            return {
                name
                for name, category in self.tool_categories.items()
                if category in SANDBOX_TOOL_CATEGORIES or category == EXECUTE
            }
        if spec.tool_access == "none":
            return set()

        return {
            name
            for name, category in self.tool_categories.items()
            if category in self.read_only_categories
        }


class RoleRuntimeView:
    def __init__(
        self,
        runtime: ToolRuntimePort,
        *,
        role: AgentRole,
        directive: str,
        allowed_tools: set[str] | None,
        sandbox_only: bool = True,
    ) -> None:
        self.runtime = runtime
        self.role = role
        self.directive = directive
        self.allowed_tools = allowed_tools
        self.sandbox_only = sandbox_only

    def list_ollama_tools(self) -> list[dict[str, object]]:
        tools = self.runtime.list_ollama_tools()
        if self.allowed_tools is None:
            return tools

        return [
            tool
            for tool in tools
            if isinstance(tool.get("function"), dict)
            and tool["function"].get("name") in self.allowed_tools
        ]

    def build_context(self) -> dict[str, object]:
        context = dict(self.runtime.build_context())
        visible_tools = self._visible_tool_names(context)
        context["available_tools"] = visible_tools
        context["tool_categories"] = self._visible_tool_categories(context, visible_tools)
        context["agent_role"] = self.role.value
        context["role_directive"] = self.directive
        context["prompt_mode"] = self.role.value
        context["orchestration"] = {
            "enabled": True,
            "role": self.role.value,
            "visible_tools": visible_tools,
        }
        context["sandbox"] = {
            "mode": "sandbox" if self.sandbox_only else "host",
            "outside_sandbox_allowed": not self.sandbox_only,
        }
        return AgentExecutionContext.from_runtime_context(context).to_wire()

    def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self.allowed_tools is not None and name not in self.allowed_tools:
            visible_runtime_tools = self._runtime_tool_names()
            if name not in visible_runtime_tools:
                available = ", ".join(sorted(visible_runtime_tools)[:20]) or "(ninguna)"
                suffix = "..." if len(visible_runtime_tools) > 20 else ""
                return {
                    "success": False,
                    "result": None,
                    "error": (
                        f"La tool '{name}' no esta disponible en el runtime actual "
                        "o no existe con ese nombre. Revisa permisos/configuracion y "
                        f"usa una tool disponible. Tools visibles: {available}{suffix}."
                    ),
                }
            return {
                "success": False,
                "result": None,
                "error": (
                    f"La tool '{name}' no esta disponible para el rol '{self.role.value}'."
                ),
            }
        return self.runtime.call_tool(name, arguments)

    def _visible_tool_names(self, context: dict[str, object]) -> list[str]:
        visible_tools = context.get("available_tools", [])
        if not isinstance(visible_tools, list):
            return []

        names = [tool for tool in visible_tools if isinstance(tool, str)]
        if self.allowed_tools is None:
            return names
        return [tool for tool in names if tool in self.allowed_tools]

    def _visible_tool_categories(
        self,
        context: dict[str, object],
        visible_tools: list[str],
    ) -> dict[str, str]:
        raw_categories = context.get("tool_categories", {})
        if not isinstance(raw_categories, dict):
            return {}

        visible_set = set(visible_tools)
        return {
            name: category
            for name, category in raw_categories.items()
            if isinstance(name, str)
            and isinstance(category, str)
            and name in visible_set
        }

    def _runtime_tool_names(self) -> set[str]:
        names: set[str] = set()
        for tool in self.runtime.list_ollama_tools():
            function = tool.get("function")
            if isinstance(function, dict) and isinstance(function.get("name"), str):
                names.add(function["name"])
        return names


class DirectAnswerRuntimeView:
    def __init__(self, runtime: ToolRuntimePort) -> None:
        self.runtime = runtime

    def list_ollama_tools(self) -> list[dict[str, object]]:
        return []

    def build_context(self) -> dict[str, object]:
        context = dict(self.runtime.build_context())
        context["available_tools"] = []
        context["tool_categories"] = {}
        context["direct_answer_mode"] = True
        context["prompt_mode"] = "direct_answer"
        context["role_directive"] = (
            "Responde de forma directa y conversacional. No uses herramientas ni "
            "solicites acciones locales para saludos, charla simple o preguntas que "
            "puedas contestar con el contexto ya disponible."
        )
        return AgentExecutionContext.from_runtime_context(context).to_wire()

    def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "success": False,
            "result": None,
            "error": "Las tools no estan disponibles en modo de respuesta directa.",
        }


class FinalAnswerRuntimeView:
    def __init__(self, runtime: ToolRuntimePort, *, directive: str) -> None:
        self.runtime = runtime
        self.directive = directive

    def list_ollama_tools(self) -> list[dict[str, object]]:
        return []

    def build_context(self) -> dict[str, object]:
        context = dict(self.runtime.build_context())
        previous_directive = context.get("role_directive")
        if isinstance(previous_directive, str) and previous_directive:
            context["role_directive"] = f"{previous_directive}\n\n{self.directive}"
        else:
            context["role_directive"] = self.directive

        context["available_tools"] = []
        context["tool_categories"] = {}
        context["tool_limit_reached"] = True
        context["prompt_mode"] = "final_answer"
        orchestration = context.get("orchestration")
        if isinstance(orchestration, dict):
            context["orchestration"] = {
                **orchestration,
                "visible_tools": [],
                "final_answer_without_tools": True,
            }
        return AgentExecutionContext.from_runtime_context(context).to_wire()

    def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "success": False,
            "result": None,
            "error": "Las tools no estan disponibles durante el cierre final.",
        }
