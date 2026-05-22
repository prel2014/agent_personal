from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from .categories import ToolCategory


class ToolParameter(BaseModel):
    name: str
    type: Literal["string", "integer", "number", "boolean", "object", "array"]
    description: str
    required: bool = True

    def to_json_schema(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "description": self.description,
        }


class ToolDefinition(BaseModel):
    name: str
    description: str
    category: ToolCategory
    parameters: list[ToolParameter]

    def to_ollama_tool(self) -> dict[str, Any]:
        properties = {
            parameter.name: parameter.to_json_schema()
            for parameter in self.parameters
        }
        required = [
            parameter.name
            for parameter in self.parameters
            if parameter.required
        ]

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


class RuntimeToolCall(BaseModel):
    name: str
    arguments: dict[str, Any]


class ToolResult(BaseModel):
    success: bool
    result: Any | None = None
    error: str | None = None
