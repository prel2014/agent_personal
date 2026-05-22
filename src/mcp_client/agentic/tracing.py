from __future__ import annotations

from dataclasses import asdict, dataclass, field

from src.mcp_shared.contracts import ChatResponse
from src.mcp_shared.storage import new_prefixed_id, utc_now_text

from .state import ToolExecutionOutcome, WorkflowStage


def _utc_now() -> str:
    return utc_now_text()


@dataclass
class StageTrace:
    step: int
    stage: str
    timestamp: str
    detail: str | None = None


@dataclass
class AssistantTrace:
    step: int
    model: str | None
    node_id: str | None
    node_model: str | None
    done_reason: str | None
    content_chars: int
    thinking_chars: int
    tool_calls: int
    timestamp: str


@dataclass
class ToolTrace:
    step: int
    name: str
    success: bool
    duration_ms: float | None
    error: str | None
    timestamp: str


@dataclass
class WorkflowTrace:
    workflow_id: str
    started_at: str
    completed_at: str | None = None
    final_stage: str | None = None
    stages: list[StageTrace] = field(default_factory=list)
    assistant_turns: list[AssistantTrace] = field(default_factory=list)
    tool_executions: list[ToolTrace] = field(default_factory=list)
    auto_written_files: list[str] = field(default_factory=list)


class TraceRecorder:
    def __init__(self) -> None:
        self.trace = WorkflowTrace(
            workflow_id=new_prefixed_id("workflow"),
            started_at=_utc_now(),
        )

    def record_stage(
        self,
        *,
        step: int,
        stage: WorkflowStage,
        detail: str | None = None,
    ) -> None:
        self.trace.stages.append(
            StageTrace(
                step=step,
                stage=stage.value,
                timestamp=_utc_now(),
                detail=detail,
            )
        )

    def record_assistant_turn(self, step: int, response: ChatResponse) -> None:
        message = response.message
        self.trace.assistant_turns.append(
            AssistantTrace(
                step=step,
                model=response.model,
                node_id=response.node_id,
                node_model=response.node_model,
                done_reason=response.done_reason,
                content_chars=len(message.content or ""),
                thinking_chars=len(message.thinking or ""),
                tool_calls=len(message.tool_calls),
                timestamp=_utc_now(),
            )
        )

    def record_tool_outcome(self, step: int, outcome: ToolExecutionOutcome) -> None:
        self.trace.tool_executions.append(
            ToolTrace(
                step=step,
                name=outcome.name,
                success=outcome.success,
                duration_ms=outcome.duration_ms,
                error=outcome.result.get("error"),
                timestamp=_utc_now(),
            )
        )

    def record_auto_write(self, paths: list[str]) -> None:
        self.trace.auto_written_files.extend(paths)

    def complete(self, stage: WorkflowStage) -> None:
        self.trace.completed_at = _utc_now()
        self.trace.final_stage = stage.value

    def to_dict(self) -> dict[str, object]:
        return asdict(self.trace)
