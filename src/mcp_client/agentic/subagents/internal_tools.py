from __future__ import annotations

from typing import Any


REQUEST_TOOLS_NAME = "request_tools"
DELEGATE_AGENT_NAME = "delegate_agent"
INTERNAL_TOOL_NAMES = frozenset({REQUEST_TOOLS_NAME, DELEGATE_AGENT_NAME})


def request_tools_schema() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": REQUEST_TOOLS_NAME,
            "description": (
                "Agrega herramientas disponibles al turno actual cuando una tarea "
                "requiere una capacidad que no esta activa. Continua con el plan "
                "actual despues de pedirlas."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tools": {
                        "type": "array",
                        "description": "Nombres exactos de tools que necesitas activar.",
                        "items": {"type": "string"},
                    },
                    "reason": {
                        "type": "string",
                        "description": "Motivo breve para activar esas tools.",
                    },
                },
                "required": ["tools"],
            },
        },
    }


def delegate_agent_schema() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": DELEGATE_AGENT_NAME,
            "description": (
                "Delega una subtarea acotada a un subagente especializado. Usa esto "
                "para trabajo paralelo conceptual, revision, inspeccion o ejecucion "
                "aislada; el subagente devuelve un resumen para continuar."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "agent": {
                        "type": "string",
                        "description": "Nombre del subagente del catalogo disponible.",
                    },
                    "task": {
                        "type": "string",
                        "description": "Tarea concreta y autocontenida para el subagente.",
                    },
                    "context": {
                        "type": "string",
                        "description": "Contexto minimo necesario para la subtarea.",
                    },
                },
                "required": ["agent", "task"],
            },
        },
    }


def internal_tool_schemas(*, allow_delegate: bool = True) -> list[dict[str, Any]]:
    schemas = [request_tools_schema()]
    if allow_delegate:
        schemas.append(delegate_agent_schema())
    return schemas
