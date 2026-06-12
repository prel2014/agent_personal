from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PromptTemplate:
    id: str
    version: int
    label: str
    modes: tuple[str, ...]
    sections: tuple[str, ...]
    required_context: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PromptTemplate":
        return cls(
            id=str(payload["id"]),
            version=int(payload.get("version", 1)),
            label=str(payload.get("label", "production")),
            modes=tuple(str(item) for item in payload.get("modes", ())),
            sections=tuple(str(item) for item in payload.get("sections", ())),
            required_context=tuple(
                str(item) for item in payload.get("required_context", ())
            ),
        )


class PromptRegistry:
    def __init__(self, root: Path, templates: list[PromptTemplate]) -> None:
        self.root = root
        self.templates = templates

    @classmethod
    def from_directory(cls, root: Path) -> "PromptRegistry":
        registry_path = root / "registry.json"
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
        templates = [
            PromptTemplate.from_dict(item)
            for item in payload.get("templates", [])
            if isinstance(item, dict)
        ]
        return cls(root=root, templates=templates)

    def resolve(
        self,
        mode: str | None,
        *,
        label: str = "production",
    ) -> PromptTemplate | None:
        normalized_mode = _normalize_mode(mode)
        for template in self.templates:
            if template.label == label and normalized_mode in template.modes:
                return template
        for template in self.templates:
            if normalized_mode in template.modes:
                return template
        return None

    def render_sections(self, template: PromptTemplate) -> list[str]:
        sections: list[str] = []
        for section in template.sections:
            section_path = self.section_path(section)
            text = section_path.read_text(encoding="utf-8").strip()
            if text:
                sections.append(text)
        return sections

    def section_path(self, section: str) -> Path:
        section_path = (self.root / section).resolve()
        if not _is_relative_to(section_path, self.root.resolve()):
            raise ValueError(f"Seccion de prompt fuera del registry: {section}")
        return section_path


def default_prompt_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "prompts"


@lru_cache(maxsize=1)
def load_default_prompt_registry() -> PromptRegistry | None:
    try:
        root = default_prompt_dir()
        if not (root / "registry.json").exists():
            return None
        return PromptRegistry.from_directory(root)
    except Exception:
        return None


def _normalize_mode(mode: str | None) -> str:
    if not mode:
        return "tool_workflow"
    if mode == "worker":
        return "tool_workflow"
    return mode


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
