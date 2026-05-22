from __future__ import annotations

import ast
import re
from typing import Any

from src.mcp_shared.contracts import ChatMessage, ToolCall, ToolFunction
from src.mcp_shared.json_payloads import iter_json_objects, load_json_object


def coerce_textual_tool_call(
    message: ChatMessage,
    tools: list[dict[str, Any]] | list[dict[str, object]],
) -> ChatMessage:
    if message.tool_calls or not message.content.strip():
        return message

    tool_call = parse_textual_tool_call(message.content, tools)
    if tool_call is None:
        return message

    return ChatMessage(
        role=message.role,
        content="",
        thinking=message.thinking,
        tool_name=message.tool_name,
        tool_calls=[tool_call],
    )


def strip_unavailable_tool_calls(
    message: ChatMessage,
    request_options: dict[str, object],
) -> ChatMessage:
    tools = request_options.get("tools")
    if isinstance(tools, list) and tools:
        return message
    if not message.tool_calls:
        return message

    content = message.content.strip()
    if not content:
        role = _agent_role(request_options)
        if role == "planner":
            content = (
                "OBJETIVO\n"
                "Preparar una ejecucion delegada al worker.\n\n"
                "HALLAZGOS\n"
                "El planner no tiene acceso a tools; la inspeccion debe hacerla el worker.\n\n"
                "PLAN\n"
                "1. El worker inspecciona los archivos necesarios dentro del sandbox.\n"
                "2. El worker aplica los cambios o produce el analisis solicitado.\n"
                "3. El reviewer valida el resultado con lectura.\n\n"
                "RIESGOS\n"
                "La informacion concreta depende de la inspeccion del worker."
            )
        else:
            content = (
                "No tengo herramientas disponibles en esta fase. Continuo con el contexto "
                "disponible sin ejecutar tools."
            )

    return ChatMessage(
        role=message.role,
        content=content,
        thinking=message.thinking,
        tool_name=message.tool_name,
        tool_calls=[],
    )


def parse_textual_tool_call(
    content: str,
    tools: list[dict[str, Any]] | list[dict[str, object]],
) -> ToolCall | None:
    allowed_tools = _allowed_tool_names(tools)
    if not allowed_tools:
        return None

    for payload in _candidate_tool_payloads(content):
        tool_call = _payload_to_tool_call(payload, allowed_tools)
        if tool_call is not None:
            return tool_call

    return None


def _agent_role(request_options: dict[str, object]) -> str | None:
    client_context = request_options.get("client_context")
    if not isinstance(client_context, dict):
        return None
    role = client_context.get("agent_role")
    return role if isinstance(role, str) else None


def _payload_to_tool_call(
    payload: dict[str, Any],
    allowed_tools: set[str],
) -> ToolCall | None:
    name = payload.get("name")
    arguments = payload.get("arguments", {})

    if not isinstance(name, str) and isinstance(payload.get("function"), dict):
        function = payload["function"]
        name = function.get("name")
        arguments = function.get("arguments", arguments)

    if not isinstance(name, str) or not name:
        return None

    if name not in allowed_tools:
        return None

    if isinstance(arguments, str):
        parsed_arguments = load_json_object(arguments)
        if parsed_arguments is None:
            return None
        arguments = parsed_arguments

    if arguments is None:
        arguments = {}

    if not isinstance(arguments, dict):
        return None

    return ToolCall(
        function=ToolFunction(
            name=name,
            arguments=arguments,
        )
    )


def _candidate_tool_payloads(content: str):
    direct_payload = load_json_object(_strip_json_fence(content))
    if direct_payload is not None:
        yield direct_payload

    for block in _iter_json_fence_blocks(content):
        block_payload = load_json_object(block)
        if block_payload is not None:
            yield block_payload
        yield from iter_json_objects(block)

    yield from _iter_tool_code_payloads(content)
    yield from iter_json_objects(content)


def _allowed_tool_names(
    tools: list[dict[str, Any]] | list[dict[str, object]],
) -> set[str]:
    names: set[str] = set()
    for tool in tools:
        function = tool.get("function")
        if isinstance(function, dict) and isinstance(function.get("name"), str):
            names.add(function["name"])
            continue

        name = tool.get("name")
        if isinstance(name, str):
            names.add(name)
    return names


def _strip_json_fence(content: str) -> str:
    stripped = content.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if len(lines) < 3 or lines[-1].strip() != "```":
        return stripped

    opener = lines[0].strip().lower()
    if opener not in {"```", "```json"}:
        return stripped

    return "\n".join(lines[1:-1]).strip()


def _iter_json_fence_blocks(content: str):
    pattern = re.compile(
        r"```(?P<language>[A-Za-z0-9_-]*)\s*\n(?P<body>.*?)```",
        flags=re.DOTALL,
    )
    for match in pattern.finditer(content):
        language = (match.group("language") or "").strip().lower()
        if language not in {"", "json"}:
            continue
        yield match.group("body").strip()


def _iter_tool_code_payloads(content: str):
    pattern = re.compile(
        r"<tool_code>\s*(?P<body>.*?)\s*</tool_code>",
        flags=re.DOTALL | re.IGNORECASE,
    )
    for match in pattern.finditer(content):
        payload = load_json_object(match.group("body"))
        if payload is not None:
            yield payload
            continue

        payload = _parse_python_tool_call(match.group("body"))
        if payload is not None:
            yield payload


def _parse_python_tool_call(content: str) -> dict[str, Any] | None:
    try:
        expression = ast.parse(content.strip(), mode="eval").body
    except SyntaxError:
        return None

    if not isinstance(expression, ast.Call):
        return None

    if isinstance(expression.func, ast.Name):
        name = expression.func.id
    elif isinstance(expression.func, ast.Attribute):
        name = expression.func.attr
    else:
        return None

    arguments: dict[str, Any] = {}
    for keyword in expression.keywords:
        if keyword.arg is None:
            return None
        try:
            arguments[keyword.arg] = ast.literal_eval(keyword.value)
        except (ValueError, TypeError):
            return None

    if expression.args:
        return None

    return {"name": name, "arguments": arguments}
