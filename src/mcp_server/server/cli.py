from __future__ import annotations

import argparse

from ..settings import add_server_arguments, load_server_config
from .http import MCPHTTPServer, MCPRequestHandler
from ..nodes import NodeProbeResult
from .service import OrchestratorService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Servidor REST que usa Ollama para razonar y devolver tool calls."
    )
    add_server_arguments(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config = load_server_config(args)
    service = OrchestratorService(config)
    if config.discovery_enabled:
        print("[discovery] iniciando sondeo de nodos Ollama...")
    discovery_report = service.startup_discovery_report(
        progress_callback=_print_discovery_progress,
    )
    httpd = MCPHTTPServer((config.host, config.port), MCPRequestHandler, service)

    print(
        f"mcp_server escuchando en http://{config.host}:{config.port} "
        f"usando modelo {service.ollama.node_registry.local_node.model}"
    )
    _print_discovery_report(discovery_report)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()

    return 0


def _print_discovery_report(report: dict[str, object]) -> None:
    if not report.get("enabled"):
        return

    candidate_count = int(report.get("candidate_count", 0))
    reachable_count = int(report.get("reachable_count", 0))
    promoted_count = int(report.get("promoted_count", 0))
    print(
        "[discovery] "
        f"sondeados {candidate_count} candidatos; "
        f"alcanzables {reachable_count}; "
        f"auto-promovidos {promoted_count}"
    )

    reachable = report.get("reachable", [])
    if not isinstance(reachable, list):
        return

    for item in reachable[:20]:
        if not isinstance(item, dict):
            continue
        models = item.get("available_models", [])
        model_text = ", ".join(models[:6]) if isinstance(models, list) else ""
        print(f"[discovery] {item.get('base_url')} modelos: {model_text}")

    if len(reachable) > 20:
        print(f"[discovery] ... {len(reachable) - 20} nodos alcanzables mas")


def _print_discovery_progress(
    event: str,
    base_url: str,
    result: NodeProbeResult | None,
) -> None:
    if event == "start":
        print(f"[scan] probando {base_url}")
        return

    if result is None:
        print(f"[scan] {base_url} sin resultado")
        return

    if result.reachable:
        models = ", ".join(result.available_models[:6]) or "(sin modelos)"
        print(f"[scan] {base_url} OK modelos: {models}")
        return

    error = result.error or "sin respuesta"
    print(f"[scan] {base_url} fallo: {error}")


if __name__ == "__main__":
    raise SystemExit(main())
