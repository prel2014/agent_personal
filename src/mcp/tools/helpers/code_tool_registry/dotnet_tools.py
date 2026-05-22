from __future__ import annotations

from ...models import ToolDefinition, ToolParameter
from ...categories import EXECUTE, READ, WRITE
from ..code_functions import dotnet_restore, dotnet_build, dotnet_test, dotnet_run

def register_dotnet_tools(registry):
    registry.register(
        ToolDefinition(
            name="dotnet_restore",
            description="Ejecuta dotnet restore sobre un proyecto, solucion o carpeta.",
            category=EXECUTE,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Ruta de un .csproj, .fsproj, .vbproj, .sln o carpeta",
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
        dotnet_restore,
    )

    registry.register(
        ToolDefinition(
            name="dotnet_build",
            description="Ejecuta dotnet build sobre un proyecto, solucion o carpeta.",
            category=EXECUTE,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Ruta de un .csproj, .fsproj, .vbproj, .sln o carpeta",
                    required=False,
                ),
                ToolParameter(
                    name="configuration",
                    type="string",
                    description="Configuracion, por ejemplo Debug o Release",
                    required=False,
                ),
                ToolParameter(
                    name="framework",
                    type="string",
                    description="Framework objetivo opcional",
                    required=False,
                ),
                ToolParameter(
                    name="no_restore",
                    type="boolean",
                    description="Evita dotnet restore antes del build",
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
        dotnet_build,
    )

    registry.register(
        ToolDefinition(
            name="dotnet_test",
            description="Ejecuta dotnet test sobre un proyecto, solucion o carpeta.",
            category=EXECUTE,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Ruta de un .csproj, .fsproj, .vbproj, .sln o carpeta",
                    required=False,
                ),
                ToolParameter(
                    name="filter",
                    type="string",
                    description="Filtro opcional para pruebas",
                    required=False,
                ),
                ToolParameter(
                    name="configuration",
                    type="string",
                    description="Configuracion, por ejemplo Debug o Release",
                    required=False,
                ),
                ToolParameter(
                    name="no_build",
                    type="boolean",
                    description="Evita compilar antes de probar",
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
        dotnet_test,
    )

    registry.register(
        ToolDefinition(
            name="dotnet_run",
            description="Ejecuta dotnet run sobre un proyecto o carpeta.",
            category=EXECUTE,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Ruta de un .csproj o carpeta de proyecto",
                    required=False,
                ),
                ToolParameter(
                    name="args",
                    type="array",
                    description="Argumentos de la aplicacion",
                    required=False,
                ),
                ToolParameter(
                    name="framework",
                    type="string",
                    description="Framework objetivo opcional",
                    required=False,
                ),
                ToolParameter(
                    name="configuration",
                    type="string",
                    description="Configuracion, por ejemplo Debug o Release",
                    required=False,
                ),
                ToolParameter(
                    name="no_build",
                    type="boolean",
                    description="Evita compilar antes de ejecutar",
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
        dotnet_run,
    )
