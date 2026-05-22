import argparse
import json
import sys

from .settings import add_config_arguments, load_config
from .runtime import LocalToolRuntime


def _parse_json_arguments(raw_value: str | None) -> dict[str, object]:
    if not raw_value:
        return {}

    value = json.loads(raw_value)
    if not isinstance(value, dict):
        raise ValueError("Los argumentos deben ser un objeto JSON.")

    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Wrapper local del runtime compartido de tools y prompts."
    )
    add_config_arguments(parser)

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("info", help="Muestra la configuracion activa.")
    subparsers.add_parser("list-tools", help="Lista las herramientas registradas.")
    subparsers.add_parser("list-prompts", help="Lista los prompts registrados.")

    call_tool_parser = subparsers.add_parser("call-tool", help="Ejecuta una tool.")
    call_tool_parser.add_argument("name", help="Nombre de la tool.")
    call_tool_parser.add_argument(
        "--arguments",
        help='Objeto JSON con argumentos. Ejemplo: {"path":"demo.txt"}',
    )

    render_prompt_parser = subparsers.add_parser("render-prompt", help="Renderiza un prompt.")
    render_prompt_parser.add_argument("name", help="Nombre del prompt.")
    render_prompt_parser.add_argument(
        "--arguments",
        help='Objeto JSON con argumentos. Ejemplo: {"path":"main.py"}',
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        runtime = LocalToolRuntime(load_config(args))

        if args.command == "info":
            print(json.dumps(runtime.info(), ensure_ascii=False, indent=2))
            return 0

        if args.command == "list-tools":
            print(json.dumps(runtime.list_tools(), ensure_ascii=False, indent=2))
            return 0

        if args.command == "list-prompts":
            print(json.dumps(runtime.list_prompts(), ensure_ascii=False, indent=2))
            return 0

        if args.command == "call-tool":
            arguments = _parse_json_arguments(args.arguments)
            print(
                json.dumps(
                    runtime.call_tool(args.name, arguments),
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0

        if args.command == "render-prompt":
            arguments = _parse_json_arguments(args.arguments)
            print(
                json.dumps(
                    runtime.render_prompt(args.name, arguments),
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
