from __future__ import annotations

from collections.abc import Mapping
from typing import Any


PROCESS_EXIT_CODE_KEYS = ("returncode", "exit_code")


def tool_effective_success(result: Mapping[str, Any]) -> bool:
    if not bool(result.get("success")):
        return False

    payload = result.get("result")
    if isinstance(payload, Mapping) and _nested_payload_failed(payload):
        return False

    return True


def tool_effective_error(result: Mapping[str, Any]) -> str | None:
    if not bool(result.get("success")):
        error = result.get("error")
        return str(error) if error else "error"

    payload = result.get("result")
    if isinstance(payload, Mapping) and _nested_payload_failed(payload):
        return process_failure_summary(payload)

    error = result.get("error")
    return str(error) if error else None


def process_failure_summary(
    payload: Mapping[str, Any],
    *,
    detail_limit: int = 500,
) -> str:
    exit_code = _exit_code(payload)
    detail = _first_text(payload, ("stderr", "stdout", "error"), limit=detail_limit)

    if exit_code is not None and detail:
        key, value = exit_code
        return f"proceso termino con {key} {value}: {detail}"
    if exit_code is not None:
        key, value = exit_code
        return f"proceso termino con {key} {value}"
    if detail:
        return detail
    return "proceso termino sin exito"


def _nested_payload_failed(payload: Mapping[str, Any]) -> bool:
    if payload.get("success") is False:
        return True

    exit_code = _exit_code(payload)
    return exit_code is not None and exit_code[1] != 0


def _exit_code(payload: Mapping[str, Any]) -> tuple[str, int] | None:
    for key in PROCESS_EXIT_CODE_KEYS:
        value = payload.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return key, value
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                continue
            try:
                return key, int(stripped)
            except ValueError:
                continue
    return None


def _first_text(
    payload: Mapping[str, Any],
    keys: tuple[str, ...],
    *,
    limit: int,
) -> str | None:
    for key in keys:
        value = payload.get(key)
        if not isinstance(value, str):
            continue
        text = " ".join(value.strip().split())
        if not text:
            continue
        if len(text) > limit:
            return text[: limit - 3] + "..."
        return text
    return None
