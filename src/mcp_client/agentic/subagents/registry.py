from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ..frontmatter import parse_frontmatter, parse_tools, split_frontmatter
from ..roles import PLANNER_DIRECTIVE, REVIEWER_DIRECTIVE, WORKER_DIRECTIVE
from .models import SubagentSpec, ToolAccess

# Aliases privados para compatibilidad con código existente que llama a las funciones internas
_split_frontmatter = split_frontmatter
_parse_frontmatter = parse_frontmatter
_parse_tools = parse_tools


READ_TOOLS = (
    "pwd",
    "listdir",
    "list_tree",
    "find_files",
    "fileinfo",
    "readfile",
    "read_lines",
    "search_code",
)
CODE_REVIEW_TOOLS = (
    *READ_TOOLS,
    "get_python_symbols",
    "find_definition",
    "find_references",
    "extract_imports",
    "git_status",
    "git_diff",
)
TEST_TOOLS = (
    *READ_TOOLS,
    "run_tests",
    "syntax_check_python",
    "python_compile_check",
    "run_python_file",
    "python_interpreter",
)


def built_in_subagents() -> dict[str, SubagentSpec]:
    specs = (
        SubagentSpec(
            name="planner",
            description="Descompone solicitudes en un plan breve sin usar tools.",
            directive=PLANNER_DIRECTIVE,
            tool_access="none",
            tools=(),
            built_in=True,
        ),
        SubagentSpec(
            name="worker",
            description="Ejecuta cambios e inspecciones con las tools necesarias.",
            directive=WORKER_DIRECTIVE,
            tool_access="full",
            tools=None,
            built_in=True,
        ),
        SubagentSpec(
            name="reviewer",
            description="Verifica con lectura si el trabajo cumple la solicitud.",
            directive=REVIEWER_DIRECTIVE,
            tool_access="read_only",
            tools=READ_TOOLS,
            built_in=True,
        ),
        SubagentSpec(
            name="file-inspector",
            description="Lee archivos, rangos y busquedas puntuales sin modificar nada.",
            directive=(
                "Eres file-inspector. Inspecciona solo lo necesario con tools de lectura. "
                "Devuelve rutas, lineas relevantes y una conclusion breve. No modifiques archivos."
            ),
            tool_access="read_only",
            tools=READ_TOOLS,
            built_in=True,
        ),
        SubagentSpec(
            name="code-reviewer",
            description="Revisa cambios de codigo, riesgos, regresiones y tests faltantes.",
            directive=(
                "Eres code-reviewer. Prioriza bugs, regresiones, permisos, contratos rotos "
                "y pruebas faltantes. Presenta hallazgos ordenados por severidad con rutas."
            ),
            tool_access="read_only",
            tools=CODE_REVIEW_TOOLS,
            built_in=True,
        ),
        SubagentSpec(
            name="test-runner",
            description="Ejecuta o valida pruebas y comandos de verificacion permitidos.",
            directive=(
                "Eres test-runner. Ejecuta la verificacion minima suficiente, reporta comando, "
                "resultado, fallos concretos y evidencia. No hagas cambios de codigo."
            ),
            tool_access="full",
            tools=TEST_TOOLS,
            built_in=True,
        ),
    )
    return {spec.name: spec for spec in specs}


class SubagentRegistry:
    def __init__(self, specs: Iterable[SubagentSpec] = ()) -> None:
        self._specs = built_in_subagents()
        for spec in specs:
            self._specs[spec.name] = spec

    @classmethod
    def from_paths(cls, paths: Iterable[Path]) -> "SubagentRegistry":
        specs: list[SubagentSpec] = []
        for directory in paths:
            if not directory.exists() or not directory.is_dir():
                continue
            for path in sorted(directory.glob("*.md")):
                specs.append(load_subagent_file(path))
        return cls(specs)

    def get(self, name: str) -> SubagentSpec | None:
        return self._specs.get(name)

    def catalog(self) -> list[dict[str, object]]:
        return [self._specs[name].catalog_entry() for name in sorted(self._specs)]


def load_subagent_file(path: Path) -> SubagentSpec:
    text = path.read_text(encoding="utf-8")
    frontmatter, body = split_frontmatter(text)
    data = parse_frontmatter(frontmatter)
    name = data.get("name") or path.stem
    description = data.get("description")
    if not description:
        raise ValueError(f"Subagente sin description: {path}")

    tool_access = data.get("tool_access", "full")
    if tool_access not in {"none", "read_only", "full"}:
        raise ValueError(f"tool_access invalido en {path}: {tool_access}")

    raw_tools = data.get("tools")
    tools = parse_tools(raw_tools)
    directive = body.strip()
    if not directive:
        raise ValueError(f"Subagente sin cuerpo/directive: {path}")

    return SubagentSpec(
        name=name,
        description=description,
        directive=directive,
        tool_access=tool_access,  # type: ignore[arg-type]
        tools=tools,
        built_in=False,
        source=str(path),
    )
