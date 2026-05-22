from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import _detect_newline

WRITE_PREVIEW_LIMIT = 240

def read_lines(path: str, start: int, end: int) -> dict[str, Any]:
    if start < 1:
        raise ValueError("'start' debe ser mayor o igual a 1.")
    if end < start:
        raise ValueError("'end' debe ser mayor o igual a 'start'.")

    file_path = Path(path)
    lines = file_path.read_text(encoding="utf-8").splitlines()
    selected = lines[start - 1:end]

    return {
        "path": str(file_path),
        "start": start,
        "end": end,
        "content": "\n".join(selected),
        "lines": [
            {
                "number": start + index,
                "text": line,
            }
            for index, line in enumerate(selected)
        ],
    }

def replace_in_file(path: str, old: str, new: str, count: int = 0) -> dict[str, Any]:
    file_path = Path(path)
    original = file_path.read_text(encoding="utf-8")
    occurrences = original.count(old)

    if occurrences == 0:
        raise ValueError("No se encontro el texto a reemplazar en el archivo.")

    if count < 0:
        raise ValueError("'count' no puede ser negativo.")

    if count == 0:
        updated = original.replace(old, new)
        replaced_count = occurrences
    else:
        updated = original.replace(old, new, count)
        replaced_count = min(occurrences, count)

    file_path.write_text(updated, encoding="utf-8")
    return {
        "success": True,
        "path": str(file_path),
        "replaced_count": replaced_count,
        "characters_written": len(updated),
        "bytes_written": len(updated.encode("utf-8")),
        "content_preview": _preview(updated),
        "content_sha256": _sha256(updated),
    }

def replace_lines(path: str, start: int, end: int, content: str) -> dict[str, Any]:
    if start < 1:
        raise ValueError("'start' debe ser mayor o igual a 1.")
    if end < start:
        raise ValueError("'end' debe ser mayor o igual a 'start'.")

    file_path = Path(path)
    original = file_path.read_text(encoding="utf-8")
    newline = _detect_newline(original)
    lines = original.splitlines()

    if end > len(lines):
        raise ValueError("'end' esta fuera del rango del archivo.")

    replacement_lines = content.splitlines()
    updated_lines = lines[: start - 1] + replacement_lines + lines[end:]
    updated_text = newline.join(updated_lines)

    if original.endswith(("\n", "\r\n")):
        updated_text += newline

    file_path.write_text(updated_text, encoding="utf-8")
    return {
        "success": True,
        "path": str(file_path),
        "replaced_range": [start, end],
        "inserted_lines": len(replacement_lines),
        "characters_written": len(updated_text),
        "bytes_written": len(updated_text.encode("utf-8")),
        "content_preview": _preview(updated_text),
        "content_sha256": _sha256(updated_text),
    }


def _preview(content: str) -> str:
    preview = content[:WRITE_PREVIEW_LIMIT]
    if len(content) > WRITE_PREVIEW_LIMIT:
        preview += "..."
    return preview


def _sha256(content: str) -> str:
    import hashlib

    return hashlib.sha256(content.encode("utf-8")).hexdigest()
