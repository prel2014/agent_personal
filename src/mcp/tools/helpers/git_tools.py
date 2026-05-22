from .git_functions import *
from ..models import ToolDefinition, ToolParameter
from ..registry import ToolRegistry
from ..categories import READ


registry = ToolRegistry()


registry.register(
    ToolDefinition(
        name="git_status",
        description=(
            "Inspecciona el estado actual de un repositorio Git sin modificarlo. "
            "Devuelve rama, tracking y cambios staged, unstaged o untracked."
        ),
        category=READ,
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="Ruta del repositorio o de un archivo/carpeta dentro del repositorio.",
                required=False,
            ),
            ToolParameter(
                name="include_untracked",
                type="boolean",
                description="Incluye archivos no trackeados en el resultado.",
                required=False,
            ),
        ],
    ),
    git_status,
)


registry.register(
    ToolDefinition(
        name="git_diff",
        description=(
            "Obtiene un diff Git de solo lectura. Puede comparar working tree, index o dos referencias."
        ),
        category=READ,
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="Ruta del repositorio o de un archivo/carpeta dentro del repositorio.",
                required=False,
            ),
            ToolParameter(
                name="staged",
                type="boolean",
                description="Si es true, muestra el diff staged (index) contra HEAD.",
                required=False,
            ),
            ToolParameter(
                name="base_ref",
                type="string",
                description="Referencia base, por ejemplo HEAD~1 o main.",
                required=False,
            ),
            ToolParameter(
                name="target_ref",
                type="string",
                description="Referencia objetivo cuando se comparan dos refs.",
                required=False,
            ),
            ToolParameter(
                name="context_lines",
                type="integer",
                description="Cantidad de lineas de contexto en el patch.",
                required=False,
            ),
            ToolParameter(
                name="max_bytes",
                type="integer",
                description="Maximo de bytes devueltos del diff antes de truncar.",
                required=False,
            ),
        ],
    ),
    git_diff,
)


registry.register(
    ToolDefinition(
        name="git_log",
        description="Lista commits recientes de un repositorio Git o de una ruta concreta dentro de el.",
        category=READ,
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="Ruta del repositorio o de un archivo/carpeta dentro del repositorio.",
                required=False,
            ),
            ToolParameter(
                name="max_count",
                type="integer",
                description="Cantidad maxima de commits a devolver.",
                required=False,
            ),
            ToolParameter(
                name="ref",
                type="string",
                description="Referencia opcional desde la cual listar el historial.",
                required=False,
            ),
        ],
    ),
    git_log,
)


registry.register(
    ToolDefinition(
        name="git_show",
        description="Muestra el detalle de un commit u objeto Git sin modificar el repositorio.",
        category=READ,
        parameters=[
            ToolParameter(
                name="revision",
                type="string",
                description="Revision u objeto Git, por ejemplo HEAD o a1b2c3d.",
            ),
            ToolParameter(
                name="path",
                type="string",
                description="Ruta del repositorio o de un archivo/carpeta para acotar la salida.",
                required=False,
            ),
            ToolParameter(
                name="max_bytes",
                type="integer",
                description="Maximo de bytes devueltos antes de truncar.",
                required=False,
            ),
        ],
    ),
    git_show,
)


registry.register(
    ToolDefinition(
        name="git_branches",
        description="Lista ramas locales o remotas de un repositorio Git.",
        category=READ,
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="Ruta del repositorio o de un archivo/carpeta dentro del repositorio.",
                required=False,
            ),
            ToolParameter(
                name="all_branches",
                type="boolean",
                description="Incluye ramas remotas ademas de las locales.",
                required=False,
            ),
            ToolParameter(
                name="contains",
                type="string",
                description="Filtra ramas que contienen una revision dada.",
                required=False,
            ),
        ],
    ),
    git_branches,
)


registry.register(
    ToolDefinition(
        name="git_blame",
        description="Atribuye lineas de un archivo a commits y autores usando Git blame.",
        category=READ,
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="Ruta del archivo dentro del repositorio.",
            ),
            ToolParameter(
                name="start_line",
                type="integer",
                description="Linea inicial opcional, desde 1.",
                required=False,
            ),
            ToolParameter(
                name="end_line",
                type="integer",
                description="Linea final opcional, inclusiva.",
                required=False,
            ),
            ToolParameter(
                name="revision",
                type="string",
                description="Revision sobre la cual correr blame. Por defecto HEAD.",
                required=False,
            ),
        ],
    ),
    git_blame,
)


registry.register(
    ToolDefinition(
        name="git_ls_files",
        description="Lista los archivos trackeados por Git, opcionalmente filtrados por ruta o patron.",
        category=READ,
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="Ruta del repositorio o de un archivo/carpeta dentro del repositorio.",
                required=False,
            ),
            ToolParameter(
                name="pattern",
                type="string",
                description="Pathspec adicional, por ejemplo src/*.py.",
                required=False,
            ),
        ],
    ),
    git_ls_files,
)
