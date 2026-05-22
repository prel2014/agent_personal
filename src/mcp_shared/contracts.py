from __future__ import annotations

from typing import Any, Literal, TypeVar

from pydantic import BaseModel, Field


ModelT = TypeVar("ModelT", bound=BaseModel)


def model_validate_compat(model_cls: type[ModelT], payload: Any) -> ModelT:
    if hasattr(model_cls, "model_validate"):
        return model_cls.model_validate(payload)
    return model_cls.parse_obj(payload)


def model_dump_compat(model: BaseModel, **kwargs) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(**kwargs)
    return model.dict(**kwargs)


class ToolFunction(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolCall(BaseModel):
    type: Literal["function"] = "function"
    function: ToolFunction


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str = ""
    thinking: str | None = None
    tool_name: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)

    @classmethod
    def from_wire(cls, payload: dict[str, Any]) -> "ChatMessage":
        normalized = dict(payload or {})
        normalized.setdefault("role", "assistant")
        normalized["content"] = normalized.get("content") or ""
        normalized["tool_calls"] = normalized.get("tool_calls") or []
        return model_validate_compat(cls, normalized)

    @classmethod
    def system(cls, content: str) -> "ChatMessage":
        return cls(role="system", content=content)

    @classmethod
    def user(cls, content: str) -> "ChatMessage":
        return cls(role="user", content=content)

    @classmethod
    def assistant(
        cls,
        *,
        content: str = "",
        thinking: str | None = None,
        tool_calls: list[ToolCall] | None = None,
    ) -> "ChatMessage":
        return cls(
            role="assistant",
            content=content,
            thinking=thinking,
            tool_calls=tool_calls or [],
        )

    @classmethod
    def tool_result(cls, tool_name: str, content: str) -> "ChatMessage":
        return cls(role="tool", tool_name=tool_name, content=content)

    def to_wire(self) -> dict[str, Any]:
        return model_dump_compat(self, exclude_none=True)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(default_factory=list)
    tools: list[dict[str, Any]] = Field(default_factory=list)
    client_context: dict[str, Any] = Field(default_factory=dict)
    stream: bool = False

    @classmethod
    def from_wire(cls, payload: dict[str, Any]) -> "ChatRequest":
        normalized = dict(payload or {})
        normalized["messages"] = [
            ChatMessage.from_wire(item).to_wire()
            for item in normalized.get("messages") or []
        ]
        normalized["tools"] = normalized.get("tools") or []
        normalized["client_context"] = normalized.get("client_context") or {}
        normalized["stream"] = bool(normalized.get("stream", False))
        return model_validate_compat(cls, normalized)

    def to_wire(self) -> dict[str, Any]:
        return model_dump_compat(self, exclude_none=True)


class ChatResponse(BaseModel):
    ok: bool = True
    error: str | None = None
    model: str | None = None
    node_id: str | None = None
    node_model: str | None = None
    done: bool = True
    done_reason: str | None = None
    message: ChatMessage = Field(default_factory=lambda: ChatMessage.assistant())

    @classmethod
    def from_wire(cls, payload: dict[str, Any]) -> "ChatResponse":
        normalized = dict(payload or {})
        normalized.setdefault("ok", True)
        normalized.setdefault("done", True)
        normalized["message"] = ChatMessage.from_wire(
            normalized.get("message") or {}
        ).to_wire()
        return model_validate_compat(cls, normalized)

    @classmethod
    def from_ollama(
        cls,
        payload: dict[str, Any],
        *,
        default_model: str,
    ) -> "ChatResponse":
        message = ChatMessage.from_wire(payload.get("message") or {})
        return cls(
            ok=True,
            model=payload.get("model", default_model),
            node_id=payload.get("node_id"),
            node_model=payload.get("node_model") or payload.get("model", default_model),
            done=payload.get("done", True),
            done_reason=payload.get("done_reason"),
            message=message,
        )

    def to_wire(self) -> dict[str, Any]:
        return model_dump_compat(self, exclude_none=True)
