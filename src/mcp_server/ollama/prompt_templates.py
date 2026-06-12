from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


class PromptRenderError(ValueError):
    """Raised when a prompt template cannot be rendered safely."""


@dataclass(frozen=True)
class PromptTemplateEngine:
    root: Path
    max_include_depth: int = 8

    def render(self, text: str, variables: Mapping[str, str]) -> str:
        return self._render_text(text, variables, source=None, seen=(), depth=0).strip()

    def render_file(self, path: Path, variables: Mapping[str, str]) -> str:
        resolved = self._resolve_path(path)
        return self._render_text(
            resolved.read_text(encoding="utf-8"),
            variables,
            source=resolved,
            seen=(resolved,),
            depth=0,
        ).strip()

    def _render_text(
        self,
        text: str,
        variables: Mapping[str, str],
        *,
        source: Path | None,
        seen: tuple[Path, ...],
        depth: int,
    ) -> str:
        _, body = _split_frontmatter(text)

        def replace(match: re.Match[str]) -> str:
            expression = match.group("expression").strip()
            if expression.startswith("include:"):
                include_path = expression[len("include:") :].strip()
                return self._render_include(
                    include_path,
                    variables,
                    source=source,
                    seen=seen,
                    depth=depth,
                )
            if expression not in variables:
                raise PromptRenderError(f"Variable de prompt desconocida: {expression}")
            return variables[expression]

        return _EXPRESSION_RE.sub(replace, body)

    def _render_include(
        self,
        include_path: str,
        variables: Mapping[str, str],
        *,
        source: Path | None,
        seen: tuple[Path, ...],
        depth: int,
    ) -> str:
        if not include_path:
            raise PromptRenderError("Include de prompt sin ruta.")
        if depth >= self.max_include_depth:
            raise PromptRenderError("Profundidad maxima de includes de prompt excedida.")
        base = source.parent if source is not None else self.root
        resolved = self._resolve_path(base / include_path)
        if resolved in seen:
            raise PromptRenderError(f"Include circular de prompt: {include_path}")
        text = resolved.read_text(encoding="utf-8")
        return self._render_text(
            text,
            variables,
            source=resolved,
            seen=(*seen, resolved),
            depth=depth + 1,
        )

    def _resolve_path(self, path: Path) -> Path:
        root = self.root.resolve()
        resolved = path.resolve()
        if not _is_relative_to(resolved, root):
            raise PromptRenderError(f"Ruta de prompt fuera del registry: {path}")
        if not resolved.exists() or not resolved.is_file():
            raise PromptRenderError(f"Archivo de prompt no encontrado: {path}")
        return resolved


_EXPRESSION_RE = re.compile(r"{{\s*(?P<expression>[^{}]+?)\s*}}")


def _split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return {}, text
    _, rest = normalized.split("---\n", 1)
    if "\n---\n" not in rest:
        raise PromptRenderError("Frontmatter de prompt sin cierre ---.")
    frontmatter, body = rest.split("\n---\n", 1)
    return _parse_frontmatter(frontmatter), body


def _parse_frontmatter(frontmatter: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw_line in frontmatter.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise PromptRenderError(f"Linea de frontmatter invalida: {raw_line}")
        key, value = line.split(":", 1)
        key = key.strip()
        if not key:
            raise PromptRenderError(f"Clave de frontmatter invalida: {raw_line}")
        data[key] = value.strip().strip('"').strip("'")
    return data


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
