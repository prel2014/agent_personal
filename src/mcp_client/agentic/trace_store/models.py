from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.mcp_shared.storage import new_prefixed_id

TraceCaptureMode = Literal["off", "metadata", "full"]
TraceThinkingMode = Literal["off", "summary", "raw"]

DEFAULT_TRACE_DB_PATH = ".mcp_traces/agent_traces.sqlite"

def new_trace_id() -> str:
    return new_prefixed_id("trace")

@dataclass(frozen=True)
class TraceStoreSettings:
    db_path: str | None = None
    capture: TraceCaptureMode = "off"
    thinking: TraceThinkingMode = "raw"

    @property
    def enabled(self) -> bool:
        return self.capture != "off"

    @property
    def resolved_db_path(self) -> str:
        return self.db_path or DEFAULT_TRACE_DB_PATH
