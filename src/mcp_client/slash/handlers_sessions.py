from .models import CommandContext, CommandResult
from src.mcp_shared.contracts import ChatResponse
from ..prompts import (
    build_compact_client_context,
    build_compact_prompt,
    compacted_context_message,
)
from ..sessions.store import title_from_prompt


def handle_sessions(ctx: CommandContext, args: list[str]) -> CommandResult:
    if len(args) > 1:
        raise ValueError("Uso: /session list [limite]")

    limit = 10
    if args:
        try:
            limit = int(args[0])
        except ValueError as exc:
            raise ValueError("Uso: /session list [limite]") from exc
        if limit < 1:
            raise ValueError("El limite debe ser mayor o igual a 1.")

    ctx.renderer.print_json(ctx.client.list_sessions(limit=limit))
    return CommandResult()


def handle_resume(ctx: CommandContext, args: list[str]) -> CommandResult:
    if len(args) != 1:
        raise ValueError("Uso: /session resume <session_id>")
    repl = _require_repl(ctx, "/resume")
    session_id = args[0]
    session = ctx.client.session_store.require_session(session_id)
    repl.current_session_id = session.id
    repl.messages = ctx.client.session_store.load_messages(session.id)
    ctx.renderer.print_line(
        f"Sesion reanudada: {session.id} ({session.message_count} mensajes)",
        style="green",
    )
    return CommandResult()


def handle_new(ctx: CommandContext, args: list[str]) -> CommandResult:
    repl = _require_repl(ctx, "/new")
    title = " ".join(args).strip() if args else None
    session = ctx.client.session_store.create_session(
        title=title or title_from_prompt(None),
        metadata={"source": "repl"},
    )
    repl.current_session_id = session.id
    repl.messages = []
    ctx.renderer.print_line(f"Nueva sesion: {session.id}", style="green")
    return CommandResult(clear_messages=True)


def handle_save(ctx: CommandContext, args: list[str]) -> CommandResult:
    repl = _require_repl(ctx, "/save")
    title = " ".join(args).strip() if args else None

    if repl.current_session_id is None:
        session = ctx.client.session_store.create_session(
            title=title or _title_from_messages(repl.messages),
            metadata={"source": "repl"},
        )
        repl.current_session_id = session.id
    elif title:
        ctx.client.session_store.rename_session(repl.current_session_id, title)

    ctx.client.session_store.replace_messages(repl.current_session_id, repl.messages)
    session = ctx.client.session_store.require_session(repl.current_session_id)
    ctx.renderer.print_line(
        f"Sesion guardada: {session.id} ({session.message_count} mensajes)",
        style="green",
    )
    return CommandResult()


def handle_compact(ctx: CommandContext, args: list[str]) -> CommandResult:
    repl = _require_repl(ctx, "/compact")
    if not repl.messages:
        ctx.renderer.print_line("No hay conversacion para compactar.", style="yellow")
        return CommandResult()

    focus = " ".join(args).strip()
    original_count = len(repl.messages)
    prompt = build_compact_prompt(focus)
    response = ChatResponse.from_wire(
        ctx.client.api.chat(
            messages=[*repl.messages, {"role": "user", "content": prompt}],
            tools=[],
            client_context=build_compact_client_context(ctx),
        )
    )
    if not response.ok:
        raise RuntimeError(response.error or "No se pudo compactar la conversacion.")

    summary = response.message.content.strip()
    if not summary:
        raise RuntimeError("El modelo devolvio un resumen vacio.")

    repl.messages = [
        {
            "role": "assistant",
            "content": compacted_context_message(summary),
        }
    ]
    if repl.current_session_id:
        ctx.client.session_store.replace_messages(repl.current_session_id, repl.messages)

    ctx.renderer.print_line(
        f"Conversacion compactada: {original_count} mensajes -> 1 resumen.",
        style="green",
    )
    return CommandResult()


def _require_repl(ctx: CommandContext, command: str):
    if ctx.repl_session is None:
        raise ValueError(f"{command} solo esta disponible dentro del REPL.")
    return ctx.repl_session


def _title_from_messages(messages: list[dict[str, object]]) -> str:
    for message in messages:
        if message.get("role") == "user":
            return title_from_prompt(str(message.get("content") or ""))
    return title_from_prompt(None)
