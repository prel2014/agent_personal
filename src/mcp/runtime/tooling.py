from __future__ import annotations

from typing import Any

from ..security import PermissionPolicy, ToolAuditTrail
from ..tools.registry import ToolRegistry
from src.mcp_shared.agent_contracts import (
    DELETE,
    EXECUTE,
    HARDWARE,
    MEDIA_INPUT,
    META,
    SANDBOX_EXECUTE,
    WRITE,
)
from ..tools.helpers.code_tools import registry as code_registry
from ..tools.helpers.git_tools import registry as git_registry
from ..tools.helpers.hardware_tools import registry as hardware_registry
from ..tools.helpers.kv_tools import registry as kv_registry
from ..tools.helpers.system_tools import registry as system_registry
from ..tools.helpers.web_tools import registry as web_registry
from ..tools.helpers.data_tools import registry as data_registry

DEFAULT_PATH_TOOLS = {
    "listdir",
    "search_code",
    "find_files",
    "list_tree",
    "find_definition",
    "find_references",
    "run_module",
    "python",
    "python_interpreter",
    "run_tests",
    "lint_python",
    "format_python",
    "node_run_script",
    "node_test",
    "node_lint",
    "node_format",
    "ts_typecheck",
    "dotnet_restore",
    "dotnet_build",
    "dotnet_test",
    "dotnet_run",
    "git_status",
    "git_diff",
    "git_log",
    "git_show",
    "git_branches",
    "git_ls_files",
}

UNTRUSTED_RESULT_TOOL_NAMES = {
    "readfile",
    "read_lines",
    "search_code",
    "find_files",
    "list_tree",
    "get_python_symbols",
    "find_definition",
    "find_references",
    "extract_imports",
    "git_status",
    "git_diff",
    "git_log",
    "git_show",
    "git_branches",
    "git_blame",
    "git_ls_files",
    "kv_get",
    "kv_list",
    "web_search",
    "web_fetch",
    "determinar_tipo_dato",
}


def build_tool_registry(kv_cache_enabled: bool) -> ToolRegistry:
    registry = ToolRegistry()
    registry.extend(system_registry)
    registry.extend(code_registry)
    registry.extend(git_registry)
    if kv_cache_enabled:
        registry.extend(kv_registry)
    registry.extend(hardware_registry)
    registry.extend(web_registry)
    registry.extend(data_registry)
    return registry


def build_permission_policy(
    config: Any,
    registry: ToolRegistry,
    audit_trail: ToolAuditTrail,
) -> PermissionPolicy:
    tool_categories = registry.category_map()
    tool_categories["pwd"] = META
    confirmation_required_tools = (
        confirmation_required_tool_names(tool_categories)
        if config.tool_confirmation_mode == "sensitive"
        else frozenset()
    )
    return PermissionPolicy(
        allow_read=config.allow_read,
        allow_write=config.allow_write,
        allow_execute=config.allow_execute,
        allow_delete=config.allow_delete,
        allow_hardware=config.allow_hardware,
        allow_media_input=config.allow_media_input,
        allow_web=config.allow_web,
        allow_sandbox_execute=config.allow_sandbox_execute,
        allowed_tools=frozenset(config.allowed_tools) if config.allowed_tools else None,
        blocked_tools=frozenset(config.blocked_tools),
        protected_path_patterns=tuple(config.protected_paths),
        protected_read_path_patterns=tuple(config.protected_read_paths),
        confirmation_required_tools=confirmation_required_tools,
        approved_sensitive_tools=frozenset(config.approved_sensitive_tools),
        tool_hooks=(audit_trail,),
        tool_categories=tool_categories,
    )


def confirmation_required_tool_names(tool_categories: dict[str, str]) -> frozenset[str]:
    sensitive_categories = {
        WRITE,
        EXECUTE,
        DELETE,
        HARDWARE,
        MEDIA_INPUT,
        SANDBOX_EXECUTE,
    }
    return frozenset(
        name
        for name, category in tool_categories.items()
        if category in sensitive_categories
    )
