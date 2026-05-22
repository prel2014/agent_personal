from __future__ import annotations

from typing import Any


class NullRenderer:
    rich_output = False

    def print_line(
        self,
        text: str = "",
        *,
        style: str | None = None,
        end: str = "\n",
    ) -> None:
        return None

    def print_assistant_message(
        self,
        step: int,
        assistant_message: dict[str, Any],
        *,
        show_thinking: bool = False,
    ) -> None:
        return None

    def print_tool_call(self, name: str, arguments: dict[str, Any]) -> None:
        return None

    def print_context_usage(self, step: int, usage, *, label: str | None = None) -> None:
        return None


class ThinkingOnlyRenderer:
    def __init__(self, renderer, *, label: str) -> None:
        self.renderer = renderer
        self.label = label
        self.rich_output = renderer.rich_output

    def print_line(
        self,
        text: str = "",
        *,
        style: str | None = None,
        end: str = "\n",
    ) -> None:
        self.renderer.print_line(text, style=style, end=end)

    def print_assistant_message(
        self,
        step: int,
        assistant_message: dict[str, Any],
        *,
        show_thinking: bool = False,
    ) -> None:
        thinking = assistant_message.get("thinking")
        if not thinking or not show_thinking:
            return

        title = f"[{self.label} step {step}] thinking"
        markdown_printer = getattr(self.renderer, "print_thinking_block", None)
        if callable(markdown_printer):
            markdown_printer(title, str(thinking))
            return

        self.renderer.print_line(
            title,
            style="yellow" if self.renderer.rich_output else None,
        )
        self.renderer.print_line(
            str(thinking),
            style="yellow" if self.renderer.rich_output else None,
        )

    def print_tool_call(self, name: str, arguments: dict[str, Any]) -> None:
        return None

    def print_context_usage(self, step: int, usage, *, label: str | None = None) -> None:
        target_label = label or self.label
        if hasattr(self.renderer, "print_context_usage"):
            self.renderer.print_context_usage(step, usage, label=target_label)


class ToolEventRenderer:
    def __init__(self, renderer) -> None:
        self.renderer = renderer
        self.rich_output = renderer.rich_output
        self.presentation = getattr(renderer, "presentation", None)

    def print_line(
        self,
        text: str = "",
        *,
        style: str | None = None,
        end: str = "\n",
    ) -> None:
        self.renderer.print_line(text, style=style, end=end)

    def print_assistant_message(
        self,
        step: int,
        assistant_message: dict[str, Any],
        *,
        show_thinking: bool = False,
    ) -> None:
        thinking = assistant_message.get("thinking")
        if thinking and show_thinking:
            thinking_renderer = ThinkingOnlyRenderer(self.renderer, label="worker")
            thinking_renderer.print_assistant_message(
                step,
                assistant_message,
                show_thinking=show_thinking,
            )

    def print_tool_call(self, name: str, arguments: dict[str, Any]) -> None:
        self.renderer.print_tool_call(name, arguments)

    def print_context_usage(self, step: int, usage, *, label: str | None = None) -> None:
        if hasattr(self.renderer, "print_context_usage"):
            self.renderer.print_context_usage(step, usage, label=label)
