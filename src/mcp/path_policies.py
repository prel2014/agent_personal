from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path


DEFAULT_PROTECTED_PATH_PATTERNS = (
    ".env",
    ".env.*",
    "**/.env",
    "**/.env.*",
    "*.pem",
    "*.key",
    "**/*.pem",
    "**/*.key",
    ".git",
    ".git/*",
    "**/.git/*",
)

DEFAULT_PROTECTED_READ_PATH_PATTERNS = DEFAULT_PROTECTED_PATH_PATTERNS


def matches_protected_path(
    path: Path,
    *,
    patterns: tuple[str, ...],
    base_dir: Path | None = None,
) -> bool:
    resolved = path.resolve()
    candidates = {resolved.name}
    if base_dir is not None:
        try:
            candidates.add(resolved.relative_to(base_dir.resolve()).as_posix())
        except ValueError:
            pass

    return any(
        fnmatch(candidate, pattern)
        for candidate in candidates
        for pattern in patterns
    )
