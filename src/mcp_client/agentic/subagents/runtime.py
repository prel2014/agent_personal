from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..ports import ToolRuntimePort
from .internal_tools import (
    DELEGATE_AGENT_NAME,
    REQUEST_TOOLS_NAME,
    internal_tool_schemas,
)

DelegateHandler = Callable[[str, str, str | None], dict[str, Any]]


class SelectableToolRuntimeView:
    def __init__(
        self,
        runtime: ToolRuntimePort,
        *,
        initial_tools: set[str] | None,
        subagent_catalog: list[dict[str, object]],
        delegate_handler: DelegateHandler | None = None,
        allow_delegate: bool = True,
    ) -> None:
        self.runtime = runtime
        self.active_tools = set(initial_tools) if initial_tools is not None else None
        self.subagent_catalog = subagent_catalog
        self.delegate_handler = delegate_handler
        self.allow_delegate = allow_delegate

    def list_ollama_tools(self) -> list[dict[str, object]]:
        visible = self._visible_runtime_tools()
        return [
            *visible,
            *internal_tool_schemas(allow_delegate=self.allow_delegate),
        ]

    def build_context(self) -> dict[str, object]:
        context = dict(self.runtime.build_context())
        visible_names = self._visible_tool_names()
        categories = context.get("tool_categories", {})
        visible_set = set(visible_names)
        visible_categories = (
            {
                name: category
                for name, category in categories.items()
                if isinstance(name, str)
                and isinstance(category, str)
                and name in visible_set
            }
            if isinstance(categories, dict)
            else {}
        )
        context["available_tools"] = [
            *visible_names,
            REQUEST_TOOLS_NAME,
            *([DELEGATE_AGENT_NAME] if self.allow_delegate else []),
        ]
        context["tool_categories"] = {
            **visible_categories,
            REQUEST_TOOLS_NAME: "orchestration",
            **({DELEGATE_AGENT_NAME: "orchestration"} if self.allow_delegate else {}),
        }
        context["subagents"] = self.subagent_catalog if self.allow_delegate else []
        context["tool_selection"] = {
            "dynamic": True,
            "active_tools": visible_names,
            "instruction": (
                "Si falta una tool necesaria, llama request_tools con los nombres "
                "exactos y continua; no replantees todo desde cero."
            ),
        }
        orchestration = context.get("orchestration")
        if isinstance(orchestration, dict):
            context["orchestration"] = {
                **orchestration,
                "subagents_enabled": self.allow_delegate,
                "dynamic_tools_enabled": True,
            }
        return context

    def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        arguments = arguments or {}
        if name == REQUEST_TOOLS_NAME:
            return self._request_tools(arguments)
        if name == DELEGATE_AGENT_NAME:
            return self._delegate_agent(arguments)
        if self.active_tools is not None and name not in self.active_tools:
            return {
                "success": False,
                "result": None,
                "error": (
                    f"La tool '{name}' no esta activa. Si la necesitas, primero llama "
                    f"{REQUEST_TOOLS_NAME} con ese nombre y continua con el mismo plan."
                ),
            }
        return self.runtime.call_tool(name, arguments)

    def _request_tools(self, arguments: dict[str, Any]) -> dict[str, Any]:
        requested = arguments.get("tools", [])
        if not isinstance(requested, list):
            requested = [requested]
        requested_names = [tool for tool in requested if isinstance(tool, str) and tool]
        allowed_names = self._all_runtime_tool_names()
        added: list[str] = []
        unavailable: list[str] = []

        if self.active_tools is None:
            active = set(allowed_names)
        else:
            active = self.active_tools

        for name in requested_names:
            if name not in allowed_names:
                unavailable.append(name)
                continue
            if name not in active:
                active.add(name)
                added.append(name)

        if self.active_tools is not None:
            self.active_tools = active

        return {
            "success": len(unavailable) == 0,
            "result": {
                "added": added,
                "already_active": sorted(set(requested_names) - set(added) - set(unavailable)),
                "unavailable": unavailable,
                "active_tools": self._visible_tool_names(),
            },
            "error": (
                f"Tools no disponibles o no permitidas: {', '.join(unavailable)}"
                if unavailable
                else None
            ),
        }

    def _delegate_agent(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if not self.allow_delegate or self.delegate_handler is None:
            return {
                "success": False,
                "result": None,
                "error": "La delegacion de subagentes no esta disponible en este contexto.",
            }
        agent = arguments.get("agent")
        task = arguments.get("task")
        context = arguments.get("context")
        if not isinstance(agent, str) or not agent.strip():
            return {"success": False, "result": None, "error": "Falta agent."}
        if not isinstance(task, str) or not task.strip():
            return {"success": False, "result": None, "error": "Falta task."}
        return self.delegate_handler(
            agent.strip(),
            task.strip(),
            context if isinstance(context, str) and context.strip() else None,
        )

    def _visible_runtime_tools(self) -> list[dict[str, object]]:
        tools = self.runtime.list_ollama_tools()
        if self.active_tools is None:
            return tools
        return [
            tool
            for tool in tools
            if _tool_name(tool) in self.active_tools
        ]

    def _visible_tool_names(self) -> list[str]:
        return [
            name
            for name in (_tool_name(tool) for tool in self._visible_runtime_tools())
            if name is not None
        ]

    def _all_runtime_tool_names(self) -> set[str]:
        return {
            name
            for name in (_tool_name(tool) for tool in self.runtime.list_ollama_tools())
            if name is not None
        }


def _tool_name(tool: dict[str, object]) -> str | None:
    function = tool.get("function")
    if not isinstance(function, dict):
        return None
    name = function.get("name")
    return name if isinstance(name, str) else None
