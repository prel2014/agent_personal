from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


OutputMode = Literal["minimal", "normal", "debug"]
VALID_OUTPUT_MODES = frozenset({"minimal", "normal", "debug"})


def normalize_output_mode(value: str | None) -> OutputMode:
    mode = (value or "normal").strip().lower()
    if mode not in VALID_OUTPUT_MODES:
        raise ValueError("output_mode debe ser minimal, normal o debug.")
    return mode  # type: ignore[return-value]


@dataclass(frozen=True)
class PresentationPolicy:
    output_mode: OutputMode = "normal"

    @property
    def is_minimal(self) -> bool:
        return self.output_mode == "minimal"

    @property
    def is_normal(self) -> bool:
        return self.output_mode == "normal"

    @property
    def is_debug(self) -> bool:
        return self.output_mode == "debug"

    def show_route(self) -> bool:
        return self.is_debug

    def show_team_phase(self) -> bool:
        return not self.is_minimal

    def show_tool_events(self) -> bool:
        return not self.is_minimal

    def show_tool_details(self) -> bool:
        return self.is_debug

    def show_intermediate_assistant(self) -> bool:
        return self.is_debug

    def show_public_final_from_team(self) -> bool:
        return not self.is_debug

    def show_context_usage(self, configured: bool) -> bool:
        return configured and self.is_debug
