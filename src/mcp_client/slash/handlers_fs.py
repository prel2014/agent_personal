import json

from .helpers import (
    call_tool,
    parse_positive_int,
    relative_display_path,
    require_no_args,
)
from .models import CommandContext, CommandResult


def handle_pwd(ctx: CommandContext, args: list[str]) -> CommandResult:
    require_no_args(args, "/pwd")
    ctx.renderer.print_line(str(call_tool(ctx, "pwd")))
    return CommandResult()


def handle_ls(ctx: CommandContext, args: list[str]) -> CommandResult:
    if len(args) > 1:
        raise ValueError("Uso: /ls [ruta]")

    path = args[0] if args else "."
    payload: dict[str, object] = {}
    if args:
        payload["path"] = path

    items = call_tool(ctx, "listdir", payload)
    if isinstance(items, str):
        items = json.loads(items)

    ctx.renderer.print_json(items)
    return CommandResult()


def handle_tree(ctx: CommandContext, args: list[str]) -> CommandResult:
    if len(args) > 2:
        raise ValueError("Uso: /tree [ruta] [depth]")

    path = args[0] if args else "."
    depth = parse_positive_int(args[1], "depth") if len(args) == 2 else 3
    tree = call_tool(ctx, "list_tree", {"path": path, "depth": depth})
    ctx.renderer.print_line(str(tree))
    return CommandResult()


def handle_read(ctx: CommandContext, args: list[str]) -> CommandResult:
    if len(args) != 1:
        raise ValueError("Uso: /read <archivo>")

    content = str(call_tool(ctx, "readfile", {"path": args[0]}))
    ctx.renderer.print_line(content, end="" if content.endswith("\n") else "\n")
    return CommandResult()


def handle_head(ctx: CommandContext, args: list[str]) -> CommandResult:
    if not args or len(args) > 2:
        raise ValueError("Uso: /head <archivo> [n]")

    path = args[0]
    count = parse_positive_int(args[1], "n") if len(args) == 2 else 20
    result = call_tool(ctx, "read_lines", {"path": path, "start": 1, "end": count})
    lines = result.get("lines", []) if isinstance(result, dict) else []

    if not lines:
        ctx.renderer.print_line("(sin contenido)")
        return CommandResult()

    for item in lines:
        ctx.renderer.print_line(f"{item['number']:>4}: {item['text']}")

    return CommandResult()


def handle_find(ctx: CommandContext, args: list[str]) -> CommandResult:
    if not args or len(args) > 2:
        raise ValueError("Uso: /find <texto> [glob]")

    query = args[0]
    payload: dict[str, object] = {"query": query, "max_results": 50}
    if len(args) == 2:
        payload["file_glob"] = args[1]

    results = call_tool(ctx, "search_code", payload)
    if not results:
        ctx.renderer.print_line("Sin coincidencias.")
        return CommandResult()

    for item in results:
        path = relative_display_path(ctx, item["path"])
        ctx.renderer.print_line(f"{path}:{item['line']} | {item['text']}")

    return CommandResult()


def handle_files(ctx: CommandContext, args: list[str]) -> CommandResult:
    if len(args) != 1:
        raise ValueError("Uso: /files <glob>")

    results = call_tool(ctx, "find_files", {"glob": args[0], "max_results": 200})
    if not results:
        ctx.renderer.print_line("Sin archivos coincidentes.")
        return CommandResult()

    for raw_path in results:
        ctx.renderer.print_line(relative_display_path(ctx, raw_path))

    return CommandResult()
