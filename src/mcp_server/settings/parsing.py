from __future__ import annotations

import os


def parse_think(raw_value: str | None) -> str | bool | None:
    value = raw_value if raw_value is not None else os.getenv("OLLAMA_THINK")
    if value is None or value == "":
        return None

    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False
    if normalized in {"low", "medium", "high"}:
        return normalized

    raise ValueError(f"Valor invalido para think: {value}")


def parse_csv_values(raw_value: str | None) -> tuple[str, ...]:
    if raw_value is None:
        return ()

    items = [
        item.strip()
        for item in raw_value.split(",")
        if item.strip()
    ]
    return tuple(items)
