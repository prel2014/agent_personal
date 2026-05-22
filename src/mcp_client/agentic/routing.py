from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Literal

from src.mcp_shared.contracts import ChatResponse

from ..prompts import build_routing_classifier_prompt
from .ports import OrchestratorPort, ToolRuntimePort


RouteName = Literal["direct", "team"]


TEAM_KEYWORDS = (
    "agrega",
    "anade",
    "arregla",
    "busca",
    "cambia",
    "corrige",
    "crea",
    "crear",
    "debug",
    "debuggea",
    "depura",
    "edita",
    "implementa",
    "guarda",
    "guardar",
    "investiga",
    "inspecciona",
    "modifica",
    "describe",
    "describir",
    "valida",
    "validalo",
    "validar",
    "verifica",
    "verificalo",
    "verificar",
    "refactor",
    "refactoriza",
    "revisa",
    "test",
    "tests",
)
DIRECT_PREFIXES = (
    "hola",
    "buenas",
    "gracias",
    "que es",
    "como uso",
    "explica",
    "explicame",
    "translate",
    "traduce",
)
WRITE_SIGNALS = (
    "analiza",
    "analisis",
    "analysis",
    "archivo",
    "archivos",
    "carpeta",
    "c++",
    "cpp",
    "codigo",
    "dependencia",
    "dependencias",
    "repo",
    "repositorio",
    "proyect",
    "proyecto",
    "tool",
    "tools",
    "docker",
    "historia",
    "historias",
    "serial",
    "texto",
    "txt",
    "web",
    "camara",
    "foto",
    "fotos",
    "imagen",
    "imagenes",
    "imágenes",
    "imagens",
    "image",
    "images",
    "jpg",
    "jpeg",
    "png",
    "webp",
    "vision",
    "visión",
)


@dataclass(frozen=True)
class RouteDecision:
    route: RouteName
    reason: str
    confidence: float
    signals: list[str] = field(default_factory=list)
    source: str = "heuristic"


@dataclass
class PlanningRouter:
    api: OrchestratorPort
    runtime: ToolRuntimePort

    def decide(
        self,
        prompt: str,
        messages: list[dict[str, Any]] | None = None,
    ) -> RouteDecision:
        heuristic = self._heuristic_decision(prompt, messages or [])
        if heuristic is not None:
            return heuristic

        return self._classifier_decision(prompt, messages or [])

    def _heuristic_decision(
        self,
        prompt: str,
        messages: list[dict[str, Any]],
    ) -> RouteDecision | None:
        normalized = _normalize(prompt)
        words = _words(normalized)
        signals: list[str] = []

        if any(keyword in normalized for keyword in TEAM_KEYWORDS):
            signals.append("team_keyword")
        if any(signal in normalized for signal in WRITE_SIGNALS):
            signals.append("workspace_or_tool_signal")
        if "?" in prompt and len(words) <= 12 and not signals:
            return RouteDecision(
                route="direct",
                reason="pregunta corta sin señales de trabajo multi-paso",
                confidence=0.9,
                signals=["short_question"],
            )
        if (
            any(normalized.startswith(prefix) for prefix in DIRECT_PREFIXES)
            and len(words) <= 18
            and not signals
        ):
            return RouteDecision(
                route="direct",
                reason="consulta simple o conversacional",
                confidence=0.9,
                signals=["direct_prefix"],
            )
        if signals:
            return RouteDecision(
                route="team",
                reason="requiere inspeccion, cambios, busqueda o uso de tools",
                confidence=0.85,
                signals=signals,
            )
        if len(words) <= 5:
            return RouteDecision(
                route="direct",
                reason="prompt muy corto sin señales de trabajo",
                confidence=0.75,
                signals=["very_short"],
            )
        return None

    def _classifier_decision(
        self,
        prompt: str,
        messages: list[dict[str, Any]],
    ) -> RouteDecision:
        classifier_prompt = build_routing_classifier_prompt(prompt)
        try:
            response = ChatResponse.from_wire(
                self.api.chat(
                    messages=[*messages, {"role": "user", "content": classifier_prompt}],
                    tools=[],
                    client_context={
                        **self.runtime.build_context(),
                        "routing_task": "planning_mode_classifier",
                    },
                )
            )
            raw = response.message.content.strip()
            payload = _extract_json_object(raw)
            route = payload.get("route")
            if route not in {"direct", "team"}:
                raise ValueError("route invalido")
            return RouteDecision(
                route=route,
                reason=str(payload.get("reason") or "clasificador LLM"),
                confidence=float(payload.get("confidence") or 0.6),
                signals=["llm_classifier"],
                source="llm",
            )
        except Exception as exc:
            return RouteDecision(
                route="team",
                reason=f"clasificador no disponible; fallback conservador: {exc}",
                confidence=0.5,
                signals=["classifier_failed"],
                source="fallback",
            )


def _normalize(value: str) -> str:
    return " ".join(value.casefold().strip().split())


def _words(value: str) -> list[str]:
    return re.findall(r"[\wáéíóúñü]+", value, flags=re.IGNORECASE)


def _extract_json_object(value: str) -> dict[str, Any]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        start = value.find("{")
        end = value.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        payload = json.loads(value[start : end + 1])

    if not isinstance(payload, dict):
        raise ValueError("El clasificador no devolvio un objeto JSON.")
    return payload
