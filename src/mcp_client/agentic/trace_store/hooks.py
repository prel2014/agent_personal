from __future__ import annotations

import json
from typing import Any

from src.mcp_shared.contracts import ChatMessage, ChatResponse

from ..state import AgentRunResult, AgentWorkflowState, ToolExecutionOutcome
from .models import TraceStoreSettings, new_trace_id
from .redaction import redact_payload, redact_text
from .sqlite_store import SQLiteTraceStore

class TracePersistenceHook:
    def __init__(
        self,
        *,
        store: SQLiteTraceStore,
        settings: TraceStoreSettings,
        run_id: str,
        mode: str,
        role: str,
        attempt: int = 1,
        complete_run: bool = True,
        run_metadata: dict[str, Any] | None = None,
    ) -> None:
        self.store = store
        self.settings = settings
        self.run_id = run_id
        self.phase_id = new_trace_id()
        self.mode = mode
        self.role = role
        self.attempt = attempt
        self.complete_run = complete_run
        self.run_metadata = run_metadata or {}
        self._input_recorded = False
        self._message_sequence = 0
        self._last_response: ChatResponse | None = None

    def on_workflow_started(self, state: AgentWorkflowState) -> None:
        self.store.create_run(
            run_id=self.run_id,
            user_prompt=(
                state.memory.last_user_prompt()
                if self.settings.capture == "full"
                else None
            ),
            mode=self.mode,
            metadata=self.run_metadata,
        )
        self.store.create_phase(
            phase_id=self.phase_id,
            run_id=self.run_id,
            role=self.role,
            attempt=self.attempt,
            metadata={"mode": self.mode},
        )
        self.store.record_event(
            run_id=self.run_id,
            phase_id=self.phase_id,
            step=state.current_step,
            event_type="workflow_started",
            payload={"stage": state.stage.value, "role": self.role, "attempt": self.attempt},
        )
        self._record_input_messages(state)

    def on_stage_changed(
        self,
        state: AgentWorkflowState,
        detail: str | None = None,
    ) -> None:
        self.store.record_event(
            run_id=self.run_id,
            phase_id=self.phase_id,
            step=state.current_step,
            event_type="stage_changed",
            payload={"stage": state.stage.value, "detail": detail},
        )

    def on_assistant_response(
        self,
        state: AgentWorkflowState,
        response: ChatResponse,
    ) -> None:
        self._last_response = response
        message = response.message
        self.store.record_event(
            run_id=self.run_id,
            phase_id=self.phase_id,
            step=state.current_step,
            event_type="assistant_response",
            payload=self._assistant_event_payload(response),
        )
        self.store.record_message(
            run_id=self.run_id,
            phase_id=self.phase_id,
            step=state.current_step,
            sequence=self._next_sequence(),
            role=message.role,
            source="assistant_response",
            content=self._captured_content(message.content),
            thinking=self._captured_thinking(message.thinking),
            tool_name=message.tool_name,
            tool_calls=self._captured_tool_calls(message),
            model=response.model,
            node_id=response.node_id,
            node_model=response.node_model,
            metadata={
                "done": response.done,
                "done_reason": response.done_reason,
                "content_chars": len(message.content or ""),
                "thinking_chars": len(message.thinking or ""),
            },
        )

    def on_tool_outcome(
        self,
        state: AgentWorkflowState,
        outcome: ToolExecutionOutcome,
    ) -> None:
        payload = {
            "name": outcome.name,
            "success": outcome.success,
            "duration_ms": outcome.duration_ms,
            "error": outcome.result.get("error"),
        }
        if self.settings.capture == "full":
            payload["arguments"] = outcome.arguments
            payload["result"] = outcome.result
        else:
            payload["argument_keys"] = sorted(outcome.arguments)
            result = outcome.result.get("result")
            payload["result_type"] = type(result).__name__

        self.store.record_event(
            run_id=self.run_id,
            phase_id=self.phase_id,
            step=state.current_step,
            event_type="tool_outcome",
            payload=payload,
        )
        self.store.record_message(
            run_id=self.run_id,
            phase_id=self.phase_id,
            step=state.current_step,
            sequence=self._next_sequence(),
            role="tool",
            source="tool_result",
            content=(
                json.dumps(redact_payload(outcome.result), ensure_ascii=False)
                if self.settings.capture == "full"
                else None
            ),
            tool_name=outcome.name,
            metadata={
                "success": outcome.success,
                "duration_ms": outcome.duration_ms,
                "argument_keys": sorted(outcome.arguments),
            },
        )

    def on_auto_write(
        self,
        state: AgentWorkflowState,
        paths: list[str],
    ) -> None:
        self.store.record_event(
            run_id=self.run_id,
            phase_id=self.phase_id,
            step=state.current_step,
            event_type="auto_write",
            payload={"paths": paths, "count": len(paths)},
        )
        for path in paths:
            self.store.record_artifact(
                run_id=self.run_id,
                phase_id=self.phase_id,
                artifact_type="auto_written_file",
                path=path,
            )

    def on_workflow_completed(
        self,
        state: AgentWorkflowState,
        result: AgentRunResult,
    ) -> None:
        self.store.complete_phase(
            phase_id=self.phase_id,
            model=self._last_response.model if self._last_response else None,
            node_id=self._last_response.node_id if self._last_response else None,
            node_model=self._last_response.node_model if self._last_response else None,
        )
        if self.complete_run:
            self.store.complete_run(
                run_id=self.run_id,
                final_answer=self._captured_content(result.final),
                metadata={"final_stage": state.stage.value, "mode": self.mode},
            )

        self._record_dataset_example(state)
        result.trace["trace_run_id"] = self.run_id
        result.trace["trace_phase_id"] = self.phase_id
        result.trace["trace_db_path"] = str(self.store.db_path)

    def _record_input_messages(self, state: AgentWorkflowState) -> None:
        if self._input_recorded:
            return
        self._input_recorded = True
        for message in state.memory.messages:
            self.store.record_message(
                run_id=self.run_id,
                phase_id=self.phase_id,
                step=state.current_step,
                sequence=self._next_sequence(),
                role=message.role,
                source="input_context",
                content=self._captured_content(message.content),
                thinking=self._captured_thinking(message.thinking),
                tool_name=message.tool_name,
                tool_calls=self._captured_tool_calls(message),
                metadata={
                    "content_chars": len(message.content or ""),
                    "thinking_chars": len(message.thinking or ""),
                },
            )

    def _record_dataset_example(self, state: AgentWorkflowState) -> None:
        if self.settings.capture != "full":
            return
        messages = state.memory.messages
        if not messages or messages[-1].role != "assistant":
            return

        self.store.record_dataset_example(
            run_id=self.run_id,
            phase_id=self.phase_id,
            example_type="sft_conversation",
            input_payload={
                "messages": [
                    self._training_message_payload(message)
                    for message in messages[:-1]
                ],
                "role": self.role,
                "mode": self.mode,
            },
            output_payload={
                "message": self._training_message_payload(messages[-1]),
            },
            tags=[f"role:{self.role}", f"mode:{self.mode}"],
        )

    def _assistant_event_payload(self, response: ChatResponse) -> dict[str, Any]:
        message = response.message
        payload: dict[str, Any] = {
            "model": response.model,
            "node_id": response.node_id,
            "node_model": response.node_model,
            "done": response.done,
            "done_reason": response.done_reason,
            "content_chars": len(message.content or ""),
            "thinking_chars": len(message.thinking or ""),
            "tool_calls": self._captured_tool_calls(message),
        }
        if self.settings.capture == "full":
            payload["message"] = self._training_message_payload(message)
        return payload

    def _training_message_payload(self, message: ChatMessage) -> dict[str, Any]:
        payload = {
            "role": message.role,
            "content": redact_text(message.content or ""),
        }
        if message.tool_name:
            payload["tool_name"] = message.tool_name
        if message.tool_calls:
            payload["tool_calls"] = message_tool_calls(message)
        thinking = self._captured_thinking(message.thinking)
        if thinking is not None:
            payload["thinking"] = thinking
        return payload

    def _captured_content(self, content: str | None) -> str | None:
        if self.settings.capture != "full":
            return None
        return redact_text(content or "")

    def _captured_thinking(self, thinking: str | None) -> str | None:
        if not thinking:
            return None
        if self.settings.thinking == "raw":
            return redact_text(thinking)
        if self.settings.thinking == "summary":
            return f"[thinking omitted; chars={len(thinking)}]"
        return None

    def _captured_tool_calls(self, message: ChatMessage) -> list[dict[str, Any]]:
        if self.settings.capture == "full":
            return message_tool_calls(message)
        return summarize_tool_calls(message)

    def _next_sequence(self) -> int:
        self._message_sequence += 1
        return self._message_sequence

def message_tool_calls(message: ChatMessage) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for call in message.tool_calls:
        if hasattr(call, "model_dump"):
            raw = call.model_dump()
        elif hasattr(call, "dict"):
            raw = call.dict()
        else:
            raw = call
        calls.append(redact_payload(raw))
    return calls

def summarize_tool_calls(message: ChatMessage) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for call in message.tool_calls:
        function = getattr(call, "function", None)
        arguments = getattr(function, "arguments", None) or {}
        summaries.append(
            {
                "type": getattr(call, "type", "function"),
                "function": {
                    "name": getattr(function, "name", None),
                    "argument_keys": sorted(str(key) for key in arguments),
                },
            }
        )
    return summaries
