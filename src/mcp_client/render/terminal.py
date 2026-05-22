import json
from typing import Any

from ..presentation import PresentationPolicy
from ..presentation.formatters import format_tool_call

class TerminalRenderer:
    def __init__(
        self,
        rich_output: bool = True,
        presentation: PresentationPolicy | None = None,
    ):
        self.rich_output = False
        self.console = None
        self._json = None
        self._markdown = None
        self.presentation = presentation or PresentationPolicy()
        self._last_context_usage_text: str | None = None
        self._last_context_usage_style: str | None = None

        if rich_output:
            try:
                from rich.console import Console
                from rich.json import JSON
                from rich.markdown import Markdown
            except ImportError:
                return

            self.console = Console(soft_wrap=True)
            self._json = JSON
            self._markdown = Markdown
            self.rich_output = True

    def print_line(
        self,
        text: str = "",
        *,
        style: str | None = None,
        end: str = "\n",
    ) -> None:
        if self.rich_output and self.console is not None:
            self.console.print(text, style=style, end=end, markup=False)
            return

        print(text, end=end)

    def print_json(self, data: Any) -> None:
        if self.rich_output and self.console is not None and self._json is not None:
            self.console.print(
                self._json.from_data(data, ensure_ascii=False, indent=2)
            )
            return

        print(json.dumps(data, ensure_ascii=False, indent=2))

    def print_assistant_message(
        self,
        step: int,
        assistant_message: dict[str, Any],
        *,
        show_thinking: bool = False,
    ) -> None:
        thinking = assistant_message.get("thinking")
        content = assistant_message.get("content")

        if thinking and show_thinking:
            self.print_thinking_block(f"[step {step}] thinking", str(thinking))

        if not content:
            return

        if self.rich_output and self.console is not None and self._markdown is not None:
            if self.presentation.is_debug:
                self.console.print(f"[step {step}]", style="bold cyan", markup=False)
            self.console.print(self._markdown(content, code_theme="monokai"))
            return

        if self.presentation.is_debug:
            print(f"[step {step}] {content}")
            return
        print(content)

    def print_thinking_block(self, title: str, thinking: str) -> None:
        if (
            self.rich_output
            and self.console is not None
            and self._markdown is not None
        ):
            self.console.print(title, style="yellow", markup=False)
            self.console.print(
                self._markdown(thinking, code_theme="monokai"),
                style="yellow",
            )
            return

        print(f"{title}: {thinking}")

    def print_context_usage(self, step: int, usage, *, label: str | None = None) -> None:
        if not self.presentation.is_debug:
            return
        width = 24
        filled = int(round(usage.ratio * width))
        bar = "#" * filled + "-" * (width - filled)
        prefix = f"[context {label} step {step}]" if label else f"[context step {step}]"
        text = (
            f"{prefix} [{bar}] "
            f"{usage.percent}% "
            f"({usage.estimated_tokens:,}/{usage.max_tokens:,} tokens)"
        )
        style = None
        if usage.percent >= 90:
            style = "bold red"
        elif usage.percent >= 75:
            style = "yellow"
        elif self.rich_output:
            style = "dim"
        self._last_context_usage_text = text
        self._last_context_usage_style = style
        self.print_line(text, style=style)

    def context_toolbar_text(self) -> str:
        if not self._last_context_usage_text:
            return "contexto: sin medir"

        text = self._last_context_usage_text
        marker = "] "
        if marker in text:
            return text.split(marker, 1)[1]
        return text

    def print_tool_call(self, name: str, arguments: dict[str, Any]) -> None:
        if not self.presentation.show_tool_events():
            return
        summary = format_tool_call(
            name,
            arguments,
            detailed=self.presentation.show_tool_details(),
        )
        if self.rich_output and self.console is not None:
            self.console.print(f"[tool] {summary}", style="bold magenta", markup=False)
            return

        print(f"[tool] {summary}")

    def print_public_result(self, content: str) -> None:
        if not content:
            return
        if self.rich_output and self.console is not None and self._markdown is not None:
            self.console.print(self._markdown(content, code_theme="monokai"))
            return
        print(content)
