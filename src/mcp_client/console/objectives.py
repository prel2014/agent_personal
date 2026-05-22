from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any


InputDialogFactory = Callable[..., Any]


def read_objectives_panel() -> str | None:
    return asyncio.run(read_objectives_panel_async())


async def read_objectives_panel_async(
    input_dialog_factory: InputDialogFactory | None = None,
) -> str | None:
    try:
        style = _dialog_style()
    except ImportError:
        return None

    if input_dialog_factory is None:
        try:
            from prompt_toolkit.shortcuts import input_dialog as input_dialog_factory
        except ImportError:
            return None

    general = await _read_dialog_value(
        input_dialog_factory,
        title="Objetivos",
        text="Objetivo general",
        ok_text="Continuar",
        cancel_text="Cancelar",
        style=style,
    )
    if general is None:
        return None

    specifics: list[str] = []
    while True:
        number = len(specifics) + 1
        value = await _read_dialog_value(
            input_dialog_factory,
            title="Objetivos especificos",
            text=f"{number}. Objetivo especifico (Enter agrega; vacio termina)",
            ok_text="Agregar",
            cancel_text="Terminar",
            style=style,
        )
        if value is None:
            break

        stripped = " ".join(value.split())
        if not stripped:
            break
        specifics.append(stripped)

    return format_objectives_prompt(general, specifics)


async def _read_dialog_value(
    input_dialog_factory: InputDialogFactory,
    **kwargs: Any,
) -> str | None:
    dialog = input_dialog_factory(**kwargs)
    return await dialog.run_async()


def _dialog_style():
    from prompt_toolkit.styles import Style

    return Style.from_dict(
        {
            "dialog": "bg:#202020",
            "dialog frame-label": "bg:#202020 #9cdcfe bold",
            "dialog.body": "bg:#202020 #d0d0d0",
            "button": "bg:#303030 #d0d0d0",
            "button.focused": "bg:#264f78 #ffffff bold",
            "text-area": "bg:#111111 #ffffff",
            "text-area.focused": "bg:#111111 #ffffff",
        }
    )


def format_objectives_prompt(general: str, specifics: list[str]) -> str:
    lines = [
        "Objetivo general:",
        general.strip(),
        "",
        "Objetivos especificos:",
    ]
    cleaned_specifics = [" ".join(item.split()) for item in specifics if item.strip()]
    if cleaned_specifics:
        lines.extend(
            f"{index}. {item}"
            for index, item in enumerate(cleaned_specifics, start=1)
        )
    else:
        lines.append("1. ")

    return "\n".join(lines).rstrip()
