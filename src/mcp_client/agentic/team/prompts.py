from __future__ import annotations

import json

from ..roles import WORKER_DIRECTIVE
from ..state import AgentRunResult


def build_worker_directive(plan_summary: str) -> str:
    return (
        f"{WORKER_DIRECTIVE}\n\n"
        "Plan del planner:\n"
        f"{plan_summary}\n\n"
        "Sigue ese plan salvo que el codigo real te obligue a ajustarlo. "
        "Si el planner incluyo una pregunta al usuario, tratala como una incertidumbre "
        "a resolver con inspeccion o una suposicion explicita, no como un bloqueo."
    )


def build_worker_retry_prompt(review_feedback: str) -> str:
    return (
        "El reviewer encontro estos hallazgos concretos:\n"
        f"{review_feedback}\n\n"
        "Corrigelos sobre el trabajo ya realizado y entrega una respuesta final actualizada."
    )


def build_review_prompt(
    *,
    original_prompt: str,
    plan_summary: str,
    worker_result: AgentRunResult,
) -> str:
    auto_written_files = ", ".join(worker_result.auto_written_files) or "(ninguno)"
    tool_activity = _summarize_tool_activity(worker_result)
    return (
        "Revisa el trabajo del worker.\n\n"
        "Solicitud original:\n"
        f"{original_prompt}\n\n"
        "Plan del planner:\n"
        f"{plan_summary}\n\n"
        "Respuesta final del worker:\n"
        f"{worker_result.final}\n\n"
        "Archivos escritos por auto-write Markdown:\n"
        f"{auto_written_files}\n\n"
        "Resultados relevantes de tools ejecutadas por el worker:\n"
        f"{tool_activity}\n\n"
        "Nota: writefile, replace_in_file, replace_lines, movefile, appendfile, "
        "deletefile y deletedir son evidencia real de cambios aunque auto-write "
        "Markdown diga ninguno.\n\n"
        "Si no encuentras problemas, empieza con APROBADO. "
        "Si encuentras problemas concretos, empieza con REQUIERE_CAMBIOS."
    )


def _summarize_tool_activity(worker_result: AgentRunResult) -> str:
    lines: list[str] = []
    for message in worker_result.memory.messages:
        if message.role != "tool":
            continue
        tool_name = message.tool_name or "tool"
        try:
            payload = json.loads(message.content)
        except json.JSONDecodeError:
            lines.append(f"- {tool_name}: resultado no JSON")
            continue
        if not isinstance(payload, dict):
            lines.append(f"- {tool_name}: {type(payload).__name__}")
            continue
        if payload.get("success") is False:
            lines.append(f"- {tool_name}: ERROR {payload.get('error') or 'error'}")
            continue

        result = payload.get("result")
        if isinstance(result, dict):
            lines.append(_summarize_tool_result_dict(tool_name, result))
        else:
            preview = str(result)
            if len(preview) > 180:
                preview = preview[:177] + "..."
            lines.append(f"- {tool_name}: ok {preview}")

    return "\n".join(lines) if lines else "(sin resultados de tools)"


def _summarize_tool_result_dict(tool_name: str, result: dict[str, object]) -> str:
    path = result.get("path")
    target_path = result.get("target_path")
    operation = result.get("operation") or tool_name
    parts = [f"- {tool_name}: ok", f"operation={operation}"]
    if path:
        parts.append(f"path={path}")
    if target_path:
        parts.append(f"target_path={target_path}")
    for key in (
        "mode",
        "bytes_written",
        "written_bytes",
        "bytes_moved",
        "removed_files",
        "removed_dirs",
        "content_sha256",
    ):
        value = result.get(key)
        if value is not None:
            parts.append(f"{key}={value}")
    return " ".join(parts)
