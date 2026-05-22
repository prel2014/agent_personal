from __future__ import annotations

from ...models import ToolDefinition, ToolParameter
from ...categories import EXECUTE, READ, WRITE
from ..code_functions import search_code, find_files, read_lines, replace_in_file, replace_lines, list_tree, get_python_symbols, find_definition, find_references, extract_imports

def register_read_write(registry):
    registry.register(
        ToolDefinition(
            name="search_code",
            description="Busca texto o expresiones regulares dentro del codigo del proyecto.",
            category=READ,
            parameters=[
                ToolParameter(name="query", type="string", description="Texto o patron a buscar"),
                ToolParameter(
                    name="path",
                    type="string",
                    description="Ruta base donde buscar",
                    required=False,
                ),
                ToolParameter(
                    name="regex",
                    type="boolean",
                    description="Si el query debe interpretarse como regex",
                    required=False,
                ),
                ToolParameter(
                    name="case_sensitive",
                    type="boolean",
                    description="Si la busqueda debe distinguir mayusculas",
                    required=False,
                ),
                ToolParameter(
                    name="file_glob",
                    type="string",
                    description="Patron de archivos, por ejemplo *.py",
                    required=False,
                ),
                ToolParameter(
                    name="max_results",
                    type="integer",
                    description="Maximo de coincidencias a devolver",
                    required=False,
                ),
            ],
        ),
        search_code,
    )

    registry.register(
        ToolDefinition(
            name="find_files",
            description="Encuentra archivos por patron dentro del proyecto.",
            category=READ,
            parameters=[
                ToolParameter(name="glob", type="string", description="Patron como *.py o tests/*.py"),
                ToolParameter(
                    name="path",
                    type="string",
                    description="Ruta base donde buscar",
                    required=False,
                ),
                ToolParameter(
                    name="max_results",
                    type="integer",
                    description="Maximo de resultados a devolver",
                    required=False,
                ),
            ],
        ),
        find_files,
    )

    registry.register(
        ToolDefinition(
            name="read_lines",
            description="Lee un rango de lineas de un archivo.",
            category=READ,
            parameters=[
                ToolParameter(name="path", type="string", description="Ruta del archivo"),
                ToolParameter(name="start", type="integer", description="Linea inicial, desde 1"),
                ToolParameter(name="end", type="integer", description="Linea final, inclusiva"),
            ],
        ),
        read_lines,
    )

    registry.register(
        ToolDefinition(
            name="replace_in_file",
            description="Reemplaza texto dentro de un archivo sin reescribirlo manualmente completo.",
            category=WRITE,
            parameters=[
                ToolParameter(name="path", type="string", description="Ruta del archivo"),
                ToolParameter(name="old", type="string", description="Texto a reemplazar"),
                ToolParameter(name="new", type="string", description="Texto nuevo"),
                ToolParameter(
                    name="count",
                    type="integer",
                    description="Numero maximo de reemplazos, 0 significa todos",
                    required=False,
                ),
            ],
        ),
        replace_in_file,
    )

    registry.register(
        ToolDefinition(
            name="replace_lines",
            description="Reemplaza un rango de lineas por contenido nuevo.",
            category=WRITE,
            parameters=[
                ToolParameter(name="path", type="string", description="Ruta del archivo"),
                ToolParameter(name="start", type="integer", description="Linea inicial, desde 1"),
                ToolParameter(name="end", type="integer", description="Linea final, inclusiva"),
                ToolParameter(name="content", type="string", description="Contenido que reemplazara el rango"),
            ],
        ),
        replace_lines,
    )

    registry.register(
        ToolDefinition(
            name="list_tree",
            description="Muestra un arbol real de archivos y carpetas.",
            category=READ,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Ruta base del arbol",
                    required=False,
                ),
                ToolParameter(
                    name="depth",
                    type="integer",
                    description="Profundidad maxima del arbol",
                    required=False,
                ),
            ],
        ),
        list_tree,
    )

    registry.register(
        ToolDefinition(
            name="get_python_symbols",
            description="Lista clases, funciones y metodos de un archivo Python.",
            category=READ,
            parameters=[
                ToolParameter(name="path", type="string", description="Ruta del archivo Python"),
            ],
        ),
        get_python_symbols,
    )

    registry.register(
        ToolDefinition(
            name="find_definition",
            description="Encuentra definiciones de simbolos Python en el proyecto.",
            category=READ,
            parameters=[
                ToolParameter(name="symbol", type="string", description="Nombre del simbolo a localizar"),
                ToolParameter(
                    name="path",
                    type="string",
                    description="Ruta base donde buscar",
                    required=False,
                ),
                ToolParameter(
                    name="max_results",
                    type="integer",
                    description="Maximo de coincidencias",
                    required=False,
                ),
            ],
        ),
        find_definition,
    )

    registry.register(
        ToolDefinition(
            name="find_references",
            description="Busca referencias de un simbolo Python en el proyecto.",
            category=READ,
            parameters=[
                ToolParameter(name="symbol", type="string", description="Nombre del simbolo a buscar"),
                ToolParameter(
                    name="path",
                    type="string",
                    description="Ruta base donde buscar",
                    required=False,
                ),
                ToolParameter(
                    name="max_results",
                    type="integer",
                    description="Maximo de coincidencias",
                    required=False,
                ),
            ],
        ),
        find_references,
    )

    registry.register(
        ToolDefinition(
            name="extract_imports",
            description="Extrae imports de un archivo Python.",
            category=READ,
            parameters=[
                ToolParameter(name="path", type="string", description="Ruta del archivo Python"),
            ],
        ),
        extract_imports,
    )
