from __future__ import annotations

from pathlib import Path

from src.mcp.path_policies import (
    DEFAULT_PROTECTED_READ_PATH_PATTERNS,
    matches_protected_path,
)


_protected_read_patterns: tuple[str, ...] = DEFAULT_PROTECTED_READ_PATH_PATTERNS


def configure_read_policy(patterns: tuple[str, ...]) -> None:
    global _protected_read_patterns
    _protected_read_patterns = patterns or DEFAULT_PROTECTED_READ_PATH_PATTERNS


def is_read_protected(path: Path, *, base_dir: Path | None = None) -> bool:
    return matches_protected_path(
        path,
        patterns=_protected_read_patterns,
        base_dir=base_dir,
    )
