from __future__ import annotations

from src.mcp_shared.contracts import ChatMessage

from .context_meter import estimate_tokens

TRIM_NOTE = "[Contexto anterior omitido para caber en la ventana del modelo.]"


def trim_messages(
    messages: list[ChatMessage],
    *,
    max_tokens: int,
    ratio: float = 0.75,
    min_turns: int = 2,
) -> tuple[list[ChatMessage], bool]:
    """
    Devuelve (lista_recortada, fue_recortado).
    No modifica la lista original.
    Garantía: siempre corta en fronteras de turno de usuario, nunca a mitad de un
    ciclo assistant→tool.
    """
    if not messages:
        return messages, False

    threshold = int(max_tokens * ratio)
    if estimate_tokens([m.to_wire() for m in messages]) <= threshold:
        return messages, False

    # Detectar resumen anclado: primer mensaje assistant generado por /session compact.
    if messages[0].role == "assistant":
        pinned = [messages[0]]
        body = messages[1:]
    else:
        pinned = []
        body = messages

    turn_starts = [i for i, m in enumerate(body) if m.role == "user"]

    if len(turn_starts) <= min_turns:
        return messages, False

    trim_note_msg = ChatMessage.assistant(content=TRIM_NOTE)

    # Probar drop_n = 1, 2, ... hasta encontrar el mínimo que cabe.
    max_to_drop = len(turn_starts) - min_turns
    for drop_n in range(1, max_to_drop + 1):
        keep_from = turn_starts[drop_n]
        candidate = pinned + body[keep_from:]
        if estimate_tokens([m.to_wire() for m in candidate]) <= threshold:
            return pinned + [trim_note_msg] + body[keep_from:], True

    # Fallback: conservar sólo min_turns turnos más recientes.
    keep_from = turn_starts[-min_turns]
    return pinned + [trim_note_msg] + body[keep_from:], True
