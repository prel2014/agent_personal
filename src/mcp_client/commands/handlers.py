from __future__ import annotations

import argparse

from ..agentic.trace_store import DEFAULT_TRACE_DB_PATH, SQLiteTraceStore
from ..app.cache_values import parse_cache_value


def dispatch_command(client, args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.command == "info":
        client.renderer.print_json(client.info())
        return 0

    if args.command == "health":
        client.renderer.print_json(client.health())
        return 0

    if args.command == "list-tools":
        client.renderer.print_json(client.list_tools())
        return 0

    if args.command == "list-nodes":
        client.renderer.print_json(client.list_nodes())
        return 0

    if args.command == "list-prompts":
        client.renderer.print_json(client.list_prompts())
        return 0

    if args.command == "doctor":
        client.renderer.print_json(client.doctor())
        return 0

    if args.command == "setup":
        client.renderer.print_json(client.setup())
        return 0

    if args.command == "sessions":
        return _dispatch_sessions_command(client, args)

    if args.command == "cache":
        return _dispatch_cache_command(client, args)

    if args.command == "export-dataset":
        return _dispatch_export_dataset_command(client, args)

    if args.command == "ask":
        return _dispatch_ask_command(client, args)

    if args.command == "repl":
        return client.repl(
            session_id=args.session,
            continue_session=args.continue_session,
        )

    if args.command == "skills":
        return _dispatch_skills_command(client, args)

    if args.command == "memory":
        return _dispatch_memory_command(client, args)

    parser.print_help()
    return 1


def _dispatch_skills_command(client, args: argparse.Namespace) -> int:
    if args.skills_command == "list":
        catalog = client.list_skills()
        if not catalog:
            client.renderer.print_line("No hay skills disponibles.")
            return 0
        active = getattr(client, "active_skill", None)
        for entry in catalog:
            name = entry.get("name", "")
            desc = entry.get("description", "")
            scope = entry.get("scope", "all")
            marker = " [activo]" if name == active else ""
            client.renderer.print_line(f"  {name}{marker}  ({scope})  — {desc}")
        return 0

    if args.skills_command == "show":
        skill = client.skill_registry.get(args.name)
        if skill is None:
            client.renderer.print_line(f"Skill desconocido: '{args.name}'")
            return 1
        client.renderer.print_line(
            f"name: {skill.name}\ndescription: {skill.description}\n"
            f"scope: {skill.scope}\nsource: {skill.source}\n\n{skill.directive}"
        )
        return 0

    return 1


def _dispatch_memory_command(client, args: argparse.Namespace) -> int:
    provider = getattr(client, "memory_provider", None)

    if args.memory_command == "list":
        if provider is None:
            client.renderer.print_line("Memoria desactivada.")
            return 0
        entries = []
        if provider.project_store is not None:
            for e in provider.project_store.list_memories(limit=100):
                entries.append(("proyecto", e.get("key", ""), e.get("value", "")))
        if provider.user_store is not None:
            for e in provider.user_store.list_memories(limit=100):
                entries.append(("usuario", e.get("key", ""), e.get("value", "")))
        if not entries:
            client.renderer.print_line("No hay memorias almacenadas.")
        for scope, key, value in entries:
            client.renderer.print_line(f"  [{scope}] {key}: {value}")
        return 0

    if args.memory_command == "add":
        if provider is None or provider.project_store is None:
            client.renderer.print_line("Memoria de proyecto desactivada.")
            return 1
        value = " ".join(args.value)
        provider.project_store.remember(args.key, value)
        client.renderer.print_line(f"Memoria guardada: '{args.key}' = '{value}'")
        return 0

    if args.memory_command == "forget":
        if provider is None or provider.project_store is None:
            client.renderer.print_line("Memoria de proyecto desactivada.")
            return 1
        result = provider.project_store.forget(args.key)
        deleted = result.get("deleted", 0)
        msg = f"Memoria '{args.key}' eliminada." if deleted else f"No se encontró '{args.key}'."
        client.renderer.print_line(msg)
        return 0

    if args.memory_command == "search":
        if provider is None:
            client.renderer.print_line("Memoria desactivada.")
            return 0
        query = " ".join(args.query)
        results = provider.recall(query)
        if not results:
            client.renderer.print_line(f"Sin resultados para: '{query}'")
        for r in results:
            client.renderer.print_line(f"  {r.get('key', '')}: {r.get('value', '')}")
        return 0

    if args.memory_command == "clear":
        if provider is None or provider.project_store is None:
            client.renderer.print_line("Memoria de proyecto desactivada.")
            return 1
        provider.project_store._store.clear(namespace="memories")
        client.renderer.print_line("Memoria de proyecto vaciada.")
        return 0

    return 1


def _dispatch_sessions_command(client, args: argparse.Namespace) -> int:
    if args.sessions_command == "list":
        client.renderer.print_json(client.list_sessions(limit=args.limit))
        return 0

    if args.sessions_command == "show":
        client.renderer.print_json(client.show_session(args.session_id))
        return 0

    if args.sessions_command == "rename":
        client.renderer.print_json(
            client.rename_session(args.session_id, " ".join(args.title))
        )
        return 0

    if args.sessions_command == "close":
        client.renderer.print_json(client.close_session(args.session_id))
        return 0

    return 1


def _dispatch_cache_command(client, args: argparse.Namespace) -> int:
    if args.cache_command == "get":
        client.renderer.print_json(client.cache_get(args.namespace, args.key))
        return 0

    if args.cache_command == "set":
        client.renderer.print_json(
            client.cache_set(
                args.namespace,
                args.key,
                parse_cache_value(args.value),
                ttl_seconds=args.ttl_seconds,
            )
        )
        return 0

    if args.cache_command == "delete":
        client.renderer.print_json(client.cache_delete(args.namespace, args.key))
        return 0

    if args.cache_command == "list":
        client.renderer.print_json(
            client.cache_list(
                namespace=args.namespace,
                prefix=args.prefix,
                limit=args.limit,
            )
        )
        return 0

    if args.cache_command == "clear":
        client.renderer.print_json(
            client.cache_clear(
                namespace=args.namespace,
                expired_only=args.expired_only,
            )
        )
        return 0

    return 1


def _dispatch_export_dataset_command(client, args: argparse.Namespace) -> int:
    db_path = args.db_path or client.config.trace_db_path or DEFAULT_TRACE_DB_PATH
    count = SQLiteTraceStore(db_path).export_dataset_jsonl(
        output_path=args.output,
        example_type=args.example_type,
        limit=args.limit,
    )
    client.renderer.print_json(
        {
            "ok": True,
            "db_path": db_path,
            "output": args.output,
            "example_type": args.example_type,
            "examples": count,
        }
    )
    return 0


def _dispatch_ask_command(client, args: argparse.Namespace) -> int:
    prompt = " ".join(args.prompt)
    result = client.ask(
        prompt,
        session_id=args.session,
        new_session=args.new_session,
    )
    payload = {
        "final": result["final"],
        "steps": len(result["messages"]),
        "auto_written_files": result.get("auto_written_files", []),
    }
    if result.get("session_id"):
        payload["session_id"] = result["session_id"]
    client.renderer.print_json(payload)
    return 0
