from pathlib import Path

from .models import CommandContext


def parse_positive_int(raw_value: str, label: str) -> int:
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"'{label}' debe ser un entero.") from exc

    if value < 1:
        raise ValueError(f"'{label}' debe ser mayor o igual a 1.")

    return value


def call_tool(
    ctx: CommandContext,
    name: str,
    arguments: dict[str, object] | None = None,
):
    result = ctx.runtime.call_tool(name, arguments or {})
    if not result.get("success"):
        raise RuntimeError(result.get("error") or f"Fallo ejecutando la tool '{name}'.")

    return result.get("result")


def relative_display_path(ctx: CommandContext, raw_path: str) -> str:
    try:
        path = Path(raw_path)
        return str(path.relative_to(ctx.runtime.config.base_dir))
    except ValueError:
        return raw_path


def print_lines(ctx: CommandContext, lines: list[str]) -> None:
    for line in lines:
        ctx.renderer.print_line(line)


def require_no_args(args: list[str], usage: str) -> None:
    if args:
        raise ValueError(f"Uso: {usage}")
