from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


SkillScope = Literal["worker", "reviewer", "all"]


@dataclass(frozen=True)
class SkillSpec:
    name: str
    description: str
    directive: str
    scope: SkillScope = "all"
    tags: tuple[str, ...] = ()
    version: str = ""
    source: str = "built-in"

    def applies_to_role(self, role_name: str) -> bool:
        if self.scope == "all":
            return True
        return self.scope == role_name

    def catalog_entry(self) -> dict[str, object]:
        entry: dict[str, object] = {
            "name": self.name,
            "description": self.description,
            "scope": self.scope,
            "source": self.source,
        }
        if self.tags:
            entry["tags"] = list(self.tags)
        if self.version:
            entry["version"] = self.version
        return entry
