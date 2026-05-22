from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...config.model import ClientConfig
from ..roles import ReviewDecision
from ..state import AgentRunResult
from ..trace_store import SQLiteTraceStore, TracePersistenceHook, TraceStoreSettings


@dataclass
class TeamTraceLifecycle:
    config: ClientConfig
    store: SQLiteTraceStore | None
    settings: TraceStoreSettings | None

    @classmethod
    def from_config(
        cls,
        config: ClientConfig,
        *,
        store: SQLiteTraceStore | None = None,
        settings: TraceStoreSettings | None = None,
    ) -> "TeamTraceLifecycle":
        resolved_settings = settings or TraceStoreSettings(
            db_path=config.trace_db_path,
            capture=config.trace_capture,
            thinking=config.trace_thinking,
        )
        resolved_store = store
        if resolved_store is None:
            resolved_store = SQLiteTraceStore.from_settings(resolved_settings)
        return cls(config=config, store=resolved_store, settings=resolved_settings)

    def hooks(self, *, run_id: str, role: str, attempt: int):
        if self.store is None or self.settings is None:
            return ()
        return (
            TracePersistenceHook(
                store=self.store,
                settings=self.settings,
                run_id=run_id,
                mode="team_orchestrator",
                role=role,
                attempt=attempt,
                complete_run=False,
                run_metadata={"mode": "team_orchestrator"},
            ),
        )

    def create_run(
        self,
        run_id: str,
        prompt: str,
        base_messages: list[dict[str, Any]],
    ) -> None:
        if self.store is None or self.settings is None:
            return
        self.store.create_run(
            run_id=run_id,
            user_prompt=prompt if self.settings.capture == "full" else None,
            mode="team_orchestrator",
            metadata={
                "input_message_count": len(base_messages),
                "planning_mode": self.config.planning_mode,
            },
        )

    def complete_run(
        self,
        *,
        run_id: str,
        prompt: str,
        base_messages: list[dict[str, Any]],
        result: AgentRunResult,
        plan_summary: str,
        review_decision: ReviewDecision,
    ) -> None:
        if self.store is None or self.settings is None:
            return

        metadata: dict[str, Any] = {
            "mode": "team_orchestrator",
            "approved": review_decision.approved,
        }
        if self.settings.capture == "full":
            metadata["review_summary"] = review_decision.summary

        self.store.complete_run(
            run_id=run_id,
            final_answer=result.final if self.settings.capture == "full" else None,
            metadata=metadata,
        )
        if self.settings.capture == "full":
            self.store.record_dataset_example(
                run_id=run_id,
                phase_id=None,
                example_type="team_final",
                input_payload={
                    "prompt": prompt,
                    "messages": base_messages,
                    "plan_summary": plan_summary,
                },
                output_payload={
                    "final": result.final,
                    "review": {
                        "approved": review_decision.approved,
                        "summary": review_decision.summary,
                    },
                },
                tags=["mode:team_orchestrator", "role:team"],
            )
        result.trace["trace_run_id"] = run_id
        result.trace["trace_db_path"] = str(self.store.db_path)
