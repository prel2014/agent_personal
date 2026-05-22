from __future__ import annotations

import json
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from src.mcp_shared.contracts import ChatMessage, ChatResponse, ToolCall

from ..agentic.ports import OrchestratorPort, RendererPort, ToolRuntimePort
from ..agentic.state import ConversationMemory, ToolExecutionOutcome
from ..presentation.formatters import format_tool_result
from ..sessions.tool_call_compat import (
    coerce_textual_tool_call,
    strip_unavailable_tool_calls,
)


def request_streamed_assistant_message(
    *,
    api: OrchestratorPort,
    renderer: RendererPort,
    messages: list[dict[str, Any]],
    request_options: dict[str, Any],
    step: int,
    show_thinking: bool,
) -> tuple[ChatResponse, ChatMessage]:
    assistant_message = ChatMessage.assistant(content="", thinking="")
    response: ChatResponse | None = None
    printed_content = False
    rendered_thinking = False
    rendered_buffered_content = False
    buffer_content = bool(request_options.get("tools")) or renderer.rich_output

    for chunk in api.chat_stream(messages=messages, **request_options):
        if chunk.get("heartbeat") is True:
            continue
        response = ChatResponse.from_wire(chunk)
        if not response.ok:
            raise RuntimeError(response.error or "El servidor devolvio un error durante streaming.")
        message = response.message

        role = message.role
        if role:
            assistant_message.role = role

        thinking_chunk = message.thinking or ""
        if thinking_chunk:
            assistant_message.thinking = (assistant_message.thinking or "") + thinking_chunk

        content_chunk = message.content or ""
        if content_chunk:
            assistant_message.content += content_chunk
            if not buffer_content:
                printed_content = _print_content_prefix(
                    renderer=renderer,
                    step=step,
                    printed_content=printed_content,
                )
                renderer.print_line(content_chunk, end="")

        tool_calls = message.tool_calls or []
        if tool_calls:
            assistant_message.tool_calls = tool_calls

    if response is None:
        raise RuntimeError("El servidor no devolvio chunks de streaming.")

    final_message = ChatMessage.assistant(
        content=assistant_message.content,
        thinking=assistant_message.thinking or None,
        tool_calls=list(assistant_message.tool_calls),
    )
    final_message = coerce_textual_tool_call(
        final_message,
        request_options.get("tools", []),
    )
    final_message = strip_unavailable_tool_calls(final_message, request_options)
    if show_thinking and final_message.thinking:
        if printed_content:
            renderer.print_line()
        _print_thinking_message(
            renderer=renderer,
            step=step,
            thinking=final_message.thinking,
        )
        rendered_thinking = True

    if buffer_content and final_message.content and not final_message.tool_calls:
        _print_buffered_assistant_message(
            renderer=renderer,
            step=step,
            content=final_message.content,
        )
        printed_content = True
        rendered_buffered_content = True

    if (rendered_thinking or printed_content) and not rendered_buffered_content:
        renderer.print_line()

    final_response = ChatResponse(
        ok=response.ok,
        model=response.model,
        node_id=response.node_id,
        node_model=response.node_model,
        done=response.done,
        done_reason=response.done_reason,
        message=final_message,
    )
    return final_response, final_message


@dataclass
class ToolCallProcessor:
    runtime: ToolRuntimePort
    renderer: RendererPort

    def process(
        self,
        tool_calls: list[ToolCall],
        memory: ConversationMemory,
    ) -> list[ToolExecutionOutcome]:
        outcomes: list[ToolExecutionOutcome] = []
        writefile_paths: set[str] = set()
        for call in tool_calls:
            name = call.function.name
            arguments = call.function.arguments or {}

            if not name:
                continue

            self.renderer.print_tool_call(name, arguments)

            started_at = perf_counter()
            duplicate_write_path = _duplicate_writefile_path(
                name,
                arguments,
                writefile_paths,
            )
            if duplicate_write_path is not None:
                result = {
                    "success": False,
                    "error_code": "duplicate_write_path",
                    "error": (
                        "El modelo intento escribir dos veces el mismo archivo "
                        f"en una sola respuesta: {duplicate_write_path}. "
                        "Usa rutas distintas para archivos distintos o justifica "
                        "una sobrescritura en un paso posterior."
                    ),
                }
            else:
                try:
                    result = self.runtime.call_tool(name, arguments)
                except Exception as exc:
                    result = {"success": False, "error": str(exc)}
            duration_ms = (perf_counter() - started_at) * 1000

            serialized = json.dumps(result, ensure_ascii=False)
            presentation = getattr(self.renderer, "presentation", None)
            show_tool_events = (
                presentation.show_tool_events() if presentation is not None else True
            )
            show_tool_details = (
                presentation.show_tool_details() if presentation is not None else False
            )
            if show_tool_events:
                self.renderer.print_line(
                    f"[tool-result] {format_tool_result(name, result, detailed=show_tool_details)}",
                    style="dim" if self.renderer.rich_output else None,
                )
            memory.append_tool(name, serialized)
            outcomes.append(
                ToolExecutionOutcome(
                    name=name,
                    arguments=arguments,
                    result=result,
                    duration_ms=duration_ms,
                )
            )
        return outcomes


def _duplicate_writefile_path(
    name: str,
    arguments: dict[str, Any],
    seen_paths: set[str],
) -> str | None:
    if name != "writefile":
        return None

    path = arguments.get("path")
    if not isinstance(path, str) or not path.strip():
        return None

    normalized = path.strip().replace("\\", "/").casefold()
    if normalized in seen_paths:
        return path

    seen_paths.add(normalized)
    return None


def _print_thinking_message(
    *,
    renderer: RendererPort,
    step: int,
    thinking: str,
) -> None:
    renderer.print_assistant_message(
        step,
        ChatMessage.assistant(content="", thinking=thinking).to_wire(),
        show_thinking=True,
    )


def _print_buffered_assistant_message(
    *,
    renderer: RendererPort,
    step: int,
    content: str,
) -> None:
    renderer.print_assistant_message(
        step,
        ChatMessage.assistant(content=content).to_wire(),
        show_thinking=False,
    )


def _print_content_prefix(
    *,
    renderer: RendererPort,
    step: int,
    printed_content: bool,
) -> bool:
    if printed_content:
        return True

    renderer.print_line(
        f"[step {step}] ",
        style="bold cyan" if renderer.rich_output else None,
        end="",
    )
    return True
