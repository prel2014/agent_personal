from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.mcp_client.agentic.context_window import TRIM_NOTE, trim_messages
from src.mcp_shared.contracts import ChatMessage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user(text: str = "pregunta") -> ChatMessage:
    return ChatMessage.user(text)


def _assistant(text: str = "respuesta") -> ChatMessage:
    return ChatMessage.assistant(content=text)


def _tool(name: str = "t", text: str = "resultado") -> ChatMessage:
    return ChatMessage.tool_result(name, text)


def _build_turns(n: int) -> list[ChatMessage]:
    """Genera n turnos completos: user + assistant."""
    msgs = []
    for i in range(n):
        msgs.append(_user(f"pregunta {i}"))
        msgs.append(_assistant(f"respuesta {i}"))
    return msgs


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_no_trim_when_under_threshold() -> None:
    msgs = _build_turns(3)
    # Forzar tokens estimados pequeños usando un threshold grande.
    result, trimmed = trim_messages(msgs, max_tokens=10_000_000, ratio=0.75)
    assert trimmed is False
    assert result is msgs  # misma lista, sin copiar


def test_trim_drops_oldest_turn() -> None:
    # Construir 4 turnos; simular threshold mínimo para forzar el trim.
    msgs = _build_turns(4)
    with patch(
        "src.mcp_client.agentic.context_window.estimate_tokens",
        side_effect=[1000, 200],  # primera llamada: supera; segunda (candidato): cabe
    ):
        result, trimmed = trim_messages(msgs, max_tokens=1000, ratio=0.75, min_turns=2)

    assert trimmed is True
    # Se descartó el turno 0; quedan turnos 1, 2, 3 → 3 user messages.
    user_msgs = [m for m in result if m.role == "user"]
    assert len(user_msgs) == 3
    assert user_msgs[0].content == "pregunta 1"


def test_trims_multiple_turns_if_needed() -> None:
    msgs = _build_turns(5)
    # side_effect: primera evaluación excede; los dos siguientes candidatos también
    # exceden; el cuarto candidato cabe.
    with patch(
        "src.mcp_client.agentic.context_window.estimate_tokens",
        side_effect=[1000, 900, 800, 200],
    ):
        result, trimmed = trim_messages(msgs, max_tokens=1000, ratio=0.75, min_turns=2)

    assert trimmed is True
    user_msgs = [m for m in result if m.role == "user"]
    assert len(user_msgs) == 2


def test_preserves_pinned_summary() -> None:
    summary = _assistant("Este es el resumen anclado de la sesión.")
    msgs = [summary] + _build_turns(4)
    with patch(
        "src.mcp_client.agentic.context_window.estimate_tokens",
        side_effect=[1000, 200],
    ):
        result, trimmed = trim_messages(msgs, max_tokens=1000, ratio=0.75, min_turns=2)

    assert trimmed is True
    assert result[0].content == summary.content
    assert result[0].role == "assistant"


def test_respects_min_turns_no_trim() -> None:
    msgs = _build_turns(2)  # exactamente min_turns=2 → no se puede recortar
    with patch(
        "src.mcp_client.agentic.context_window.estimate_tokens",
        return_value=9999,  # siempre excede
    ):
        result, trimmed = trim_messages(msgs, max_tokens=100, ratio=0.75, min_turns=2)

    assert trimmed is False
    assert result is msgs


def test_adds_trim_note_when_trimming() -> None:
    msgs = _build_turns(4)
    with patch(
        "src.mcp_client.agentic.context_window.estimate_tokens",
        side_effect=[1000, 200],
    ):
        result, trimmed = trim_messages(msgs, max_tokens=1000, ratio=0.75, min_turns=2)

    assert trimmed is True
    # La nota debe estar en los mensajes y ser un assistant
    notes = [m for m in result if TRIM_NOTE in (m.content or "")]
    assert len(notes) == 1
    assert notes[0].role == "assistant"


def test_keeps_tool_pairs_intact() -> None:
    """Cortar en frontera user nunca deja un tool_result huérfano."""
    msgs = [
        _user("turno 0"),
        _assistant("respuesta con tool"),
        _tool("mi_tool", "resultado tool"),
        _user("turno 1"),
        _assistant("respuesta 1"),
        _user("turno 2"),
        _assistant("respuesta 2"),
    ]
    with patch(
        "src.mcp_client.agentic.context_window.estimate_tokens",
        side_effect=[1000, 200],
    ):
        result, trimmed = trim_messages(msgs, max_tokens=1000, ratio=0.75, min_turns=2)

    assert trimmed is True
    # No debe haber tool_result sin que haya habido un user antes
    roles = [m.role for m in result]
    for i, role in enumerate(roles):
        if role == "tool":
            assert "user" in roles[:i], "tool_result aparece antes de cualquier user"


def test_empty_messages_returns_unchanged() -> None:
    result, trimmed = trim_messages([], max_tokens=1000, ratio=0.75)
    assert trimmed is False
    assert result == []


def test_trim_uses_fallback_when_no_candidate_fits() -> None:
    """Cuando ningún candidato cabe, el fallback conserva min_turns."""
    msgs = _build_turns(4)  # 4 user turns
    # Todos los candidatos exceden el threshold → se usa fallback
    with patch(
        "src.mcp_client.agentic.context_window.estimate_tokens",
        return_value=9999,  # siempre excede
    ):
        result, trimmed = trim_messages(msgs, max_tokens=100, ratio=0.75, min_turns=2)

    assert trimmed is True
    user_msgs = [m for m in result if m.role == "user"]
    assert len(user_msgs) == 2
    notes = [m for m in result if TRIM_NOTE in (m.content or "")]
    assert len(notes) == 1
