from .models import CommandContext, CommandResult, SlashCommand
from .parsing import parse_command_line


class SlashCommandRouter:
    def __init__(self, commands: list[SlashCommand]):
        self._commands = {command.name: command for command in commands}
        self._routes: dict[tuple[str, ...], SlashCommand] = {}
        for command in commands:
            for route in command.route_variants():
                self._routes[route] = command

    def handles(self, line: str) -> bool:
        return line.startswith("/")

    def run(self, line: str, ctx: CommandContext) -> CommandResult:
        tokens = parse_command_line(line)
        if not tokens:
            raise ValueError("Comando vacio.")

        route_tokens = _normalize_route_tokens(tokens)
        if not route_tokens or not route_tokens[0]:
            route_tokens = ["help"]

        resolved = self.resolve(route_tokens)
        if resolved is None:
            name = route_tokens[0]
            children = self.list_subcommands(name)
            if children:
                available = ", ".join(command.command_path[1] for command in children)
                raise ValueError(
                    f"Subcomando desconocido para /{name}. Opciones: {available}."
                )
            raise ValueError(f"Comando desconocido: /{name}. Usa /help para ver opciones.")

        command, consumed_count = resolved
        return command.handler(ctx, route_tokens[consumed_count:])

    def resolve(self, route_tokens: list[str]) -> tuple[SlashCommand, int] | None:
        max_length = min(len(route_tokens), self._max_route_length())
        for length in range(max_length, 0, -1):
            route = tuple(route_tokens[:length])
            command = self._routes.get(route)
            if command is not None:
                return command, length
        return None

    def list_root_entries(self) -> list[tuple[str, str]]:
        entries: dict[str, str] = {}
        for command in self._commands.values():
            path = command.command_path
            if len(path) > 1:
                entries.setdefault(path[0], f"{command.category} - submenu")
                continue
            entries.setdefault(path[0], f"{command.category} - {command.summary}")
        return sorted(entries.items())

    def list_subcommands(self, parent: str) -> list[SlashCommand]:
        normalized = parent.strip().lstrip("/")
        commands = [
            command
            for command in self._commands.values()
            if len(command.command_path) > 1 and command.command_path[0] == normalized
        ]
        return sorted(commands, key=lambda command: command.command_path)

    def get_command_path(self, route_tokens: list[str]) -> SlashCommand | None:
        normalized = _normalize_route_tokens(route_tokens)
        resolved = self.resolve(normalized)
        if resolved is None:
            return None
        command, consumed_count = resolved
        if consumed_count != len(normalized):
            return None
        return command

    def list_commands(self) -> list[SlashCommand]:
        return list(self._commands.values())

    def get_command(self, name: str) -> SlashCommand | None:
        normalized = name.strip().lstrip("/")
        if not normalized:
            return None
        if " " in normalized:
            return self.get_command_path(normalized.split())
        return self._commands.get(normalized) or self.get_command_path([normalized])

    def _max_route_length(self) -> int:
        if not self._routes:
            return 1
        return max(len(route) for route in self._routes)


def _normalize_route_tokens(tokens: list[str]) -> list[str]:
    if not tokens:
        return []
    normalized = [tokens[0].lstrip("/")]
    normalized.extend(tokens[1:])
    return [token for token in normalized if token]
