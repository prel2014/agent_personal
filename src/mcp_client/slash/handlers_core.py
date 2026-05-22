from .helpers import require_no_args
from .models import CommandContext, CommandResult


def handle_info(ctx: CommandContext, args: list[str]) -> CommandResult:
    require_no_args(args, "/info")
    ctx.renderer.print_json(ctx.client.info())
    return CommandResult()


def handle_health(ctx: CommandContext, args: list[str]) -> CommandResult:
    require_no_args(args, "/health")
    ctx.renderer.print_json(ctx.client.health())
    return CommandResult()


def handle_tools(ctx: CommandContext, args: list[str]) -> CommandResult:
    require_no_args(args, "/tools")
    ctx.renderer.print_json(ctx.client.list_tools())
    return CommandResult()


def handle_prompts(ctx: CommandContext, args: list[str]) -> CommandResult:
    require_no_args(args, "/prompts")
    ctx.renderer.print_json(ctx.client.list_prompts())
    return CommandResult()


def handle_perms(ctx: CommandContext, args: list[str]) -> CommandResult:
    require_no_args(args, "/perms")
    ctx.renderer.print_json(ctx.runtime.info()["permissions"])
    return CommandResult()


def handle_mode(ctx: CommandContext, args: list[str]) -> CommandResult:
    if len(args) > 1:
        raise ValueError("Uso: /mode [auto|direct|team]")

    if not args:
        ctx.renderer.print_line(f"Modo de planning actual: {ctx.client.config.planning_mode}")
        return CommandResult()

    aliases = {
        "auto": "auto",
        "direct": "never",
        "simple": "never",
        "never": "never",
        "team": "always",
        "always": "always",
    }
    requested = args[0].strip().lower()
    mode = aliases.get(requested)
    if mode is None:
        raise ValueError("Modo invalido. Usa auto, direct o team.")

    ctx.client.set_planning_mode(mode)
    ctx.renderer.print_line(f"Modo de planning actualizado: {mode}", style="green")
    return CommandResult()


def handle_thinking(ctx: CommandContext, args: list[str]) -> CommandResult:
    if len(args) > 1:
        raise ValueError("Uso: /thinking [on|off|toggle]")

    if not args or args[0].strip().lower() == "toggle":
        enabled = ctx.client.toggle_show_thinking()
    else:
        requested = args[0].strip().lower()
        if requested not in {"on", "off"}:
            raise ValueError("Uso: /thinking [on|off|toggle]")
        enabled = ctx.client.set_show_thinking(requested == "on")

    state = "ON" if enabled else "OFF"
    ctx.renderer.print_line(
        f"Thinking visible: {state}",
        style="yellow" if ctx.renderer.rich_output else None,
    )
    return CommandResult()


def handle_questions(ctx: CommandContext, args: list[str]) -> CommandResult:
    if len(args) > 1:
        raise ValueError("Uso: /questions [auto|manual|toggle|status]")

    if not args or args[0].strip().lower() == "status":
        state = "AUTO" if ctx.client.auto_answer_questions else "MANUAL"
        ctx.renderer.print_line(
            f"Preguntas del agente: {state}",
            style="yellow" if ctx.renderer.rich_output else None,
        )
        return CommandResult()

    requested = args[0].strip().lower()
    if requested == "toggle":
        enabled = ctx.client.toggle_auto_answer_questions()
    elif requested == "auto":
        enabled = ctx.client.set_auto_answer_questions(True)
    elif requested == "manual":
        enabled = ctx.client.set_auto_answer_questions(False)
    else:
        raise ValueError("Uso: /questions [auto|manual|toggle|status]")

    state = "AUTO" if enabled else "MANUAL"
    ctx.renderer.print_line(
        f"Preguntas del agente: {state}",
        style="yellow" if ctx.renderer.rich_output else None,
    )
    return CommandResult()


def handle_output(ctx: CommandContext, args: list[str]) -> CommandResult:
    if len(args) > 1:
        raise ValueError("Uso: /output [minimal|normal|debug]")

    if not args:
        ctx.renderer.print_line(
            f"Modo de salida: {ctx.client.config.output_mode}",
            style="yellow" if ctx.renderer.rich_output else None,
        )
        return CommandResult()

    mode = ctx.client.set_output_mode(args[0])
    ctx.renderer.print_line(
        f"Modo de salida actualizado: {mode}",
        style="green",
    )
    return CommandResult()


def handle_status(ctx: CommandContext, args: list[str]) -> CommandResult:
    require_no_args(args, "/status")
    repl = ctx.repl_session
    session_id = repl.current_session_id if repl is not None else None
    ctx.renderer.print_json(
        {
            "session_id": session_id,
            "message_count": len(repl.messages) if repl is not None else None,
            "planning_mode": ctx.client.config.planning_mode,
            "output_mode": ctx.client.config.output_mode,
            "auto_answer_questions": ctx.client.auto_answer_questions,
            "server_url": ctx.client.config.server_url,
            "base_dir": str(ctx.runtime.config.base_dir),
            "trace_capture": ctx.client.config.trace_capture,
            "session_db_path": ctx.client.config.session_db_path,
            "kv_cache_enabled": ctx.client.config.kv_cache_enabled,
            "kv_cache_db_path": ctx.client.config.kv_cache_db_path,
            "context_window_tokens": ctx.client.config.context_window_tokens,
            "show_context_meter": ctx.client.config.show_context_meter,
            "permissions": ctx.runtime.info()["permissions"],
        }
    )
    return CommandResult()


def handle_clear(ctx: CommandContext, args: list[str]) -> CommandResult:
    require_no_args(args, "/clear")
    ctx.renderer.print_line("Conversacion limpiada.", style="green")
    return CommandResult(clear_messages=True)


def handle_exit(ctx: CommandContext, args: list[str]) -> CommandResult:
    require_no_args(args, "/exit")
    return CommandResult(exit_repl=True)
