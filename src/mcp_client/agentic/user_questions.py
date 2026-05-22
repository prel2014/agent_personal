from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


OPTION_RE = re.compile(
    r"^\s*(?:[-*+]\s+|\d+[\.)]\s+|[A-Za-z][\.)]\s+|\[[ xX]\]\s+)(?P<option>.+?)\s*$"
)
QUESTION_MARKERS = (
    "necesito que confirmes",
    "necesito confirmar",
    "confirmacion",
    "pregunta:",
    "elige",
    "selecciona",
    "escoge",
    "que prefieres",
    "cual prefieres",
    "cual opcion",
    "aclaracion",
    "confirmas",
)
QUESTION_ACTIVATION_MARKERS = (
    "motivo: falta_informacion",
    "motivo: informacion_faltante",
    "motivo: decision_usuario",
    "motivo: orden_explicita",
    "motivo: aprobacion_requerida",
    "motivo: bloqueo",
    "falta informacion",
    "informacion faltante",
    "no puedo continuar sin",
    "necesito una decision",
    "necesito que confirmes",
    "necesito confirmar",
    "aprobacion requerida",
)
OPTION_SELECTION_MARKERS = (
    "elige una opcion",
    "elige una de estas opciones",
    "elige una alternativa",
    "selecciona una opcion",
    "selecciona una de estas opciones",
    "escoge una opcion",
    "escoge una de estas opciones",
    "que opcion prefieres",
    "cual opcion prefieres",
    "cual opcion eliges",
    "elige",
    "selecciona",
    "escoge",
    "opciones:",
    "alternativas:",
)


@dataclass(frozen=True)
class UserQuestion:
    text: str
    options: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "text": self.text,
            "options": list(self.options),
        }


def detect_user_question(text: str) -> UserQuestion | None:
    normalized = (text or "").strip()
    if not normalized:
        return None

    options = extract_user_options(normalized)
    lowered = _strip_accents(normalized.lower())
    has_question_signal = any(marker in lowered for marker in QUESTION_MARKERS)
    has_activation_signal = any(
        marker in lowered for marker in QUESTION_ACTIVATION_MARKERS
    )

    # A normal assistant answer can end with "en que puedo ayudarte?".
    # Only surface an interactive prompt when the assistant used the explicit
    # confirmation/options protocol and declared why user input is required.
    if options and has_question_signal and has_activation_signal:
        return UserQuestion(text=normalized, options=options)
    if _looks_like_formal_question(lowered) and has_activation_signal:
        return UserQuestion(text=normalized, options=options)

    return None


def extract_user_options(text: str) -> list[str]:
    candidate_options: list[str] = []
    non_option_lines: list[str] = []
    for line in text.splitlines():
        match = OPTION_RE.match(line)
        if not match:
            stripped = line.strip()
            if stripped:
                non_option_lines.append(stripped)
            continue
        option = match.group("option").strip()
        if option:
            candidate_options.append(option)

    if len(candidate_options) < 2:
        return []

    intro_text = _strip_accents("\n".join(non_option_lines).lower())
    if any(marker in intro_text for marker in OPTION_SELECTION_MARKERS):
        return candidate_options

    return []


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _looks_like_formal_question(lowered_text: str) -> bool:
    formal_markers = (
        "confirmacion",
        "pregunta:",
        "necesito que confirmes",
        "necesito confirmar",
        "aclaracion requerida",
    )
    return any(marker in lowered_text for marker in formal_markers)
