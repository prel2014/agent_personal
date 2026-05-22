from __future__ import annotations

from typing import Any, Iterator, Protocol


class ToolRuntimePort(Protocol):
    def list_ollama_tools(self) -> list[dict[str, object]]:
        ...

    def build_context(self) -> dict[str, object]:
        ...

    def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ...


class OrchestratorPort(Protocol):
    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        client_context: dict[str, Any],
    ) -> dict[str, Any]:
        ...

    def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        client_context: dict[str, Any],
    ) -> Iterator[dict[str, Any]]:
        ...


class RendererPort(Protocol):
    rich_output: bool

    def print_line(
        self,
        text: str = "",
        *,
        style: str | None = None,
        end: str = "\n",
    ) -> None:
        ...

    def print_assistant_message(
        self,
        step: int,
        assistant_message: dict[str, Any],
        *,
        show_thinking: bool = False,
    ) -> None:
        ...

    def print_tool_call(self, name: str, arguments: dict[str, Any]) -> None:
        ...

    def print_context_usage(self, step: int, usage, *, label: str | None = None) -> None:
        ...
