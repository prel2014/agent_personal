from .helpers import print_lines
from .models import CommandContext, CommandResult, SlashCommand


def handle_help(ctx: CommandContext, args: list[str]) -> CommandResult:
    router = ctx.client.slash_router
    if args:
        if len(args) > 2:
            raise ValueError("Uso: /help [comando|menu subcomando]")

        command = router.get_command_path(args)
        if command is None and len(args) == 1:
            name = args[0].lstrip("/")
            command = router.get_command(name)

        if command is not None:
            _print_command_help(ctx, command)
            return CommandResult()

        if len(args) == 1:
            menu = args[0].lstrip("/")
            children = router.list_subcommands(menu)
            if children:
                _print_subcommand_menu(ctx, menu, children)
                return CommandResult()

        command_name = " ".join(arg.lstrip("/") for arg in args)
        raise ValueError(f"No existe el comando '/{command_name}'.")

    grouped: dict[str, list[SlashCommand]] = {}
    for command in router.list_commands():
        grouped.setdefault(command.category, []).append(command)

    if ctx.renderer.rich_output and getattr(ctx.renderer, "console", None) is not None:
        _print_rich_command_menu(ctx, grouped)
        return CommandResult()

    ctx.renderer.print_line("Comandos slash disponibles:", style="bold cyan")
    for category, commands in grouped.items():
        ctx.renderer.print_line(f"{category}:", style="bold")
        for parent, command in _plain_menu_rows(commands):
            if command is None:
                ctx.renderer.print_line(f"  /{parent}", style="bold")
                continue
            prefix = "    " if parent else "  "
            ctx.renderer.print_line(
                f"{prefix}{command.display_invocation:<20} {command.summary}"
            )
    ctx.renderer.print_line("Usa /help <comando> o /help <menu> <subcomando> para ver detalles.")
    return CommandResult()


def _print_command_help(ctx: CommandContext, command: SlashCommand) -> None:
    if ctx.renderer.rich_output and getattr(ctx.renderer, "console", None) is not None:
        from rich.panel import Panel
        from rich.table import Table

        table = Table.grid(padding=(0, 2))
        table.add_column(style="bold cyan")
        table.add_column()
        table.add_row("Uso", command.usage)
        table.add_row("Categoria", command.category)
        if command.examples:
            table.add_row("Ejemplos", "\n".join(command.examples))

        ctx.renderer.console.print(
            Panel(
                table,
                title=command.display_invocation,
                subtitle=command.summary,
                border_style="cyan",
            )
        )
        return

    ctx.renderer.print_line(command.display_invocation, style="bold cyan")
    ctx.renderer.print_line(command.summary)
    ctx.renderer.print_line(f"Uso: {command.usage}")
    if command.examples:
        ctx.renderer.print_line("Ejemplos:")
        print_lines(ctx, [f"  {example}" for example in command.examples])


def _print_subcommand_menu(
    ctx: CommandContext,
    menu: str,
    commands: list[SlashCommand],
) -> None:
    if ctx.renderer.rich_output and getattr(ctx.renderer, "console", None) is not None:
        from rich.panel import Panel
        from rich.table import Table

        table = Table.grid(padding=(0, 2))
        table.add_column(style="bold cyan")
        table.add_column(style="green")
        table.add_column()
        for command in commands:
            subcommand = command.command_path[1]
            table.add_row(subcommand, command.usage, command.summary)

        ctx.renderer.console.print(
            Panel(
                table,
                title=f"/{menu}",
                subtitle="Subcomandos disponibles",
                border_style="cyan",
            )
        )
        return

    ctx.renderer.print_line(f"/{menu}", style="bold cyan")
    for command in commands:
        subcommand = command.command_path[1]
        ctx.renderer.print_line(f"  {subcommand:<10} {command.summary}")


def _print_rich_command_menu(
    ctx: CommandContext,
    grouped: dict[str, list[SlashCommand]],
) -> None:
    from rich.table import Table

    table = Table(
        title="Comandos slash",
        show_header=True,
        header_style="bold cyan",
        expand=False,
    )
    table.add_column("Comando", style="bold")
    table.add_column("Uso", style="green")
    table.add_column("Descripcion")

    for category, commands in grouped.items():
        table.add_section()
        table.add_row(f"[cyan]{category}[/cyan]", "", "")
        for parent, command in _plain_menu_rows(commands):
            if command is None:
                table.add_row(f"/{parent}", "", "submenu")
                continue
            command_text = (
                f"  {command.command_path[1]}"
                if parent
                else command.display_invocation
            )
            table.add_row(command_text, command.usage, command.summary)

    ctx.renderer.console.print(table)
    ctx.renderer.print_line(
        "Usa /help <comando> o /help <menu> <subcomando> para ver detalles.",
        style="dim",
    )


def _plain_menu_rows(
    commands: list[SlashCommand],
) -> list[tuple[str | None, SlashCommand | None]]:
    rows: list[tuple[str | None, SlashCommand | None]] = []
    seen_parents: set[str] = set()
    for command in sorted(commands, key=lambda item: item.command_path):
        path = command.command_path
        if len(path) > 1:
            parent = path[0]
            if parent not in seen_parents:
                rows.append((parent, None))
                seen_parents.add(parent)
            rows.append((parent, command))
            continue
        rows.append((None, command))
    return rows
