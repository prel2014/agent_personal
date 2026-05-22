from __future__ import annotations

from typing import Iterable, Protocol

from src.mcp_shared.contracts import ChatResponse

from .state import AgentRunResult, AgentWorkflowState, ToolExecutionOutcome
from .tracing import TraceRecorder


class WorkflowHook(Protocol):
    def on_workflow_started(self, state: AgentWorkflowState) -> None:
        ...

    def on_stage_changed(self, state: AgentWorkflowState, detail: str | None = None) -> None:
        ...

    def on_assistant_response(
        self,
        state: AgentWorkflowState,
        response: ChatResponse,
    ) -> None:
        ...

    def on_tool_outcome(
        self,
        state: AgentWorkflowState,
        outcome: ToolExecutionOutcome,
    ) -> None:
        ...

    def on_auto_write(
        self,
        state: AgentWorkflowState,
        paths: list[str],
    ) -> None:
        ...

    def on_workflow_completed(
        self,
        state: AgentWorkflowState,
        result: AgentRunResult,
    ) -> None:
        ...


class CompositeWorkflowHook:
    def __init__(self, hooks: Iterable[WorkflowHook] = ()) -> None:
        self._hooks = tuple(hooks)

    def on_workflow_started(self, state: AgentWorkflowState) -> None:
        for hook in self._hooks:
            hook.on_workflow_started(state)

    def on_stage_changed(
        self,
        state: AgentWorkflowState,
        detail: str | None = None,
    ) -> None:
        for hook in self._hooks:
            hook.on_stage_changed(state, detail=detail)

    def on_assistant_response(
        self,
        state: AgentWorkflowState,
        response: ChatResponse,
    ) -> None:
        for hook in self._hooks:
            hook.on_assistant_response(state, response)

    def on_tool_outcome(
        self,
        state: AgentWorkflowState,
        outcome: ToolExecutionOutcome,
    ) -> None:
        for hook in self._hooks:
            hook.on_tool_outcome(state, outcome)

    def on_auto_write(
        self,
        state: AgentWorkflowState,
        paths: list[str],
    ) -> None:
        for hook in self._hooks:
            hook.on_auto_write(state, paths)

    def on_workflow_completed(
        self,
        state: AgentWorkflowState,
        result: AgentRunResult,
    ) -> None:
        for hook in self._hooks:
            hook.on_workflow_completed(state, result)


class TraceWorkflowHook:
    def __init__(self, recorder: TraceRecorder) -> None:
        self.recorder = recorder

    def on_workflow_started(self, state: AgentWorkflowState) -> None:
        self.recorder.record_stage(step=state.current_step, stage=state.stage)

    def on_stage_changed(
        self,
        state: AgentWorkflowState,
        detail: str | None = None,
    ) -> None:
        self.recorder.record_stage(
            step=state.current_step,
            stage=state.stage,
            detail=detail,
        )

    def on_assistant_response(
        self,
        state: AgentWorkflowState,
        response: ChatResponse,
    ) -> None:
        self.recorder.record_assistant_turn(state.current_step, response)

    def on_tool_outcome(
        self,
        state: AgentWorkflowState,
        outcome: ToolExecutionOutcome,
    ) -> None:
        self.recorder.record_tool_outcome(state.current_step, outcome)

    def on_auto_write(
        self,
        state: AgentWorkflowState,
        paths: list[str],
    ) -> None:
        self.recorder.record_auto_write(paths)

    def on_workflow_completed(
        self,
        state: AgentWorkflowState,
        result: AgentRunResult,
    ) -> None:
        self.recorder.complete(state.stage)
