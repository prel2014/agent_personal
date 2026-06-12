from .models import CommandContext, CommandResult
from ..app.cache_values import parse_cache_value


def handle_cache_get(ctx: CommandContext, args: list[str]) -> CommandResult:
    if len(args) != 2:
        raise ValueError("Uso: /cache get <namespace> <key>")
    ctx.renderer.print_json(ctx.client.cache_get(args[0], args[1]))
    return CommandResult()


def handle_cache_set(ctx: CommandContext, args: list[str]) -> CommandResult:
    if len(args) < 3:
        raise ValueError("Uso: /cache set <namespace> <key> <value>")
    ctx.renderer.print_json(
        ctx.client.cache_set(args[0], args[1], parse_cache_value(" ".join(args[2:])))
    )
    return CommandResult()


def handle_cache_list(ctx: CommandContext, args: list[str]) -> CommandResult:
    if len(args) > 1:
        raise ValueError("Uso: /cache list [namespace]")
    namespace = args[0] if args else None
    ctx.renderer.print_json(ctx.client.cache_list(namespace=namespace, limit=100))
    return CommandResult()


def handle_cache_search(ctx: CommandContext, args: list[str]) -> CommandResult:
    if not args:
        raise ValueError("Uso: /cache search <query> [namespace]")
    query = args[0]
    namespace = args[1] if len(args) > 1 else None
    ctx.renderer.print_json(ctx.client.cache_search(query, namespace=namespace))
    return CommandResult()
