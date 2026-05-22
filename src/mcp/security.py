from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Protocol

from .path_policies import (
    DEFAULT_PROTECTED_PATH_PATTERNS,
    DEFAULT_PROTECTED_READ_PATH_PATTERNS,
    matches_protected_path,
)
from .tools.categories import (
    DELETE,
    EXECUTE,
    HARDWARE,
    LEGACY_TOOL_CATEGORIES,
    MEDIA_INPUT,
    META,
    READ,
    SANDBOX_EXECUTE,
    WEB,
    WRITE,
)
TOOL_CATEGORIES: dict[str, str] = dict(LEGACY_TOOL_CATEGORIES)


@dataclass(frozen=True)
class ToolExecutionRequest:
    name: str
    arguments: dict[str, Any]
    category: str
    base_dir: Path

    def candidate_paths(self) -> list[Path]:
        paths: list[Path] = []
        for key in ("path", "path_a", "path_b", "target_path", "save_frame_path"):
            value = self.arguments.get(key)
            if isinstance(value, str):
                paths.append(Path(value))
        return paths


@dataclass(frozen=True)
class ToolExecutionEvent:
    request: ToolExecutionRequest
    success: bool
    result: Any | None = None
    error: str | None = None
    duration_ms: float | None = None


class ToolExecutionHook(Protocol):
    def before_tool(self, request: ToolExecutionRequest) -> None:
        ...

    def after_tool(self, event: ToolExecutionEvent) -> None:
        ...


class ToolApprovalRequiredError(PermissionError):
    def __init__(self, tool_name: str, reason: str) -> None:
        super().__init__(reason)
        self.tool_name = tool_name


@dataclass
class ToolAuditTrail:
    limit: int = 200
    events: list[ToolExecutionEvent] = field(default_factory=list)

    def before_tool(self, request: ToolExecutionRequest) -> None:
        return None

    def after_tool(self, event: ToolExecutionEvent) -> None:
        self.events.append(event)
        if len(self.events) > self.limit:
            self.events = self.events[-self.limit :]

    def snapshot(self, limit: int | None = None) -> list[dict[str, object]]:
        selected = self.events if limit is None else self.events[-limit:]
        return [
            {
                "tool": event.request.name,
                "category": event.request.category,
                "paths": [str(path) for path in event.request.candidate_paths()],
                "success": event.success,
                "error": event.error,
                "duration_ms": event.duration_ms,
            }
            for event in selected
        ]


