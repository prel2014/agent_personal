import argparse

from src.mcp.settings import add_config_arguments as add_runtime_arguments


def add_client_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    add_runtime_arguments(parser)
    parser.add_argument(
        "--server-url",
        help="URL base del servidor HTTP que razona con Ollama.",
    )
    parser.add_argument(
        "--client-name",
        help="Nombre del cliente CLI.",
    )
    parser.add_argument(
        "--client-version",
        help="Version del cliente CLI.",
    )
    parser.add_argument(
        "--server-bearer-token",
        help="Token Bearer para autenticar contra mcp_server cuando este protegido.",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        help="Maximo de iteraciones tool-call por prompt.",
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        help="Timeout HTTP del cliente hacia mcp_server en segundos.",
    )
    parser.add_argument(
        "--no-stream",
        dest="stream_responses",
        action="store_false",
        default=None,
        help="Desactiva streaming de respuestas y usa modo bloqueante.",
    )
    parser.add_argument(
        "--show-thinking",
        action="store_true",
        default=None,
        help="Muestra el campo thinking devuelto por Ollama cuando exista.",
    )
    parser.add_argument(
        "--no-auto-write-code",
        dest="auto_write_code",
        action="store_false",
        default=None,
        help="Desactiva la extraccion y escritura automatica de codigo devuelto en Markdown.",
    )
    parser.add_argument(
        "--plain-output",
        dest="rich_output",
        action="store_false",
        default=None,
        help="Desactiva Markdown, colores y resaltado de sintaxis en la terminal.",
    )
    parser.add_argument(
        "--output-mode",
        choices=("minimal", "normal", "debug"),
        help="Nivel de detalle de salida del CLI. Por defecto: normal.",
    )
    parser.add_argument(
        "--no-orchestrate-agents",
        dest="orchestrate_agents",
        action="store_false",
        default=None,
        help="Alias de --planning-mode never. Desactiva planner-worker-reviewer.",
    )
    parser.add_argument(
        "--planning-mode",
        choices=("auto", "always", "never"),
        help="Decide si usar respuesta directa o planner-worker-reviewer.",
    )
    parser.add_argument(
        "--planner-max-steps",
        type=int,
        help="Maximo de iteraciones para el planner.",
    )
    parser.add_argument(
        "--reviewer-max-steps",
        type=int,
        help="Maximo de iteraciones para el reviewer.",
    )
    parser.add_argument(
        "--review-retries",
        type=int,
        help="Cantidad de ciclos extra de correccion tras feedback del reviewer.",
    )
    parser.add_argument(
        "--trace-db-path",
        help="Ruta SQLite donde se persistiran trazas y ejemplos de dataset.",
    )
    parser.add_argument(
        "--trace-capture",
        choices=("off", "metadata", "full"),
        help=(
            "Nivel de captura SQLite: off desactiva, metadata guarda eventos sin "
            "contenido completo, full guarda conversaciones y resultados sanitizados."
        ),
    )
    parser.add_argument(
        "--trace-thinking",
        choices=("off", "summary", "raw"),
        help=(
            "Politica para el campo thinking de modelos compatibles. Por defecto "
            "usa raw cuando --trace-capture esta activo; off y summary son overrides."
        ),
    )
    parser.add_argument(
        "--session-db-path",
        help="Ruta SQLite para sesiones persistentes del cliente.",
    )
    parser.add_argument(
        "--allow-remote-sensitive-tracing",
        action="store_true",
        default=None,
        help=(
            "Permite trace_capture=full o trace_thinking=raw contra un servidor remoto "
            "no local. No recomendado."
        ),
    )
    parser.add_argument(
        "--context-window-tokens",
        type=int,
        help=(
            "Tamano de ventana de contexto usado para el medidor local. "
            "Por defecto 131072."
        ),
    )
    parser.add_argument(
        "--show-context-meter",
        dest="show_context_meter",
        action="store_true",
        default=None,
        help="Muestra el medidor estimado de contexto.",
    )
    parser.add_argument(
        "--no-context-meter",
        dest="show_context_meter",
        action="store_false",
        default=None,
        help="Oculta el medidor estimado de uso de ventana de contexto.",
    )
    parser.add_argument(
        "--skill",
        dest="skill",
        metavar="NAME",
        default=None,
        help="Activa un skill por nombre en esta sesion (ej: --skill concise-responder).",
    )
    parser.add_argument(
        "--no-memory",
        dest="no_memory",
        action="store_true",
        default=False,
        help="Desactiva la inyeccion automatica de memoria en esta sesion.",
    )
    parser.add_argument(
        "--memory-top-k",
        dest="memory_top_k",
        type=int,
        default=None,
        help="Numero de memorias a recuperar por turno (default: 3).",
    )

    return parser
