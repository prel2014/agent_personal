from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ToolAccess = Literal["none", "read_only", "full"]


@dataclass(frozen=True)
class SubagentSpec:
    name: str
    description: str
    directive: str
    tool_access: ToolAccess = "full"
    tools: tuple[str, ...] | None = None
    built_in: bool = False
    source: str = "built-in"

    def catalog_entry(self) -> dict[str, object]:
        entry: dict[str, object] = {
            "name": self.name,
            "description": self.description,
            "tool_access": self.tool_access,
            "source": self.source,
        }
        if self.tools is not None:
            entry["tools"] = list(self.tools)
        return entry