@dataclass(frozen=True)
class PermissionPolicy:
    allow_read: bool = True
    allow_write: bool = True
    allow_execute: bool = True
    allow_delete: bool = False
    allow_hardware: bool = False
    allow_media_input: bool = False
    allow_web: bool = False
    allow_sandbox_execute: bool = False
    allowed_tools: frozenset[str] | None = None
    blocked_tools: frozenset[str] = frozenset()
    protected_path_patterns: tuple[str, ...] = DEFAULT_PROTECTED_PATH_PATTERNS
    protected_read_path_patterns: tuple[str, ...] = DEFAULT_PROTECTED_READ_PATH_PATTERNS
    confirmation_required_tools: frozenset[str] = frozenset()
    approved_sensitive_tools: frozenset[str] = frozenset()
    tool_hooks: tuple[ToolExecutionHook, ...] = ()
    tool_categories: Mapping[str, str] = field(
        default_factory=lambda: dict(TOOL_CATEGORIES)
    )

    def allows_tool(self, name: str) -> bool:
        return self.denial_reason(name) is None

    def denial_reason(self, name: str) -> str | None:
        category = self.tool_categories.get(name)
        if category is None:
            return f"La herramienta '{name}' no tiene una categoria de permisos registrada."

        if name in self.blocked_tools:
            return f"La herramienta '{name}' fue bloqueada por configuracion."

        if self.allowed_tools is not None and name not in self.allowed_tools and category != META:
            return f"La herramienta '{name}' no esta incluida en la allowlist activa."

        if category == META:
            return None

        if category == READ and not self.allow_read:
            return f"La herramienta '{name}' requiere permiso de lectura y esta deshabilitada."

        if category == WRITE and not self.allow_write:
            return f"La herramienta '{name}' requiere permiso de escritura y esta deshabilitada."

        if category == EXECUTE and not self.allow_execute:
            return f"La herramienta '{name}' requiere permiso de ejecucion y esta deshabilitada."

        if category == DELETE and not self.allow_delete:
            return f"La herramienta '{name}' requiere permiso de borrado y esta deshabilitada."

        if category == HARDWARE and not self.allow_hardware:
            return f"La herramienta '{name}' requiere permiso de hardware y esta deshabilitada."

        if category == MEDIA_INPUT and not self.allow_media_input:
            return f"La herramienta '{name}' requiere permiso de entrada multimedia y esta deshabilitada."

        if category == WEB and not self.allow_web:
            return f"La herramienta '{name}' requiere permiso web y esta deshabilitada."

        if category == SANDBOX_EXECUTE and not self.allow_sandbox_execute:
            return f"La herramienta '{name}' requiere permiso de ejecucion en sandbox y esta deshabilitada."

        return None

    def require_tool(self, name: str) -> None:
        reason = self.denial_reason(name)
        if reason is not None:
            raise PermissionError(reason)

    def build_request(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        base_dir: Path,
    ) -> ToolExecutionRequest:
        return ToolExecutionRequest(
            name=name,
            arguments=dict(arguments),
            category=self.tool_categories.get(name, ""),
            base_dir=base_dir,
        )

    def before_tool(self, request: ToolExecutionRequest) -> None:
        self.require_tool(request.name)
        approval_reason = self._approval_required_reason(request)
        if approval_reason is not None:
            raise ToolApprovalRequiredError(request.name, approval_reason)
        path_reason = self._protected_path_reason(request)
        if path_reason is not None:
            raise PermissionError(path_reason)

        for hook in self.tool_hooks:
            hook.before_tool(request)

    def after_tool(self, event: ToolExecutionEvent) -> None:
        for hook in self.tool_hooks:
            hook.after_tool(event)

    def _protected_path_reason(self, request: ToolExecutionRequest) -> str | None:
        if request.category not in {READ, WRITE, DELETE, MEDIA_INPUT}:
            return None

        candidate_paths = request.candidate_paths()
        if request.category == MEDIA_INPUT:
            value = request.arguments.get("save_frame_path")
            candidate_paths = [Path(value)] if isinstance(value, str) else []

        patterns = (
            self.protected_read_path_patterns
            if request.category == READ
            else self.protected_path_patterns
        )
        action_text = "leer" if request.category == READ else "modificar"

        for path in candidate_paths:
            if matches_protected_path(
                path,
                patterns=patterns,
                base_dir=request.base_dir,
            ):
                normalized = self._relative_path(path, request.base_dir)
                visible = normalized.as_posix() if normalized is not None else str(path)
                return (
                    f"La herramienta '{request.name}' no puede {action_text} "
                    f"la ruta protegida '{visible}'."
                )
        return None

    def _approval_required_reason(self, request: ToolExecutionRequest) -> str | None:
        if request.name not in self.confirmation_required_tools:
            return None
        if request.name in self.approved_sensitive_tools:
            return None
        return (
            f"La herramienta sensible '{request.name}' requiere aprobacion previa "
            "antes de ejecutarse."
        )

    @staticmethod
    def _relative_path(path: Path, base_dir: Path) -> Path | None:
        try:
            return path.resolve().relative_to(base_dir.resolve())
        except ValueError:
            return None

    def summary(self) -> dict[str, object]:
        return {
            "allow_read": self.allow_read,
            "allow_write": self.allow_write,
            "allow_execute": self.allow_execute,
            "allow_delete": self.allow_delete,
            "allow_hardware": self.allow_hardware,
            "allow_media_input": self.allow_media_input,
            "allow_web": self.allow_web,
            "allow_sandbox_execute": self.allow_sandbox_execute,
            "allowed_tools": sorted(self.allowed_tools) if self.allowed_tools is not None else None,
            "blocked_tools": sorted(self.blocked_tools),
            "protected_path_patterns": list(self.protected_path_patterns),
            "protected_read_path_patterns": list(self.protected_read_path_patterns),
            "confirmation_required_tools": sorted(self.confirmation_required_tools),
            "approved_sensitive_tools": sorted(self.approved_sensitive_tools),
        }
