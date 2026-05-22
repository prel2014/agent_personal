from __future__ import annotations

import ast
import json
from typing import Any

from src.mcp_shared.markdown import strip_single_fence


CODE_FILE_SUFFIXES = {
    ".bat",
    ".c",
    ".cc",
    ".cfg",
    ".conf",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".h",
    ".hpp",
    ".html",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".kt",
    ".lua",
    ".php",
    ".ps1",
    ".py",
    ".rb",
    ".rs",
    ".sh",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".xml",
    ".yaml",
    ".yml",
}
MARKDOWN_FILE_SUFFIXES = {".md", ".mdx", ".markdown"}
MOJIBAKE_MARKERS = (
    "\u00c3",
    "\u00c2",
    "\u00e2\u20ac",
    "\u00e2\u0080",
    "\u00f0\u009f",
)
def _model_to_dict(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()

    if hasattr(model, "dict"):
        return model.dict()

    raise TypeError(f"No se puede serializar el modelo: {type(model)!r}")

def _maybe_unescape_serialized_content(value: str) -> str:
    decoded = _decode_wrapped_string(value)
    if decoded is not None:
        return decoded

    decoded = _decode_flat_escaped_text(value)
    if decoded is not None:
        return decoded

    return value

def _clean_model_written_content(value: str, *, path: str | None = None) -> str:
    decoded = _maybe_unescape_serialized_content(value)
    cleaned = _strip_single_code_fence(decoded, path=path)
    _reject_suspicious_model_content(cleaned)
    return cleaned

def _strip_single_code_fence(value: str, *, path: str | None = None) -> str:
    stripped = strip_single_fence(value)
    if stripped is None:
        return value

    body, language = stripped
    suffix = _path_suffix(path)
    if suffix in MARKDOWN_FILE_SUFFIXES:
        return value
    if suffix in CODE_FILE_SUFFIXES or language not in {"", "md", "markdown", "text", "txt"}:
        return body
    return value

def _reject_suspicious_model_content(value: str) -> None:
    stripped = value.strip()
    lowered = stripped.lower()
    if "<tool_code" in lowered or "</tool_code>" in lowered:
        raise ValueError(
            "Contenido rechazado: contiene wrappers <tool_code>. "
            "Reintenta enviando solo el texto que debe escribirse."
        )

    if "\ufffd" in value:
        raise ValueError(
            "Contenido rechazado: contiene caracteres de reemplazo Unicode."
        )

    marker = _first_mojibake_marker(value)
    if marker is not None:
        raise ValueError(
            f"Contenido rechazado: parece contener mojibake o texto mal decodificado ({marker!r})."
        )

    if _looks_like_tool_payload(stripped):
        raise ValueError(
            "Contenido rechazado: parece ser una llamada a tool serializada, no contenido de archivo."
        )

def _first_mojibake_marker(value: str) -> str | None:
    for marker in MOJIBAKE_MARKERS:
        if marker in value:
            return marker
    return None

def _looks_like_tool_payload(value: str) -> bool:
    if not value.startswith("{") or not value.endswith("}"):
        return False
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return False
    if not isinstance(payload, dict):
        return False
    if isinstance(payload.get("function"), dict):
        return isinstance(payload["function"].get("name"), str)
    return isinstance(payload.get("name"), str) and "arguments" in payload

def _path_suffix(path: str | None) -> str:
    if not path:
        return ""
    normalized = path.replace("\\", "/").rsplit("/", 1)[-1]
    if "." not in normalized:
        return ""
    return "." + normalized.rsplit(".", 1)[-1].lower()

def _decode_wrapped_string(value: str) -> str | None:
    stripped = value.strip()
    if len(stripped) < 2:
        return None

    if stripped.startswith('"') and stripped.endswith('"'):
        try:
            decoded = ast.literal_eval(stripped)
        except (SyntaxError, ValueError):
            return None

        if isinstance(decoded, str) and _is_better_decoded_text(value, decoded, wrapped=True):
            return decoded

        return None

    if stripped.startswith("'") and stripped.endswith("'"):
        try:
            decoded = ast.literal_eval(stripped)
        except (SyntaxError, ValueError):
            return None

        if isinstance(decoded, str) and _is_better_decoded_text(value, decoded, wrapped=True):
            return decoded

    return None

def _decode_flat_escaped_text(value: str) -> str | None:
    if "\n" in value or "\r" in value:
        return None

    escaped_newlines = value.count(r"\n") + value.count(r"\r\n")
    if escaped_newlines < 2 and r"\n    " not in value and r"\n\t" not in value:
        return None

    decoded = _decode_common_escapes(value)

    if _is_better_decoded_text(value, decoded, wrapped=False):
        return decoded

    return None

def _decode_common_escapes(value: str) -> str:
    return (
        value
        .replace(r"\r\n", "\n")
        .replace(r"\n", "\n")
        .replace(r"\r", "\r")
        .replace(r"\t", "\t")
        .replace(r"\"", '"')
        .replace(r"\'", "'")
    )

def _is_better_decoded_text(original: str, decoded: str, *, wrapped: bool) -> bool:
    if decoded == original:
        return False

    escape_tokens = (r"\n", r"\r", r"\t", r"\"", r"\'")
    original_escape_count = sum(original.count(token) for token in escape_tokens)
    decoded_escape_count = sum(decoded.count(token) for token in escape_tokens)

    if wrapped:
        return original_escape_count > decoded_escape_count or decoded.count("\n") > 0

    return (
        decoded.count("\n") > original.count("\n")
        and decoded_escape_count < original_escape_count
    )
