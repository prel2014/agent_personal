from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


READ = "read"
WRITE = "write"
EXECUTE = "execute"
DELETE = "delete"
META = "meta"
HARDWARE = "hardware"
MEDIA_INPUT = "media_input"
WEB = "web"
SANDBOX_EXECUTE = "sandbox_execute"

ToolCategory = Literal[
    "read",
    "write",
    "execute",
    "delete",
    "meta",
    "hardware",
    "media_input",
    "web",
    "sandbox_execute",
]

VALID_TOOL_CATEGORIES = frozenset(
    {
        READ,
        WRITE,
        EXECUTE,
        DELETE,
        META,
        HARDWARE,
        MEDIA_INPUT,
        WEB,
        SANDBOX_EXECUTE,
    }
)

READ_ONLY_TOOL_CATEGORIES = frozenset({READ, META, MEDIA_INPUT})
SANDBOX_TOOL_CATEGORIES = frozenset(
    {READ, WRITE, EXECUTE, DELETE, META, MEDIA_INPUT, WEB, SANDBOX_EXECUTE}
)


class AgentExecutionContext(BaseModel):
    base_dir: str | None = None
    encoding: str | None = None
    permissions: dict[str, Any] = Field(default_factory=dict)
    runtime_policy: dict[str, Any] = Field(default_factory=dict)
    available_tools: list[str] = Field(default_factory=list)
    tool_categories: dict[str, str] = Field(default_factory=dict)
    untrusted_tools: list[str] = Field(default_factory=list)
    agent_role: str | None = None
    role_directive: str | None = None
    prompt_mode: str | None = None
    direct_answer_mode: bool = False
    orchestration: dict[str, Any] = Field(default_factory=dict)
    sandbox: dict[str, Any] = Field(default_factory=dict)
    media_input: dict[str, Any] = Field(default_factory=dict)
    tool_confirmation: dict[str, Any] = Field(default_factory=dict)
    kv_cache: dict[str, Any] = Field(default_factory=dict)
    detected_languages: list[str] = Field(default_factory=list)
    primary_language: str | None = None
    language_markers: dict[str, Any] = Field(default_factory=dict)
    language_file_counts: dict[str, int] = Field(default_factory=dict)
    tooling: dict[str, Any] = Field(default_factory=dict)
    location_hint: str | None = None
    prompts: list[dict[str, Any]] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_runtime_context(cls, context: dict[str, Any]) -> "AgentExecutionContext":
        model_fields = getattr(cls, "model_fields", None)
        known_fields = set(model_fields or getattr(cls, "__fields__", {}))
        known_payload = {key: value for key, value in context.items() if key in known_fields}
        extra = {key: value for key, value in context.items() if key not in known_fields}
        known_payload["extra"] = extra
        return cls(**known_payload)

    def to_wire(self) -> dict[str, Any]:
        if hasattr(self, "model_dump"):
            payload = self.model_dump(exclude_none=True, exclude_defaults=True)
        else:
            payload = self.dict(exclude_none=True, exclude_defaults=True)

        extra = payload.pop("extra", {}) or {}
        return {**payload, **extra}
