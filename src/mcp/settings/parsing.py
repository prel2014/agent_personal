from pathlib import Path


def resolve_base_dir(raw_value: str | None) -> Path:
    candidate = Path(raw_value).expanduser() if raw_value else Path.cwd()
    resolved = candidate.resolve()

    if not resolved.exists():
        raise ValueError(f"BASE_DIR no existe: {resolved}")

    if not resolved.is_dir():
        raise ValueError(f"BASE_DIR no es una carpeta: {resolved}")

    return resolved


def parse_tool_list(raw_value: str | None) -> tuple[str, ...] | None:
    if raw_value is None:
        return None

    items = tuple(
        item.strip()
        for item in raw_value.split(",")
        if item.strip()
    )
    return items or None


def parse_required_csv_values(raw_value: str | None) -> tuple[str, ...]:
    return parse_tool_list(raw_value) or ()
