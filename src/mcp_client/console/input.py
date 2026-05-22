from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..slash.models import CommandContext
    from ..slash.router import SlashCommandRouter


def create_console_prompt_session(router: "SlashCommandRouter", ctx: "CommandContext"):
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
        from prompt_toolkit.history import InMemoryHistory
        from prompt_toolkit.shortcuts import CompleteStyle
        from prompt_toolkit.styles import Style
    except ImportError:
        return None

    from ..slash.completion import SlashCommandCompleter
    from ..slash.lexer import SlashCommandLexer

    try:
        return PromptSession(
            history=InMemoryHistory(),
            completer=SlashCommandCompleter(router, ctx),
            lexer=SlashCommandLexer(router),
            auto_suggest=AutoSuggestFromHistory(),
            complete_while_typing=True,
            complete_style=CompleteStyle.COLUMN,
            key_bindings=_create_key_bindings(ctx),
            reserve_space_for_menu=10,
            enable_history_search=True,
            mouse_support=False,
            style=Style.from_dict(
                {
                    "completion-menu.completion": "bg:#202020 #d0d0d0",
                    "completion-menu.completion.current": "bg:#444444 #ffffff bold",
                    "completion-menu.meta.completion": "bg:#202020 #9cdcfe",
                    "completion-menu.meta.completion.current": "bg:#444444 #ffffff",
                    "slash.command": "bg:#264f78 #ffffff bold",
                    "slash.argument": "#ce9178",
                    "slash.unknown": "bg:#5a1d1d #ffb3b3 bold",
                    "scrollbar.background": "bg:#202020",
                    "scrollbar.button": "bg:#606060",
                }
            ),
            bottom_toolbar=lambda: _bottom_toolbar(ctx),
        )
    except Exception:
        return None


@dataclass
class ConsoleInputReader:
    prompt_session: Any = None

    def read_prompt(self, label: str = "tu> ") -> str | None:
        try:
            if self.prompt_session is not None:
                return self.prompt_session.prompt(label).strip()

            return input(label).strip()
        except KeyboardInterrupt:
            return ""
        except EOFError:
            return None


def _bottom_toolbar(ctx: "CommandContext"):
    thinking = "ON" if ctx.client.is_show_thinking_enabled() else "OFF"
    questions = "AUTO" if ctx.client.is_auto_answer_questions_enabled() else "MANUAL"
    context_text = "contexto: sin medir"
    context_provider = getattr(ctx.client.renderer, "context_toolbar_text", None)
    if callable(context_provider):
        context_text = context_provider()
    return (
        " / comandos | Ctrl+T thinking:"
        f"{thinking} | Ctrl+Y preguntas:{questions} | {context_text} | "
        "Tab/Enter: completar | Flechas: navegar"
    )


def _create_key_bindings(ctx: "CommandContext"):
    from prompt_toolkit.key_binding import KeyBindings

    key_bindings = KeyBindings()

    @key_bindings.add("/")
    def _(event):
        buffer = event.current_buffer
        buffer.insert_text("/")
        if buffer.document.cursor_position == 1:
            buffer.start_completion(select_first=False)

    @key_bindings.add("c-space")
    def _(event):
        event.current_buffer.start_completion(select_first=False)

    @key_bindings.add("c-t")
    def _(event):
        ctx.client.toggle_show_thinking()
        event.app.invalidate()

    @key_bindings.add("c-y")
    def _(event):
        ctx.client.toggle_auto_answer_questions()
        event.app.invalidate()

    return key_bindings
