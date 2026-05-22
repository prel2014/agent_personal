from pathlib import Path
from typing import TYPE_CHECKING

from .models import ARG_COMMAND, ARG_GLOB, ARG_PATH

try:
    from prompt_toolkit.completion import Completer
except ImportError:
    class Completer:  # type: ignore[no-redef]
        pass

if TYPE_CHECKING:
    from prompt_toolkit.document import Document

    from .models import CommandContext
    from .router import SlashCommandRouter


SKIP_NAMES = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
}


class SlashCommandCompleter(Completer):
    def __init__(self, router: "SlashCommandRouter", ctx: "CommandContext"):
        self.router = router
        self.ctx = ctx

    def get_completions(self, document: "Document", complete_event):
        from prompt_toolkit.completion import Completion

        text_before_cursor = document.text_before_cursor
        if not text_before_cursor.startswith("/"):
            return

        stripped = text_before_cursor.lstrip()
        if not stripped.startswith("/"):
            return

        tokens, current_index, current_prefix = _split_completion_context(stripped)
        if not tokens:
            return

        command_name = tokens[0].lstrip("/")

        if current_index == 0:
            for name, meta in self.router.list_root_entries():
                candidate = f"/{name}"
                if candidate.startswith(current_prefix):
                    yield Completion(
                        _with_argument_separator(candidate),
                        start_position=-len(current_prefix),
                        display=candidate,
                        display_meta=meta,
                        style="class:slash.command",
                        selected_style="class:slash.command",
                    )
            return

        if current_index == 1:
            subcommands = self.router.list_subcommands(command_name)
            if subcommands:
                for command in subcommands:
                    subcommand = command.command_path[1]
                    if subcommand.startswith(current_prefix):
                        yield Completion(
                            _with_argument_separator(subcommand),
                            start_position=-len(current_prefix),
                            display=subcommand,
                            display_meta=command.summary,
                            style="class:slash.command",
                            selected_style="class:slash.command",
                        )
                return

        route_tokens = [command_name, *tokens[1:current_index]]
        resolved = self.router.resolve(route_tokens)
        if resolved is None:
            return

        command, consumed_count = resolved
        if command.name == "help" and current_index == 2 and len(tokens) >= 2:
            parent = tokens[1].lstrip("/")
            for child in self.router.list_subcommands(parent):
                subcommand = child.command_path[1]
                if subcommand.startswith(current_prefix):
                    yield Completion(
                        _with_argument_separator(subcommand),
                        start_position=-len(current_prefix),
                        display=subcommand,
                        display_meta=child.summary,
                        style="class:slash.command",
                        selected_style="class:slash.command",
                    )
            return

        arg_index = current_index - consumed_count
        if arg_index >= len(command.arg_kinds):
            return

        arg_kind = command.arg_kinds[arg_index]
        if arg_kind == ARG_COMMAND:
            for item in self._command_name_completions(current_prefix):
                yield item
            return

        if arg_kind in {ARG_PATH, ARG_GLOB}:
            for item in self._path_completions(current_prefix):
                yield item

    async def get_completions_async(self, document: "Document", complete_event):
        for completion in self.get_completions(document, complete_event):
            yield completion

    def _command_name_completions(self, prefix: str):
        from prompt_toolkit.completion import Completion

        normalized_prefix = prefix.lstrip("/")
        for candidate, meta in self.router.list_root_entries():
            if candidate.startswith(normalized_prefix):
                yield Completion(
                    _with_argument_separator(candidate),
                    start_position=-len(prefix),
                    display=candidate,
                    display_meta=meta,
                    style="class:slash.command",
                    selected_style="class:slash.command",
                )

    def _path_completions(self, prefix: str):
        from prompt_toolkit.completion import Completion

        base_dir = self.ctx.runtime.config.base_dir
        search_root, _ = _resolve_search_root(base_dir, prefix)
        if not search_root.exists() or not search_root.is_dir():
            return
        try:
            search_root.relative_to(base_dir)
        except ValueError:
            return

        current_prefix = prefix.replace("\\", "/")
        for child in sorted(search_root.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
            if child.name in SKIP_NAMES:
                continue
            candidate_relative = child.relative_to(base_dir).as_posix()
            completion_text = candidate_relative + ("/" if child.is_dir() else "")
            if current_prefix and not completion_text.startswith(current_prefix):
                continue

            insertion = _quote_if_needed(completion_text)
            typed = _quote_if_needed(current_prefix)
            meta = "directorio" if child.is_dir() else "archivo"
            yield Completion(
                insertion,
                start_position=-len(typed),
                display=completion_text,
                display_meta=meta,
            )


def _split_completion_context(text: str) -> tuple[list[str], int, str]:
    if text.endswith(" "):
        tokens = text.split()
        return tokens, len(tokens), ""

    tokens = text.split()
    if not tokens:
        return [], 0, ""

    return tokens, len(tokens) - 1, tokens[-1]


def _resolve_search_root(base_dir: Path, prefix: str) -> tuple[Path, str]:
    normalized = prefix.strip('"').strip("'").replace("\\", "/")
    if not normalized:
        return base_dir, ""

    as_path = Path(normalized)
    if normalized.endswith("/"):
        return (base_dir / as_path).resolve(), ""

    parent = as_path.parent
    if str(parent) in {"", "."}:
        return base_dir, as_path.name

    return (base_dir / parent).resolve(), as_path.name


def _quote_if_needed(value: str) -> str:
    if " " in value:
        return f'"{value}"'

    return value


def _with_argument_separator(value: str) -> str:
    if value.endswith(" "):
        return value

    return f"{value} "
