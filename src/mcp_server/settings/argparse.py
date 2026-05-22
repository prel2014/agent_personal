from __future__ import annotations

import argparse


def add_server_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("--host", help="Host de escucha del servidor REST.")
    parser.add_argument("--port", type=int, help="Puerto del servidor REST.")
    parser.add_argument(
        "--auth-mode",
        choices=("off", "bearer_static"),
        help="Modo de autenticacion HTTP para mcp_server.",
    )
    parser.add_argument(
        "--auth-static-tokens",
        help="Lista separada por comas con tokens Bearer aceptados por el servidor.",
    )
    parser.add_argument(
        "--no-auth-for-info",
        dest="require_auth_for_info",
        action="store_false",
        default=None,
        help="Permite acceso publico a /info y /nodes incluso con auth habilitada.",
    )
    parser.add_argument(
        "--private-health",
        dest="public_health",
        action="store_false",
        default=None,
        help="Protege /health con la misma politica de autenticacion del servidor.",
    )
    parser.add_argument(
        "--ollama-base-url",
        help="URL base de Ollama. Ejemplo: http://127.0.0.1:11434",
    )
    parser.add_argument(
        "--model",
        help=(
            "Modelo de Ollama que se usara como fallback local. "
            "Omitelo o usa 'auto' para seleccionarlo desde /api/tags."
        ),
    )
    parser.add_argument(
        "--keep-alive",
        help="Valor keep_alive enviado a Ollama. Ejemplo: 5m.",
    )
    parser.add_argument(
        "--think",
        help="Valor think para Ollama: true, false, low, medium o high.",
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        help="Timeout de peticiones HTTP a Ollama en segundos.",
    )
    parser.add_argument(
        "--system-prompt",
        help="Prompt de sistema para el orquestador.",
    )
    parser.add_argument(
        "--nodes-config",
        help="Ruta a un JSON con nodos remotos de Ollama y roles asociados.",
    )
    parser.add_argument(
        "--no-local-fallback",
        dest="allow_local_fallback",
        action="store_false",
        default=None,
        help="Desactiva el fallback al nodo local cuando falla un nodo remoto.",
    )
    parser.add_argument(
        "--discover-nodes",
        dest="discovery_enabled",
        action="store_true",
        default=None,
        help="Habilita la deteccion automatica de instancias Ollama en red.",
    )
    parser.add_argument(
        "--no-discovery-auto-lan",
        dest="discovery_auto_lan",
        action="store_false",
        default=None,
        help=(
            "Desactiva la inferencia automatica de la red local cuando "
            "--discover-nodes no recibe hosts ni CIDR."
        ),
    )
    parser.add_argument(
        "--discovery-hosts",
        help=(
            "Lista separada por comas con hosts o URLs a sondear. "
            "Ejemplo: 192.168.1.20,192.168.1.21,http://192.168.1.22:11434"
        ),
    )
    parser.add_argument(
        "--discovery-cidrs",
        help=(
            "Lista separada por comas con rangos CIDR para sondeo. "
            "Ejemplo: 192.168.1.0/24,10.0.0.0/28"
        ),
    )
    parser.add_argument(
        "--discovery-port",
        type=int,
        help="Puerto por defecto usado al descubrir hosts sin URL explicita.",
    )
    parser.add_argument(
        "--discovery-timeout",
        type=float,
        help="Timeout por host durante el sondeo automatico.",
    )
    parser.add_argument(
        "--discovery-ttl-seconds",
        type=float,
        help="Segundos que dura en cache el resultado de descubrimiento.",
    )
    parser.add_argument(
        "--discovery-max-hosts",
        type=int,
        help="Maximo de hosts a sondear desde los rangos configurados.",
    )
    parser.add_argument(
        "--auto-promote-discovered-nodes",
        dest="auto_promote_discovered_nodes",
        action="store_true",
        default=None,
        help=(
            "Promueve nodos Ollama descubiertos a candidatos de routing usando "
            "modelos y roles inferidos. Requiere discovery habilitado."
        ),
    )
    parser.add_argument(
        "--auto-promote-roles",
        help=(
            "Roles que pueden asignarse automaticamente a nodos descubiertos. "
            "Ejemplo: planner,worker,reviewer"
        ),
    )
    parser.add_argument(
        "--auto-promote-priority",
        type=int,
        help="Prioridad base para nodos auto-promovidos. Menor valor gana.",
    )
    parser.add_argument(
        "--auto-promote-max-nodes",
        type=int,
        help="Maximo de nodos virtuales creados por auto-promocion.",
    )

    return parser
