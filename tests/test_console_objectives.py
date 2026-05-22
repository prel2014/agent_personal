from __future__ import annotations

import asyncio

from src.mcp_client.console.input import (
    _insert_objective_text,
    _objectives_shortcut_sequences,
)
from src.mcp_client.console.objectives import (
    format_objectives_prompt,
    read_objectives_panel_async,
)


def test_objectives_shortcut_supports_common_sequences_and_fallbacks() -> None:
    sequences = _objectives_shortcut_sequences()

    assert ("f2",) in sequences
    assert ("c-o",) in sequences
    assert ("escape", "enter") in sequences
    assert ("escape", "[", "1", "3", ";", "7", "u") in sequences
    assert ("escape", "[", "2", "7", ";", "7", ";", "1", "3", "~") in sequences


def test_read_objectives_panel_async_uses_async_dialogs() -> None:
    factory = FakeInputDialogFactory([
        "Mejorar el sistema de inventario",
        " validar stock minimo ",
        "generar reporte semanal",
        "",
    ])

    text = asyncio.run(read_objectives_panel_async(factory))

    assert text == (
        "Objetivo general:\n"
        "Mejorar el sistema de inventario\n"
        "\n"
        "Objetivos especificos:\n"
        "1. validar stock minimo\n"
        "2. generar reporte semanal"
    )
    assert [call["title"] for call in factory.calls] == [
        "Objetivos",
        "Objetivos especificos",
        "Objetivos especificos",
        "Objetivos especificos",
    ]


def test_read_objectives_panel_async_returns_none_when_general_cancelled() -> None:
    factory = FakeInputDialogFactory([None])

    assert asyncio.run(read_objectives_panel_async(factory)) is None


def test_insert_objective_text_appends_to_existing_buffer() -> None:
    buffer = FakeBuffer("hola")

    _insert_objective_text(buffer, "Objetivo general:\nX")

    assert buffer.text == "hola\n\nObjetivo general:\nX"


def test_insert_objective_text_ignores_empty_result() -> None:
    buffer = FakeBuffer("hola")

    _insert_objective_text(buffer, None)

    assert buffer.text == "hola"


def test_format_objectives_prompt_numbers_specific_objectives() -> None:
    text = format_objectives_prompt(
        "Mejorar el sistema de inventario",
        [
            "validar stock minimo",
            "generar reporte semanal",
        ],
    )

    assert text == (
        "Objetivo general:\n"
        "Mejorar el sistema de inventario\n"
        "\n"
        "Objetivos especificos:\n"
        "1. validar stock minimo\n"
        "2. generar reporte semanal"
    )


def test_format_objectives_prompt_leaves_first_number_when_no_specifics() -> None:
    text = format_objectives_prompt("Investigar ventas", [])

    assert text.endswith("Objetivos especificos:\n1.")


class FakeInputDialogFactory:
    def __init__(self, values: list[str | None]) -> None:
        self.values = values
        self.calls: list[dict[str, object]] = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return FakeDialog(self.values.pop(0))


class FakeDialog:
    def __init__(self, value: str | None) -> None:
        self.value = value

    async def run_async(self) -> str | None:
        return self.value


class FakeBuffer:
    def __init__(self, text: str = "") -> None:
        self.text = text

    def insert_text(self, value: str) -> None:
        self.text += value
