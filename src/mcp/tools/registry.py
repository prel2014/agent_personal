from __future__ import annotations

from collections.abc import Callable

from .models import RuntimeToolCall, ToolDefinition, ToolResult


class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def register(self, tool_definition: ToolDefinition, function: Callable):
        self.tools[tool_definition.name] = {
            "definition": tool_definition,
            "function": function,
        }

    def execute(self, tool_call: RuntimeToolCall) -> ToolResult:
        tool = self.tools.get(tool_call.name)

        if tool is None:
            return ToolResult(
                success=False,
                error=f"Herramienta no encontrada: {tool_call.name}",
            )

        try:
            result = tool["function"](**tool_call.arguments)
            return ToolResult(success=True, result=result)
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))

    def list_tools(self):
        return [tool["definition"] for tool in self.tools.values()]

    def list_ollama_tools(self):
        return [tool["definition"].to_ollama_tool() for tool in self.tools.values()]

    def category_map(self) -> dict[str, str]:
        return {
            name: tool["definition"].category
            for name, tool in self.tools.items()
        }

    def has_tool(self, name: str) -> bool:
        return name in self.tools

    def extend(self, other: "ToolRegistry"):
        self.tools.update(other.tools)
