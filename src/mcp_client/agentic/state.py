from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.mcp_shared.contracts import ChatMessage, ChatResponse

from ..tool_results import tool_effective_error, tool_effective_success


class WorkflowStage(str, Enum):
    PLANNING = "planning"
    REQUESTING_ASSISTANT = "requesting_assistant"
    EXECUTING_TOOLS = "executing_tools"
    AUTO_WRITING = "auto_writing"
    COMPLETED = "completed"


@dataclass
class ConversationMemory:
    messages: list[ChatMessage] = field(default_factory=list)

    @classmethod
    def from_wire(
        cls,
        messages: list[dict[str, Any]] | None = None,
    ) -> "ConversationMemory":
        return cls(
            messages=[ChatMessage.from_wire(message) for message in messages or []]
        )

    def append_user(self, content: str) -> None:
        self.messages.append(ChatMessage.user(content))

    def append_system(self, content: str) -> None:
        self.messages.append(ChatMessage.system(content))

    def append_assistant(self, message: ChatMessage) -> None:
        self.messages.append(message)

    def append_tool(self, tool_name: str, content: str) -> None:
        self.messages.append(ChatMessage.tool_result(tool_name, content))

    def last_user_prompt(self) -> str:
        for message in reversed(self.messages):
            if message.role == "user":
                return message.content
        return ""

    def to_wire(self) -> list[dict[str, Any]]:
        return [message.to_wire() for message in self.messages]

    def copy(self) -> "ConversationMemory":
        return ConversationMemory(messages=list(self.messages))


@dataclass(frozen=True)
class ToolExecutionOutcome:
    name: str
    arguments: dict[str, Any]
    result: dict[str, Any]
    duration_ms: float | None = None

    @property
    def success(self) -> bool:
        return tool_effective_success(self.result)

    @property
    def error(self) -> str | None:
        return tool_effective_error(self.result)


@dataclass
class AgentWorkflowState:
    memory: ConversationMemory
    stage: WorkflowStage = WorkflowStage.PLANNING
    current_step: int = 0
    last_response: ChatResponse | None = None


@dataclass
class AgentRunResult:
    final: str
    memory: ConversationMemory
    response: ChatResponse
    auto_written_files: list[str] = field(default_factory=list)
    trace: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "final": self.final,
            "messages": self.memory.to_wire(),
            "response": self.response.to_wire(),
            "auto_written_files": list(self.auto_written_files),
            "trace": dict(self.trace),
        }
