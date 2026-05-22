from __future__ import annotations

from ...models import ToolDefinition, ToolParameter
from ...categories import EXECUTE, READ, WRITE
from ..code_functions import (
    format_python,
    lint_python,
    python_compile_check,
    python_interpreter,
    run_module,
    run_python_file,
    run_tests,
    syntax_check_python,
)

def register_python_tools(registry):
    registry.register(
        ToolDefinition(
            name="syntax_check_python",
            description="Valida sintaxis de un archivo Python.",
            category=READ,
            parameters=[
                ToolParameter(name="path", type="string", description="Ruta del archivo Python"),
            ],
        ),
        syntax_check_python,
    )

    registry.register(
        ToolDefinition(
            name="python_compile_check",
            description="Compila un archivo Python con py_compile para detectar errores.",
            category=READ,
            parameters=[
                ToolParameter(name="path", type="string", description="Ruta del archivo Python"),
            ],
        ),
        python_compile_check,
    )

    registry.register(
        ToolDefinition(
            name="run_python_file",
            description="Ejecuta un archivo Python concreto.",
            category=EXECUTE,
            parameters=[
                ToolParameter(name="path", type="string", description="Ruta del archivo Python"),
                ToolParameter(
                    name="args",
                    type="array",
                    description="Lista de argumentos para el script",
                    required=False,
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    description="Timeout en segundos",
                    required=False,
                ),
            ],
        ),
        run_python_file,
    )

    registry.register(
        ToolDefinition(
            name="python",
            description=(
                "Alias de run_python_file. Ejecuta un archivo Python concreto; "
                "requiere permiso de ejecucion."
            ),
            category=EXECUTE,
            parameters=[
                ToolParameter(name="path", type="string", description="Ruta del archivo Python"),
                ToolParameter(
                    name="args",
                    type="array",
                    description="Lista de argumentos para el script",
                    required=False,
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    description="Timeout en segundos",
                    required=False,
                ),
            ],
        ),
        run_python_file,
    )

    registry.register(
        ToolDefinition(
            name="python_interpreter",
            description=(
                "Ejecuta codigo Python inline con python -c en la carpeta base; "
                "requiere permiso de ejecucion."
            ),
            category=EXECUTE,
            parameters=[
                ToolParameter(name="code", type="string", description="Codigo Python a ejecutar"),
                ToolParameter(
                    name="path",
                    type="string",
                    description="Carpeta de trabajo desde donde ejecutar el codigo",
                    required=False,
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    description="Timeout en segundos",
                    required=False,
                ),
            ],
        ),
        python_interpreter,
    )

    registry.register(
        ToolDefinition(
            name="run_module",
            description="Ejecuta un modulo Python con python -m.",
            category=EXECUTE,
            parameters=[
                ToolParameter(name="module", type="string", description="Nombre del modulo"),
                ToolParameter(
                    name="path",
                    type="string",
                    description="Ruta de trabajo desde donde ejecutar",
                    required=False,
                ),
                ToolParameter(
                    name="args",
                    type="array",
                    description="Lista de argumentos para el modulo",
                    required=False,
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    description="Timeout en segundos",
                    required=False,
                ),
            ],
        ),
        run_module,
    )

    registry.register(
        ToolDefinition(
            name="run_tests",
            description="Ejecuta pruebas con pytest.",
            category=EXECUTE,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Ruta de archivo o carpeta de tests",
                    required=False,
                ),
                ToolParameter(
                    name="pattern",
                    type="string",
                    description="Patron opcional para pytest -k",
                    required=False,
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    description="Timeout en segundos",
                    required=False,
                ),
            ],
        ),
        run_tests,
    )

    registry.register(
        ToolDefinition(
            name="lint_python",
            description="Ejecuta lint con ruff o flake8.",
            category=EXECUTE,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Ruta de archivo o carpeta a revisar",
                    required=False,
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    description="Timeout en segundos",
                    required=False,
                ),
            ],
        ),
        lint_python,
    )

    registry.register(
        ToolDefinition(
            name="format_python",
            description="Formatea codigo Python con ruff format o black.",
            category=EXECUTE,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Ruta de archivo o carpeta a formatear",
                    required=False,
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    description="Timeout en segundos",
                    required=False,
                ),
            ],
        ),
        format_python,
    )
