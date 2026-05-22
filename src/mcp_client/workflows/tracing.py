from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..agentic.trace_store import (
    SQLiteTraceStore,
    TracePersistenceHook,
    TraceStoreSettings,
    new_trace_id,
)
from ..config.model import ClientConfig


@dataclass
class WorkflowTraceService:
    config: ClientConfig
    settings: TraceStoreSettings = field(init=False)
    store: SQLiteTraceStore | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        self.settings = TraceStoreSettings(
            db_path=self.config.trace_db_path,
            capture=self.config.trace_capture,
            thinking=self.config.trace_thinking,
        )
        self.store = SQLiteTraceStore.from_settings(self.settings)

    def new_run_id(self) -> str:
        return new_trace_id()

    def hooks(
        self,
        *,
        run_id: str,
        mode: str,
        role: str,
        attempt: int = 1,
        complete_run: bool,
        run_metadata: dict[str, Any] | None = None,
    ):
        if self.store is None:
            return ()
        return (
            TracePersistenceHook(
                store=self.store,
                settings=self.settings,
                run_id=run_id,
                mode=mode,
                role=role,
                attempt=attempt,
                complete_run=complete_run,
                run_metadata=run_metadata,
            ),
        )

    def create_routed_run(
        self,
        prompt: str,
        messages: list[dict[str, Any]] | None,
        route: str,
        reason: str,
        signals: list[str],
    ) -> str:
        run_id = self.new_run_id()
        if self.store is None:
            return run_id

        self.store.create_run(
            run_id=run_id,
            user_prompt=prompt if self.settings.capture == "full" else None,
            mode=f"auto:{route}",
            metadata={
                "route": route,
                "route_reason": reason,
                "route_signals": signals,
                "input_message_count": len(messages or []),
            },
        )
        self.store.record_event(
            run_id=run_id,
            event_type="route_decision",
            payload={"route": route, "reason": reason, "signals": signals},
        )
        return run_id
