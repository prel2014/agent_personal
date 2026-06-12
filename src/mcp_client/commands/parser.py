from __future__ import annotations

import argparse

from ..config import add_client_arguments


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="CLI local que expone tools al servidor de razonamiento."
    )
    add_client_arguments(parser)

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("info", help="Muestra la configuracion del cliente.")
    subparsers.add_parser("health", help="Consulta el health del servidor.")
    subparsers.add_parser("list-nodes", help="Lista los nodos Ollama visibles por el orquestador.")
    subparsers.add_parser("list-tools", help="Lista las tools locales.")
    subparsers.add_parser("list-prompts", help="Lista los prompts locales.")
    subparsers.add_parser("doctor", help="Valida entorno, permisos, servidor y persistencia local.")
    subparsers.add_parser("setup", help="Prepara directorios y SQLite locales sin activar permisos peligrosos.")

    repl_parser = subparsers.add_parser("repl", help="Abre una sesion interactiva.")
    repl_group = repl_parser.add_mutually_exclusive_group()
    repl_group.add_argument("--session", help="ID de sesion persistente a reanudar.")
    repl_group.add_argument(
        "--continue",
        dest="continue_session",
        action="store_true",
        help="Reanuda la sesion persistente mas reciente.",
    )

    sessions_parser = subparsers.add_parser("sessions", help="Gestiona sesiones persistentes.")
    sessions_subparsers = sessions_parser.add_subparsers(
        dest="sessions_command",
        required=True,
    )
    sessions_list = sessions_subparsers.add_parser("list", help="Lista sesiones recientes.")
    sessions_list.add_argument("--limit", type=int, default=20, help="Cantidad maxima de sesiones.")
    sessions_show = sessions_subparsers.add_parser("show", help="Muestra una sesion y sus mensajes.")
    sessions_show.add_argument("session_id", help="ID de sesion.")
    sessions_rename = sessions_subparsers.add_parser("rename", help="Renombra una sesion.")
    sessions_rename.add_argument("session_id", help="ID de sesion.")
    sessions_rename.add_argument("title", nargs="+", help="Nuevo titulo.")
    sessions_close = sessions_subparsers.add_parser("close", help="Marca una sesion como cerrada.")
    sessions_close.add_argument("session_id", help="ID de sesion.")

    cache_parser = subparsers.add_parser("cache", help="Gestiona el KV cache local.")
    cache_subparsers = cache_parser.add_subparsers(
        dest="cache_command",
        required=True,
    )
    cache_get = cache_subparsers.add_parser("get", help="Lee una entrada del KV cache.")
    cache_get.add_argument("namespace", help="Namespace del cache.")
    cache_get.add_argument("key", help="Clave a leer.")
    cache_set = cache_subparsers.add_parser("set", help="Escribe una entrada del KV cache.")
    cache_set.add_argument("namespace", help="Namespace del cache.")
    cache_set.add_argument("key", help="Clave a escribir.")
    cache_set.add_argument("value", help="Valor. Si es JSON valido, se guarda como JSON.")
    cache_set.add_argument("--ttl-seconds", type=int, help="TTL opcional en segundos.")
    cache_delete = cache_subparsers.add_parser("delete", help="Borra una entrada del KV cache.")
    cache_delete.add_argument("namespace", help="Namespace del cache.")
    cache_delete.add_argument("key", help="Clave a borrar.")
    cache_list = cache_subparsers.add_parser("list", help="Lista entradas del KV cache.")
    cache_list.add_argument("--namespace", help="Namespace opcional.")
    cache_list.add_argument("--prefix", help="Prefijo opcional de key.")
    cache_list.add_argument("--limit", type=int, default=100, help="Cantidad maxima de entradas.")
    cache_clear = cache_subparsers.add_parser("clear", help="Borra entradas del KV cache.")
    cache_clear.add_argument("--namespace", help="Namespace opcional.")
    cache_clear.add_argument(
        "--expired-only",
        action="store_true",
        help="Borra solo entradas expiradas.",
    )

    export_parser = subparsers.add_parser(
        "export-dataset",
        help="Exporta ejemplos entrenables desde la base SQLite de trazas.",
    )
    export_parser.add_argument(
        "--db-path",
        help="Ruta SQLite de trazas. Si se omite usa --trace-db-path o el path por defecto.",
    )
    export_parser.add_argument(
        "--output",
        required=True,
        help="Archivo JSONL de salida.",
    )
    export_parser.add_argument(
        "--example-type",
        default="sft_conversation",
        help="Tipo de ejemplo a exportar. Ejemplo: sft_conversation o team_final.",
    )
    export_parser.add_argument(
        "--limit",
        type=int,
        help="Maximo de ejemplos a exportar.",
    )

    ask_parser = subparsers.add_parser("ask", help="Envia un prompt al servidor.")
    ask_group = ask_parser.add_mutually_exclusive_group()
    ask_group.add_argument("--session", help="ID de sesion persistente a continuar.")
    ask_group.add_argument(
        "--new-session",
        action="store_true",
        help="Crea una sesion persistente nueva para este prompt.",
    )
    ask_parser.add_argument("prompt", nargs="+", help="Prompt del usuario.")

    skills_parser = subparsers.add_parser("skills", help="Gestiona skills del agente.")
    skills_subparsers = skills_parser.add_subparsers(dest="skills_command", required=True)
    skills_subparsers.add_parser("list", help="Lista skills disponibles.")
    skills_show_p = skills_subparsers.add_parser("show", help="Muestra un skill.")
    skills_show_p.add_argument("name", help="Nombre del skill.")

    memory_parser = subparsers.add_parser("memory", help="Gestiona la memoria persistente del agente.")
    memory_subparsers = memory_parser.add_subparsers(dest="memory_command", required=True)
    memory_subparsers.add_parser("list", help="Lista todas las memorias (proyecto y usuario).")
    mem_add = memory_subparsers.add_parser("add", help="Guarda una memoria de proyecto.")
    mem_add.add_argument("key", help="Clave de la memoria.")
    mem_add.add_argument("value", nargs="+", help="Valor de la memoria.")
    mem_forget = memory_subparsers.add_parser("forget", help="Elimina una memoria de proyecto.")
    mem_forget.add_argument("key", help="Clave de la memoria.")
    mem_search = memory_subparsers.add_parser("search", help="Busca memorias por query.")
    mem_search.add_argument("query", nargs="+", help="Query de busqueda.")
    memory_subparsers.add_parser("clear", help="Borra todas las memorias de proyecto.")

    return parser
