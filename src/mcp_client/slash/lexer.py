from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prompt_toolkit.document import Document

    from .router import SlashCommandRouter


COMMAND_STYLE = "class:slash.command"
ARGUMENT_STYLE = "class:slash.argument"
UNKNOWN_STYLE = "class:slash.unknown"

_TOKEN_RE = re.compile(r"\S+")


class SlashCommandLexer:
    def __init__(self, router: "SlashCommandRouter"):
        self.router = router

    def lex_document(self, document: "Document"):
        def get_line(line_no: int) -> list[tuple[str, str]]:
            lines = document.text.splitlines() or [""]
            if line_no >= len(lines):
                return []
            return style_slash_command_line(lines[line_no], self.router)

        return get_line


def style_slash_command_line(
    line: str,
    router: "SlashCommandRouter",
) -> list[tuple[str, str]]:
    if not line.startswith("/"):
        return [("", line)]

    matches = list(_TOKEN_RE.finditer(line))
    if not matches:
        return [("", line)]

    route_tokens = _route_tokens_from_matches(matches)
    command_token_count = _resolved_command_token_count(route_tokens, router)
    first_token_style = COMMAND_STYLE if command_token_count else UNKNOWN_STYLE

    styled: list[tuple[str, str]] = []
    cursor = 0
    for index, match in enumerate(matches):
        if match.start() > cursor:
            styled.append(("", line[cursor : match.start()]))

        token = match.group(0)
        if index < command_token_count:
            style = COMMAND_STYLE
        elif index == 0:
            style = first_token_style
        else:
            style = ARGUMENT_STYLE
        styled.append((style, token))
        cursor = match.end()

    if cursor < len(line):
        styled.append(("", line[cursor:]))

    return styled


def _route_tokens_from_matches(matches: list[re.Match[str]]) -> list[str]:
    if not matches:
        return []
    first = matches[0].group(0).lstrip("/")
    return [first, *(match.group(0) for match in matches[1:])]


def _resolved_command_token_count(
    route_tokens: list[str],
    router: "SlashCommandRouter",
) -> int:
    if not route_tokens or not route_tokens[0]:
        return 1

    resolved = router.resolve(route_tokens)
    if resolved is not None:
        _, consumed_count = resolved
        return consumed_count

    root = route_tokens[0]
    if any(name.startswith(root) for name, _ in router.list_root_entries()):
        return 1

    return 0
