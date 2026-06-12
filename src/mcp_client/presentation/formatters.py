from __future__ import annotations

import json
from typing import Any

from ..tool_results import tool_effective_error, tool_effective_success


def preview(value: str, limit: int = 160) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def format_tool_call(name: str, arguments: dict[str, Any], *, detailed: bool) -> str:
    if not arguments:
        return name
    if detailed:
        return f"{name} args={json.dumps(arguments, ensure_ascii=False)}"

    for key in ("path", "file_path", "cwd", "url", "query", "command"):
        value = arguments.get(key)
        if isinstance(value, str) and value:
            return f"{name} {key}={value}"
    return name


def format_tool_result(name: str, result: dict[str, Any], *, detailed: bool) -> str:
    if detailed:
        return f"{name}: {preview(json.dumps(result, ensure_ascii=False), 500)}"

    if not tool_effective_success(result):
        error = tool_effective_error(result) or "error"
        return f"{name} error: {preview(error, 120)}"

    payload = result.get("result")
    if isinstance(payload, str) and payload.strip().startswith("["):
        try:
            items = json.loads(payload)
        except json.JSONDecodeError:
            items = None
        if isinstance(items, list):
            suffix = "" if len(items) == 1 else "s"
            preview_items = ", ".join(str(item) for item in items[:5])
            if len(items) > 5:
                preview_items += f", +{len(items) - 5} mas"
            return f"{name} ok ({len(items)} elemento{suffix}: {preview_items})"

    if isinstance(payload, dict):
        path = payload.get("path") or payload.get("saved_frame_path")
        target_path = payload.get("target_path")
        operation = payload.get("operation")
        bytes_written = payload.get("bytes_written")
        if path and operation:
            detail = (
                f"{operation} {path} -> {target_path}"
                if target_path
                else f"{operation} {path}"
            )
            if isinstance(bytes_written, int):
                detail += f" ({bytes_written} bytes)"
            bytes_moved = payload.get("bytes_moved")
            if isinstance(bytes_moved, int):
                detail += f" ({bytes_moved} bytes)"
            removed_files = payload.get("removed_files")
            removed_dirs = payload.get("removed_dirs")
            if isinstance(removed_files, int) or isinstance(removed_dirs, int):
                detail += (
                    f" ({removed_files or 0} archivos, {removed_dirs or 0} carpetas)"
                )
            return detail

    if payload in ("ok", True, None):
        return f"{name} ok"

    return f"{name} ok: {preview(json.dumps(payload, ensure_ascii=False), 120)}"
