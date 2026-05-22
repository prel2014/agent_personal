from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any

from src.mcp_shared.agent_contracts import AgentExecutionContext, META

from ..prompts.defaults import list_prompts, render_prompt
from ..security import ToolAuditTrail, ToolExecutionEvent
from ..tools.models import RuntimeToolCall, ToolDefinition
from ..tools.helpers import hardware_tools, web_tools
from ..tools.helpers.read_policy import configure_read_policy
from ..tools.helpers.kv_functions import configure_kv_store
from .arguments import (
    DISCOVERABLE_FILE_PATH_TOOLS as RUNTIME_DISCOVERABLE_FILE_PATH_TOOLS,
    PATH_ARGUMENTS as RUNTIME_PATH_ARGUMENTS,
    RuntimeArgumentNormalizer,
    SERIALIZED_CONTENT_FIELDS as RUNTIME_SERIALIZED_CONTENT_FIELDS,
    WRITTEN_CONTENT_FIELDS as RUNTIME_WRITTEN_CONTENT_FIELDS,
)
from .profile import _detect_project_profile
from .serialization import _model_to_dict
from .tooling import (
    DEFAULT_PATH_TOOLS as RUNTIME_DEFAULT_PATH_TOOLS,
    UNTRUSTED_RESULT_TOOL_NAMES as RUNTIME_UNTRUSTED_RESULT_TOOL_NAMES,
    build_permission_policy,
    build_tool_registry,
)


