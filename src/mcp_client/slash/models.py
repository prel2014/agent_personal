from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from ..app import MCPClient
    from ..console.repl import ConsoleREPLSession


Handler = Callable[["CommandContext", list[str]], "CommandResult"]
ARG_COMMAND = "command"
ARG_PATH = "path"
ARG_GLOB = "glob"
ARG_INT = "int"
ARG_TEXT = "text"


@dataclass(frozen=True)
class SlashCommand:
    name: str
    summary: str
    usage: str
    category: str
    handler: Handler
    examples: tuple[str, ...] = ()
    arg_kinds: tuple[str, ...] = ()
    route: tuple[str, ...] = ()
    aliases: tuple[tuple[str, ...], ...] = ()

    @property
    def command_path(self) -> tuple[str, ...]:
        return self.route or (self.name,)

    @property
    def display_name(self) -> str:
        return " ".join(self.command_path)

    @property
    def display_invocation(self) -> str:
        return "/" + self.display_name

    def route_variants(self) -> tuple[tuple[str, ...], ...]:
        variants = [self.command_path, (self.name,), *self.aliases]
        unique: list[tuple[str, ...]] = []
        for variant in variants:
            cleaned = tuple(part.strip().lstrip("/") for part in variant if part.strip())
            if cleaned and cleaned not in unique:
                unique.append(cleaned)
        return tuple(unique)


@dataclass(frozen=True)
class CommandResult:
    exit_repl: bool = False
    clear_messages: bool = False


@dataclass(frozen=True)
class CommandContext:
    client: "MCPClient"
    repl_session: "ConsoleREPLSession | None" = None

    @property
    def renderer(self):
        return self.client.renderer

    @property
    def runtime(self):
        return self.client.runtime
