from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ..frontmatter import parse_frontmatter, split_frontmatter
from .models import SkillScope, SkillSpec

_VALID_SCOPES: frozenset[str] = frozenset({"worker", "reviewer", "all"})


class SkillRegistry:
    def __init__(self, specs: Iterable[SkillSpec] = ()) -> None:
        self._specs: dict[str, SkillSpec] = {}
        for spec in specs:
            self._specs[spec.name] = spec

    @classmethod
    def from_paths(cls, paths: Iterable[Path]) -> "SkillRegistry":
        specs: list[SkillSpec] = []
        for directory in paths:
            if not directory.exists() or not directory.is_dir():
                continue
            for path in sorted(directory.glob("*.md")):
                try:
                    specs.append(load_skill_file(path))
                except (ValueError, OSError):
                    pass
        return cls(specs)

    def get(self, name: str) -> SkillSpec | None:
        return self._specs.get(name)

    def list_all(self) -> list[SkillSpec]:
        return [self._specs[name] for name in sorted(self._specs)]

    def catalog(self) -> list[dict[str, object]]:
        return [spec.catalog_entry() for spec in self.list_all()]


def load_skill_file(path: Path) -> SkillSpec:
    text = path.read_text(encoding="utf-8")
    frontmatter, body = split_frontmatter(text)
    data = parse_frontmatter(frontmatter)

    name = data.get("name") or path.stem
    description = data.get("description")
    if not description:
        raise ValueError(f"Skill sin description: {path}")

    scope_raw = data.get("scope", "all")
    if scope_raw not in _VALID_SCOPES:
        raise ValueError(f"scope invalido en {path}: {scope_raw!r}. Valores: {sorted(_VALID_SCOPES)}")
    scope: SkillScope = scope_raw  # type: ignore[assignment]

    raw_tags = data.get("tags", "")
    tags: tuple[str, ...] = tuple(
        t.strip() for t in raw_tags.split(",") if t.strip()
    ) if raw_tags else ()

    version = data.get("version", "")

    directive = body.strip()
    if not directive:
        raise ValueError(f"Skill sin cuerpo/directive: {path}")

    return SkillSpec(
        name=name,
        description=description,
        directive=directive,
        scope=scope,
        tags=tags,
        version=version,
        source=str(path),
    )
