from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from src.mcp_shared.agent_contracts import AgentExecutionContext


class ContextProvider(Protocol):
    name: str

    def build(self, context: AgentExecutionContext) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class RuntimeContextProvider:
    name: str = "runtime"

    def build(self, context: AgentExecutionContext) -> dict[str, Any]:
        return _compact(
            {
                "base_dir": context.base_dir,
                "encoding": context.encoding,
                "prompt_mode": context.prompt_mode,
                "agent_role": context.agent_role,
                "direct_answer_mode": True if context.direct_answer_mode else None,
                "orchestration": context.orchestration,
                "permissions": context.permissions,
                "detected_languages": context.detected_languages,
                "primary_language": context.primary_language,
                "tooling": context.tooling,
                "sandbox": context.sandbox,
                "media_input": context.media_input,
                "location_hint": context.location_hint,
            }
        )


@dataclass(frozen=True)
class ToolContextProvider:
    name: str = "tools"

    def build(self, context: AgentExecutionContext) -> dict[str, Any]:
        return _compact(
            {
                "available_tools": context.available_tools,
                "tool_categories": context.tool_categories,
                "tool_selection": context.tool_selection,
            }
        )


@dataclass(frozen=True)
class SubagentContextProvider:
    name: str = "subagents"

    def build(self, context: AgentExecutionContext) -> dict[str, Any]:
        return _compact({"subagents": context.subagents})


@dataclass(frozen=True)
class SafetyContextProvider:
    name: str = "safety"

    def build(self, context: AgentExecutionContext) -> dict[str, Any]:
        return _compact(
            {
                "tool_confirmation": context.tool_confirmation,
                "untrusted_tools": context.untrusted_tools,
            }
        )


@dataclass(frozen=True)
class SkillMemoryContextProvider:
    name: str = "skill_memory"

    def build(self, context: AgentExecutionContext) -> dict[str, Any]:
        return _compact(
            {
                "active_skill": context.active_skill,
                "memories": context.memories,
            }
        )


DEFAULT_CONTEXT_PROVIDERS: tuple[ContextProvider, ...] = (
    RuntimeContextProvider(),
    ToolContextProvider(),
    SubagentContextProvider(),
    SafetyContextProvider(),
    SkillMemoryContextProvider(),
)


@dataclass(frozen=True)
class PromptContextComposer:
    providers: tuple[ContextProvider, ...] = field(
        default_factory=lambda: DEFAULT_CONTEXT_PROVIDERS
    )

    def payload(self, context: AgentExecutionContext) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for provider in self.providers:
            payload.update(provider.build(context))
        return payload


def _compact(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, {}, [])
    }
