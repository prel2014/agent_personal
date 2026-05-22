from __future__ import annotations

from pathlib import Path
from typing import Any

from ..tools.helpers.code_functions.common import _iter_all_files
from .serialization import (
    _clean_model_written_content,
    _maybe_unescape_serialized_content,
)

IMAGE_SOURCE_SUFFIXES = {
    ".bmp",
    ".gif",
    ".jpeg",
    ".jpg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
}

PATH_ARGUMENTS = {"path", "path_a", "path_b", "target_path"}
DISCOVERABLE_FILE_PATH_TOOLS = {
    "readfile",
    "read_lines",
    "fileinfo",
    "get_python_symbols",
    "extract_imports",
    "syntax_check_python",
    "python_compile_check",
}
SERIALIZED_CONTENT_FIELDS = {
    "writefile": {"content"},
    "appendfile": {"content"},
    "replace_in_file": {"old", "new"},
    "replace_lines": {"content"},
}
WRITTEN_CONTENT_FIELDS = {
    "writefile": {"content"},
    "appendfile": {"content"},
    "replace_in_file": {"new"},
    "replace_lines": {"content"},
}


class RuntimeArgumentNormalizer:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir.resolve()

    def normalize(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        normalized: dict[str, Any] = {}

        for key, value in arguments.items():
            if key in PATH_ARGUMENTS and isinstance(value, str):
                normalized[key] = self.resolve_user_path(
                    value,
                    discover_file=self._should_discover_file_path(
                        tool_name,
                        key,
                        value,
                    ),
                )
            elif (
                tool_name == "image_describe"
                and key == "save_frame_path"
                and isinstance(value, str)
            ):
                normalized[key] = self.resolve_user_path(value)
            elif (
                tool_name == "image_describe"
                and key == "source"
                and isinstance(value, str)
                and self._image_source_should_resolve_as_path(value, arguments)
            ):
                normalized[key] = self.resolve_user_path(value)
            elif self._is_written_content_field(tool_name, key) and isinstance(value, str):
                normalized[key] = _clean_model_written_content(
                    value,
                    path=str(arguments.get("path") or ""),
                )
            elif self._is_serialized_content_field(tool_name, key) and isinstance(value, str):
                normalized[key] = _maybe_unescape_serialized_content(value)
            else:
                normalized[key] = value

        return normalized

    def resolve_user_path(self, value: str, *, discover_file: bool = False) -> str:
        user_path = Path(value).expanduser()
        candidate = user_path if user_path.is_absolute() else self.base_dir / user_path
        resolved = candidate.resolve()

        self._ensure_inside_base_dir(resolved)

        if discover_file and not resolved.exists():
            discovered = self._discover_relative_file(value)
            if discovered is not None:
                return str(discovered)

        return str(resolved)

    @staticmethod
    def _is_serialized_content_field(tool_name: str, key: str) -> bool:
        return key in SERIALIZED_CONTENT_FIELDS.get(tool_name, set())

    @staticmethod
    def _is_written_content_field(tool_name: str, key: str) -> bool:
        return key in WRITTEN_CONTENT_FIELDS.get(tool_name, set())

    def _image_source_should_resolve_as_path(
        self,
        value: str,
        arguments: dict[str, Any],
    ) -> bool:
        source_type = str(arguments.get("source_type", "auto")).strip().lower()
        if source_type == "file":
            return True

        if source_type != "auto":
            return False

        stripped = value.strip()
        if not stripped or stripped.isdigit():
            return False

        lowered = stripped.lower()
        if lowered.startswith(("rtsp://", "rtsps://", "http://", "https://")):
            return False

        user_path = Path(stripped).expanduser()
        candidate = user_path if user_path.is_absolute() else self.base_dir / user_path
        return candidate.exists() or user_path.suffix.lower() in IMAGE_SOURCE_SUFFIXES

    @staticmethod
    def _should_discover_file_path(tool_name: str, key: str, value: str) -> bool:
        if key != "path" or tool_name not in DISCOVERABLE_FILE_PATH_TOOLS:
            return False

        stripped = value.strip()
        if not stripped or any(marker in stripped for marker in ("*", "?", "[", "]")):
            return False

        user_path = Path(stripped).expanduser()
        if user_path.is_absolute():
            return False

        return user_path.name not in {"", ".", ".."}

    def _discover_relative_file(self, value: str) -> Path | None:
        requested = Path(value.strip().replace("\\", "/"))
        normalized_request = requested.as_posix().strip("/")
        requested_name = requested.name.lower()
        has_parent = len(requested.parts) > 1
        matches: list[Path] = []

        for file_path in _iter_all_files(self.base_dir):
            if not file_path.is_file():
                continue

            relative_path = file_path.relative_to(self.base_dir).as_posix()
            comparison_path = relative_path.lower()
            comparison_request = normalized_request.lower()
            if has_parent:
                if comparison_path == comparison_request or comparison_path.endswith(
                    "/" + comparison_request
                ):
                    matches.append(file_path.resolve())
            elif file_path.name.lower() == requested_name:
                matches.append(file_path.resolve())

        if not matches:
            return None

        matches = sorted(set(matches), key=lambda path: path.as_posix().lower())
        if len(matches) == 1:
            self._ensure_inside_base_dir(matches[0])
            return matches[0]

        relative_matches = [
            path.relative_to(self.base_dir).as_posix()
            for path in matches[:10]
        ]
        suffix = "" if len(matches) <= 10 else f" y {len(matches) - 10} mas"
        raise FileNotFoundError(
            "La ruta exacta no existe y el nombre es ambiguo. "
            f"Coincidencias para '{value}': {', '.join(relative_matches)}{suffix}. "
            "Especifica una ruta mas precisa."
        )

    def _ensure_inside_base_dir(self, path: Path) -> None:
        try:
            path.relative_to(self.base_dir)
        except ValueError as exc:
            raise PermissionError(
                f"La ruta '{path}' esta fuera de BASE_DIR '{self.base_dir}'."
            ) from exc
