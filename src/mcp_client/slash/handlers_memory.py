from __future__ import annotations

from .models import CommandContext, CommandResult


def _project_store(ctx: CommandContext):
    provider = getattr(ctx.client, "memory_provider", None)
    if provider is None:
        raise ValueError("La memoria está desactivada en esta sesión (--no-memory).")
    store = provider.project_store
    if store is None:
        raise ValueError("La memoria de proyecto está desactivada.")
    return store


def _user_store(ctx: CommandContext):
    provider = getattr(ctx.client, "memory_provider", None)
    if provider is None:
        raise ValueError("La memoria está desactivada en esta sesión (--no-memory).")
    store = provider.user_store
    if store is None:
        raise ValueError("La memoria de usuario está desactivada.")
    return store


def handle_memory_list(ctx: CommandContext, args: list[str]) -> CommandResult:
    provider = getattr(ctx.client, "memory_provider", None)
    if provider is None:
        ctx.renderer.print_line("Memoria desactivada.")
        return CommandResult()

    entries = []
    if provider.project_store is not None:
        for e in provider.project_store.list_memories(limit=50):
            entries.append(("proyecto", e.get("key", ""), e.get("value", "")))
    if provider.user_store is not None:
        for e in provider.user_store.list_memories(limit=50):
            entries.append(("usuario", e.get("key", ""), e.get("value", "")))

    if not entries:
        ctx.renderer.print_line("No hay memorias almacenadas.")
        return CommandResult()

    lines = [f"  [{scope}] {key}: {value}" for scope, key, value in entries]
    ctx.renderer.print_line("\n".join(lines))
    return CommandResult()


def handle_memory_add(ctx: CommandContext, args: list[str]) -> CommandResult:
    if len(args) < 2:
        raise ValueError("Uso: /memory add <clave> <valor>")
    key = args[0]
    value = " ".join(args[1:])
    store = _project_store(ctx)
    store.remember(key, value)
    ctx.renderer.print_line(f"Memoria guardada: '{key}' = '{value}'")
    return CommandResult()


def handle_memory_user_add(ctx: CommandContext, args: list[str]) -> CommandResult:
    if len(args) < 2:
        raise ValueError("Uso: /memory user add <clave> <valor>")
    key = args[0]
    value = " ".join(args[1:])
    store = _user_store(ctx)
    store.remember(key, value)
    ctx.renderer.print_line(f"Memoria de usuario guardada: '{key}' = '{value}'")
    return CommandResult()


def handle_memory_search(ctx: CommandContext, args: list[str]) -> CommandResult:
    if not args:
        raise ValueError("Uso: /memory search <query>")
    query = " ".join(args)
    provider = getattr(ctx.client, "memory_provider", None)
    if provider is None:
        ctx.renderer.print_line("Memoria desactivada.")
        return CommandResult()
    results = provider.recall(query)
    if not results:
        ctx.renderer.print_line(f"No se encontraron memorias para: '{query}'")
        return CommandResult()
    lines = [f"  {r.get('key', '')}: {r.get('value', '')}  (score={r.get('score', 0):.3f})" for r in results]
    ctx.renderer.print_line("\n".join(lines))
    return CommandResult()


def handle_memory_forget(ctx: CommandContext, args: list[str]) -> CommandResult:
    if not args:
        raise ValueError("Uso: /memory forget <clave>")
    key = args[0]
    store = _project_store(ctx)
    result = store.forget(key)
    deleted = result.get("deleted", 0)
    if deleted:
        ctx.renderer.print_line(f"Memoria '{key}' eliminada.")
    else:
        ctx.renderer.print_line(f"No se encontró la memoria '{key}'.")
    return CommandResult()


def handle_memory_user_forget(ctx: CommandContext, args: list[str]) -> CommandResult:
    if not args:
        raise ValueError("Uso: /memory user forget <clave>")
    key = args[0]
    store = _user_store(ctx)
    result = store.forget(key)
    deleted = result.get("deleted", 0)
    if deleted:
        ctx.renderer.print_line(f"Memoria de usuario '{key}' eliminada.")
    else:
        ctx.renderer.print_line(f"No se encontró la memoria de usuario '{key}'.")
    return CommandResult()
