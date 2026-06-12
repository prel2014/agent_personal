from __future__ import annotations

from prompt_toolkit.document import Document

from src.mcp_client.slash.completion import SlashCommandCompleter
from src.mcp_client.slash.lexer import (
    ARGUMENT_STYLE,
    COMMAND_STYLE,
    UNKNOWN_STYLE,
    style_slash_command_line,
)
from src.mcp_client.slash.models import CommandResult, SlashCommand
from src.mcp_client.slash.registry import create_default_router
from src.mcp_client.slash.router import SlashCommandRouter


def test_router_supports_hierarchical_route_and_legacy_name() -> None:
    calls: list[list[str]] = []

    def handler(ctx, args: list[str]) -> CommandResult:
        calls.append(args)
        return CommandResult()

    router = SlashCommandRouter(
        [
            SlashCommand(
                name="cache-get",
                summary="Lee cache",
                usage="/cache get <namespace> <key>",
                category="Cache",
                handler=handler,
                route=("cache", "get"),
            )
        ]
    )

    router.run("/cache get repo last_scan", None)  # type: ignore[arg-type]
    router.run("/cache-get repo last_scan", None)  # type: ignore[arg-type]

    assert calls == [["repo", "last_scan"], ["repo", "last_scan"]]


def test_default_router_exposes_subcommand_groups() -> None:
    router = create_default_router()

    assert ("cache", "Cache - submenu") in router.list_root_entries()
    assert [command.command_path for command in router.list_subcommands("cache")] == [
        ("cache", "get"),
        ("cache", "list"),
        ("cache", "search"),
        ("cache", "set"),
    ]
    assert router.get_command_path(["cache", "get"]).name == "cache-get"


def test_completion_suggests_subcommands() -> None:
    router = create_default_router()
    completer = SlashCommandCompleter(router, None)  # type: ignore[arg-type]

    completions = list(completer.get_completions(Document("/cache "), None))

    assert [completion.text for completion in completions] == ["get ", "list ", "search ", "set "]
    assert [completion.display_text for completion in completions] == ["get", "list", "search", "set"]


def test_completion_leaves_space_for_root_command_arguments() -> None:
    router = create_default_router()
    completer = SlashCommandCompleter(router, None)  # type: ignore[arg-type]

    completions = list(completer.get_completions(Document("/re"), None))

    assert [(completion.text, completion.display_text) for completion in completions] == [
        ("/read ", "/read"),
    ]


def test_slash_command_line_styles_route_as_block_and_arguments_separately() -> None:
    router = create_default_router()

    styled = style_slash_command_line("/cache get repo last_scan", router)

    assert styled == [
        (COMMAND_STYLE, "/cache"),
        ("", " "),
        (COMMAND_STYLE, "get"),
        ("", " "),
        (ARGUMENT_STYLE, "repo"),
        ("", " "),
        (ARGUMENT_STYLE, "last_scan"),
    ]


def test_slash_command_line_marks_unknown_root() -> None:
    router = create_default_router()

    styled = style_slash_command_line("/wat value", router)

    assert styled == [
        (UNKNOWN_STYLE, "/wat"),
        ("", " "),
        (ARGUMENT_STYLE, "value"),
    ]
