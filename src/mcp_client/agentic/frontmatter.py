from __future__ import annotations

from pathlib import Path


def split_frontmatter(text: str) -> tuple[str, str]:
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        raise ValueError("El archivo debe iniciar con frontmatter YAML (---).")
    _, rest = normalized.split("---\n", 1)
    if "\n---\n" not in rest:
        raise ValueError("Frontmatter sin cierre ---.")
    frontmatter, body = rest.split("\n---\n", 1)
    return frontmatter, body


def parse_frontmatter(frontmatter: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in frontmatter.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            raise ValueError(f"Linea de frontmatter invalida: {line}")
        key, value = stripped.split(":", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def parse_tools(raw_tools: str | None) -> tuple[str, ...] | None:
    if raw_tools is None or raw_tools == "":
        return None
    if raw_tools in {"[]", "()"}:
        return ()
    value = raw_tools.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    tools = tuple(tool.strip().strip('"').strip("'") for tool in value.split(","))
    return tuple(tool for tool in tools if tool)
