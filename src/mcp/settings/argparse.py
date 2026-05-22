import argparse


def add_config_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument(
        "--base-dir",
        help="Carpeta base permitida para operaciones de archivos. Tambien puede venir de MCP_BASE_DIR.",
    )
    parser.add_argument(
        "--server-name",
        help="Nombre del servidor. Tambien puede venir de MCP_SERVER_NAME.",
    )
    parser.add_argument(
        "--server-version",
        help="Version del servidor. Tambien puede venir de MCP_SERVER_VERSION.",
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "json-stdio"),
        help="Transporte logico del servidor.",
    )
    parser.add_argument(
        "--encoding",
        help="Codificacion por defecto para archivos de texto.",
    )
    parser.add_argument(
        "--read-only",
        action="store_true",
        default=None,
        help="Deshabilita escritura, ejecucion y borrado; deja solo lectura.",
    )
    parser.add_argument(
        "--deny-read",
        dest="allow_read",
        action="store_false",
        default=None,
        help="Deshabilita herramientas de lectura e inspeccion.",
    )
    parser.add_argument(
        "--deny-write",
        dest="allow_write",
        action="store_false",
        default=None,
        help="Deshabilita herramientas de escritura y modificacion.",
    )
    execute_group = parser.add_mutually_exclusive_group()
    execute_group.add_argument(
        "--allow-execute",
        action="store_true",
        default=None,
        help="Habilita herramientas que ejecutan procesos locales. Es el default.",
    )
    execute_group.add_argument(
        "--deny-execute",
        dest="allow_execute",
        action="store_false",
        default=None,
        help="Deshabilita herramientas que ejecutan procesos locales.",
    )
    parser.add_argument(
        "--allow-delete",
        action="store_true",
        default=None,
        help="Habilita tools de borrado como deletefile y deletedir.",
    )
    parser.add_argument(
        "--allow-hardware",
        action="store_true",
        default=None,
        help="Habilita tools que acceden a puertos seriales o hardware local.",
    )
    parser.add_argument(
        "--allow-media-input",
        action="store_true",
        default=None,
        help="Habilita tools que leen imagenes, camaras web o fuentes RTSP.",
    )
    parser.add_argument(
        "--vision-model",
        help=(
            "Modelo Ollama usado por image_describe. "
            "Si se omite o vale auto, se detecta desde /api/tags. "
            "Tambien puede venir de MCP_VISION_MODEL u OLLAMA_VISION_MODEL."
        ),
    )
    parser.add_argument(
        "--vision-ollama-base-url",
        help=(
            "URL base de Ollama para image_describe. "
            "Tambien puede venir de MCP_VISION_OLLAMA_BASE_URL u OLLAMA_BASE_URL."
        ),
    )
    parser.add_argument(
        "--allow-web",
        action="store_true",
        default=None,
        help="Habilita tools web aisladas como web_search y web_fetch.",
    )
    parser.add_argument(
        "--allow-sandbox-execute",
        action="store_true",
        default=None,
        help="Habilita ejecucion arbitraria dentro del sandbox.",
    )
    parser.add_argument(
        "--sandbox-backend",
        choices=("docker", "local"),
        help="Backend de sandbox. docker es el backend seguro por defecto; local es solo para pruebas.",
    )
    parser.add_argument(
        "--sandbox-image",
        help="Imagen Docker usada para worker/proxy del sandbox.",
    )
    parser.add_argument(
        "--sandbox-timeout",
        type=float,
        help="Timeout maximo por ejecucion de sandbox en segundos.",
    )
    parser.add_argument(
        "--web-allowed-domains",
        help="Dominios web permitidos separados por comas. Vacio permite dominios publicos no bloqueados.",
    )
    parser.add_argument(
        "--web-denied-domains",
        help="Dominios web bloqueados separados por comas.",
    )
    parser.add_argument(
        "--allow-private-web",
        dest="web_block_private_networks",
        action="store_false",
        default=None,
        help="Permite destinos web en redes privadas/locales. No recomendado.",
    )
    parser.add_argument(
        "--web-max-response-bytes",
        type=int,
        help="Maximo de bytes a leer por respuesta web.",
    )
    parser.add_argument(
        "--web-search-provider",
        choices=("searxng",),
        help="Proveedor de busqueda web aislada.",
    )
    parser.add_argument(
        "--web-search-base-url",
        help="URL base del proveedor SearxNG. Ejemplo: http://searxng:8080",
    )
    parser.add_argument(
        "--allowed-tools",
        help="Lista separada por comas con tools explicitamente permitidas.",
    )
    parser.add_argument(
        "--blocked-tools",
        help="Lista separada por comas con tools explicitamente bloqueadas.",
    )
    parser.add_argument(
        "--protected-paths",
        help=(
            "Lista separada por comas con rutas o patrones protegidos "
            "contra escritura/borrado."
        ),
    )
    parser.add_argument(
        "--protected-read-paths",
        help=(
            "Lista separada por comas con rutas o patrones protegidos "
            "contra lectura e inspeccion directa."
        ),
    )
    parser.add_argument(
        "--tool-confirmation-mode",
        choices=("off", "sensitive"),
        help=(
            "Politica de confirmacion de tools. "
            "sensitive exige aprobacion previa para tools mutantes o de alto impacto."
        ),
    )
    parser.add_argument(
        "--approved-sensitive-tools",
        help=(
            "Lista separada por comas con tools sensibles aprobadas para ejecucion "
            "cuando --tool-confirmation-mode=sensitive."
        ),
    )
    parser.add_argument(
        "--kv-cache-db-path",
        help="Ruta SQLite para el KV cache local. Tambien puede venir de MCP_CLIENT_KV_CACHE_DB_PATH.",
    )
    parser.add_argument(
        "--no-kv-cache",
        dest="kv_cache_enabled",
        action="store_false",
        default=None,
        help="Deshabilita tools y persistencia KV local.",
    )

    return parser
