from __future__ import annotations

from typing import Protocol


class CompactContext(Protocol):
    runtime: object
    client: object


def build_compact_prompt(focus: str) -> str:
    focus_text = (
        f"\nEnfoque solicitado por el usuario: {focus}\n"
        if focus
        else ""
    )
    return (
        "Compacta la conversacion anterior para ahorrar contexto.\n"
        "Devuelve solo un resumen operativo en espanol, sin saludo ni explicaciones.\n"
        "Conserva estrictamente lo necesario para continuar el trabajo:\n"
        "- objetivo actual del usuario\n"
        "- decisiones tomadas y restricciones importantes\n"
        "- archivos, comandos, configuracion y rutas relevantes\n"
        "- cambios ya realizados y resultados de pruebas/verificaciones\n"
        "- pendientes, riesgos, errores abiertos y siguientes pasos\n"
        "Omite charla, repeticiones y detalles que no afecten el trabajo futuro.\n"
        f"{focus_text}"
    )


def build_compact_client_context(ctx: CompactContext) -> dict[str, object]:
    runtime = getattr(ctx, "runtime")
    client = getattr(ctx, "client")
    context = dict(runtime.build_context())
    context["available_tools"] = []
    context["tool_categories"] = {}
    context["direct_answer_mode"] = True
    context["prompt_mode"] = "compact"
    context["context_window_tokens"] = client.config.context_window_tokens
    context["role_directive"] = (
        "Resume la conversacion para compactar contexto. "
        "No ejecutes herramientas ni introduzcas informacion nueva."
    )
    return context


def compacted_context_message(summary: str) -> str:
    return (
        "Resumen compactado de la conversacion anterior. "
        "Contexto persistente para continuar:\n\n"
        f"{summary}"
    )
