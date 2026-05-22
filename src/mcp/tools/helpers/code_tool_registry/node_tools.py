from __future__ import annotations

from ...models import ToolDefinition, ToolParameter
from ...categories import EXECUTE, READ, WRITE
from ..code_functions import node_syntax_check, node_run_script, node_test, node_lint, node_format, ts_typecheck

def register_node_tools(registry):
    registry.register(
        ToolDefinition(
            name="node_syntax_check",
            description="Valida sintaxis de un archivo JavaScript con Node. Para TypeScript delega a ts_typecheck.",
            category=EXECUTE,
            parameters=[
                ToolParameter(name="path", type="string", description="Ruta del archivo JS o TS"),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    description="Timeout en segundos",
                    required=False,
                ),
            ],
        ),
        node_syntax_check,
    )

    registry.register(
        ToolDefinition(
            name="node_run_script",
            description="Ejecuta un script de package.json con npm, pnpm, yarn o bun.",
            category=EXECUTE,
            parameters=[
                ToolParameter(name="script", type="string", description="Nombre del script, por ejemplo build o dev"),
                ToolParameter(
                    name="path",
                    type="string",
                    description="Ruta dentro del proyecto Node",
                    required=False,
                ),
                ToolParameter(
                    name="args",
                    type="array",
                    description="Argumentos extra para el script",
                    required=False,
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    description="Timeout en segundos",
                    required=False,
                ),
                ToolParameter(
                    name="package_manager",
                    type="string",
                    description="Override opcional: npm, pnpm, yarn o bun",
                    required=False,
                ),
            ],
        ),
        node_run_script,
    )

    registry.register(
        ToolDefinition(
            name="node_test",
            description="Ejecuta el script test de un proyecto Node.",
            category=EXECUTE,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Ruta dentro del proyecto Node",
                    required=False,
                ),
                ToolParameter(
                    name="args",
                    type="array",
                    description="Argumentos extra para el script test",
                    required=False,
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    description="Timeout en segundos",
                    required=False,
                ),
                ToolParameter(
                    name="package_manager",
                    type="string",
                    description="Override opcional: npm, pnpm, yarn o bun",
                    required=False,
                ),
            ],
        ),
        node_test,
    )

    registry.register(
        ToolDefinition(
            name="node_lint",
            description="Ejecuta el script lint de un proyecto Node.",
            category=EXECUTE,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Ruta dentro del proyecto Node",
                    required=False,
                ),
                ToolParameter(
                    name="args",
                    type="array",
                    description="Argumentos extra para el script lint",
                    required=False,
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    description="Timeout en segundos",
                    required=False,
                ),
                ToolParameter(
                    name="package_manager",
                    type="string",
                    description="Override opcional: npm, pnpm, yarn o bun",
                    required=False,
                ),
            ],
        ),
        node_lint,
    )

    registry.register(
        ToolDefinition(
            name="node_format",
            description="Ejecuta el script format de un proyecto Node.",
            category=EXECUTE,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Ruta dentro del proyecto Node",
                    required=False,
                ),
                ToolParameter(
                    name="args",
                    type="array",
                    description="Argumentos extra para el script format",
                    required=False,
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    description="Timeout en segundos",
                    required=False,
                ),
                ToolParameter(
                    name="package_manager",
                    type="string",
                    description="Override opcional: npm, pnpm, yarn o bun",
                    required=False,
                ),
            ],
        ),
        node_format,
    )

    registry.register(
        ToolDefinition(
            name="ts_typecheck",
            description="Ejecuta type checking de TypeScript con tsc --noEmit.",
            category=EXECUTE,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Ruta de un archivo TS, carpeta o tsconfig.json",
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
        ts_typecheck,
    )