class LocalToolRuntime:
    PATH_ARGUMENTS = RUNTIME_PATH_ARGUMENTS
    DISCOVERABLE_FILE_PATH_TOOLS = RUNTIME_DISCOVERABLE_FILE_PATH_TOOLS
    SERIALIZED_CONTENT_FIELDS = RUNTIME_SERIALIZED_CONTENT_FIELDS
    WRITTEN_CONTENT_FIELDS = RUNTIME_WRITTEN_CONTENT_FIELDS
    DEFAULT_PATH_TOOLS = RUNTIME_DEFAULT_PATH_TOOLS
    UNTRUSTED_RESULT_TOOL_NAMES = RUNTIME_UNTRUSTED_RESULT_TOOL_NAMES

    def __init__(self, config):
        self.config = config
        self.audit_trail = ToolAuditTrail()
        self.registry = build_tool_registry(config.kv_cache_enabled)
        self.permissions = build_permission_policy(config, self.registry, self.audit_trail)
        self.argument_normalizer = RuntimeArgumentNormalizer(config.base_dir)
        self.project_profile = _detect_project_profile(config.base_dir)
        hardware_tools.configure_media_tools(config)
        web_tools.configure_web_tools(config)
        configure_read_policy(tuple(config.protected_read_paths))
        configure_kv_store(config.kv_cache_db_path, enabled=config.kv_cache_enabled)

    def info(self) -> dict[str, object]:
        return {
            "server_name": self.config.server_name,
            "server_version": self.config.server_version,
            "transport": self.config.transport,
            "base_dir": str(self.config.base_dir),
            "encoding": self.config.encoding,
            "permissions": self.permissions.summary(),
            "detected_languages": self.project_profile["detected_languages"],
            "primary_language": self.project_profile["primary_language"],
            "tooling": self.project_profile["tooling"],
            "sandbox": {
                "backend": self.config.sandbox_backend,
                "image": self.config.sandbox_image,
                "web_allowed_domains": list(self.config.web_allowed_domains),
                "web_denied_domains": list(self.config.web_denied_domains),
                "web_block_private_networks": self.config.web_block_private_networks,
                "web_search_provider": self.config.web_search_provider,
                "web_search_configured": self.config.web_search_base_url is not None,
            },
            "media_input": {
                "enabled": self.config.allow_media_input,
                "vision_model": self.config.vision_model or "auto",
                "ollama_base_url": self.config.vision_ollama_base_url,
            },
            "tool_confirmation_mode": self.config.tool_confirmation_mode,
            "recent_tool_event_count": len(self.audit_trail.events),
        }

    def list_tools(self) -> list[dict[str, object]]:
        tools = [
            _model_to_dict(tool)
            for tool in self.registry.list_tools()
            if self.permissions.allows_tool(tool.name)
        ]
        if self.permissions.allows_tool("pwd"):
            tools.append(_model_to_dict(self._pwd_tool_definition()))
        return tools

    def list_ollama_tools(self) -> list[dict[str, object]]:
        tools = [
            tool.to_ollama_tool()
            for tool in self.registry.list_tools()
            if self.permissions.allows_tool(tool.name)
        ]
        if self.permissions.allows_tool("pwd"):
            tools.append(self._pwd_tool_definition().to_ollama_tool())
        return tools

    def list_prompts(self) -> list[dict[str, object]]:
        return list_prompts()

    def build_context(self) -> dict[str, object]:
        context = {
            "base_dir": str(self.config.base_dir),
            "encoding": self.config.encoding,
            "permissions": self.permissions.summary(),
            "available_tools": [tool["name"] for tool in self.list_tools()],
            "tool_categories": {
                tool["name"]: tool["category"]
                for tool in self.list_tools()
                if isinstance(tool.get("name"), str)
                and isinstance(tool.get("category"), str)
            },
            "detected_languages": self.project_profile["detected_languages"],
            "primary_language": self.project_profile["primary_language"],
            "tooling": self.project_profile["tooling"],
            "sandbox": {
                "backend": self.config.sandbox_backend,
                "web_allowed_domains": list(self.config.web_allowed_domains),
                "web_denied_domains": list(self.config.web_denied_domains),
                "web_block_private_networks": self.config.web_block_private_networks,
                "web_search_provider": self.config.web_search_provider,
                "web_search_configured": self.config.web_search_base_url is not None,
            },
            "media_input": {
                "enabled": self.config.allow_media_input,
                "vision_model": self.config.vision_model or "auto",
                "ollama_base_url": self.config.vision_ollama_base_url,
            },
            "tool_confirmation": {
                "mode": self.config.tool_confirmation_mode,
                "required_tools": sorted(self.permissions.confirmation_required_tools),
                "approved_tools": sorted(self.permissions.approved_sensitive_tools),
            },
            "untrusted_tools": sorted(self.UNTRUSTED_RESULT_TOOL_NAMES),
            "location_hint": (
                "Las referencias como 'aqui', 'aca', 'esta carpeta' o "
                "'directorio actual' se refieren a base_dir."
            ),
        }
        return AgentExecutionContext.from_runtime_context(context).to_wire()

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        if name != "pwd" and not self.registry.has_tool(name):
            return {
                "success": False,
                "result": None,
                "error": f"Herramienta no encontrada: {name}",
            }

        started_at = perf_counter()
        request = None
        try:
            normalized_arguments = self.argument_normalizer.normalize(name, arguments or {})
            if name in self.DEFAULT_PATH_TOOLS and "path" not in normalized_arguments:
                normalized_arguments["path"] = str(self.config.base_dir)
            if name == "deletedir":
                target = self.argument_normalizer.resolve_user_path(
                    str(normalized_arguments.get("path") or "")
                )
                if Path(target).resolve() == self.config.base_dir.resolve():
                    raise PermissionError("deletedir no puede eliminar BASE_DIR completo.")
                normalized_arguments["path"] = target

            request = self.permissions.build_request(
                name,
                normalized_arguments,
                base_dir=self.config.base_dir,
            )
            self.permissions.before_tool(request)

            if name == "pwd":
                raw_result = {
                    "success": True,
                    "result": str(self.config.base_dir),
                    "error": None,
                }
            else:
                raw_result = _model_to_dict(
                    self.registry.execute(
                        RuntimeToolCall(name=name, arguments=normalized_arguments)
                    )
                )
            raw_result = self._annotate_tool_result(name, raw_result)
        except Exception as exc:
            raw_result = self._tool_error_result(name, exc)

        if request is not None:
            event = ToolExecutionEvent(
                request=request,
                success=bool(raw_result.get("success")),
                result=raw_result.get("result"),
                error=raw_result.get("error"),
                duration_ms=(perf_counter() - started_at) * 1000,
            )
            self.permissions.after_tool(event)
        return raw_result

    def render_prompt(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        normalized_arguments = self.argument_normalizer.normalize("", arguments or {})
        prompt_text = render_prompt(name, **normalized_arguments)
        return {
            "success": True,
            "name": name,
            "prompt": prompt_text,
        }

    def _pwd_tool_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="pwd",
            category=META,
            description=(
                "Devuelve la carpeta base actual del cliente. "
                "Usala cuando el usuario diga 'aqui', 'esta carpeta' o necesites "
                "confirmar la ubicacion de trabajo."
            ),
            parameters=[],
        )

    def recent_tool_events(self, limit: int = 20) -> list[dict[str, object]]:
        return self.audit_trail.snapshot(limit=limit)

    def _annotate_tool_result(
        self,
        name: str,
        raw_result: dict[str, Any],
    ) -> dict[str, Any]:
        if name in self.UNTRUSTED_RESULT_TOOL_NAMES:
            raw_result.setdefault("untrusted", True)
        return raw_result

    @staticmethod
    def _tool_error_result(name: str, exc: Exception) -> dict[str, Any]:
        from ..security import ToolApprovalRequiredError

        payload = {
            "success": False,
            "result": None,
            "error": str(exc),
        }
        if isinstance(exc, ToolApprovalRequiredError):
            payload["error_code"] = "approval_required"
            payload["requires_confirmation"] = True
            payload["tool_name"] = name
        elif isinstance(exc, PermissionError):
            payload["error_code"] = "permission_denied"
        else:
            payload["error_code"] = "tool_error"
        return payload
