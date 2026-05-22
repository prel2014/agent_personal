from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Any

PROJECT_SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
}

LANGUAGE_MARKERS = {
    "python": {
        "files": {
            "pyproject.toml",
            "requirements.txt",
            "setup.py",
            "setup.cfg",
            "pipfile",
            "poetry.lock",
        },
        "suffixes": {".py", ".pyi"},
    },
    "node": {
        "files": {
            "package.json",
            "package-lock.json",
            "npm-shrinkwrap.json",
            "pnpm-lock.yaml",
            "yarn.lock",
            "bun.lock",
            "bun.lockb",
            "tsconfig.json",
        },
        "suffixes": {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"},
    },
    "dotnet": {
        "files": {
            "global.json",
            "nuget.config",
            "directory.build.props",
            "directory.build.targets",
        },
        "suffixes": {".cs", ".csx", ".fs", ".vb", ".csproj", ".fsproj", ".vbproj", ".sln"},
    },
}

def _detect_project_profile(base_dir: Path) -> dict[str, Any]:
    scores = {language: 0 for language in LANGUAGE_MARKERS}
    file_counts = {language: 0 for language in LANGUAGE_MARKERS}
    markers: dict[str, list[str]] = {language: [] for language in LANGUAGE_MARKERS}
    present_filenames: set[str] = set()

    for current_root, dirnames, filenames in os.walk(base_dir):
        dirnames[:] = [name for name in dirnames if name not in PROJECT_SKIP_DIRS]
        current_path = Path(current_root)

        for filename in filenames:
            file_path = current_path / filename
            relative_path = file_path.relative_to(base_dir).as_posix()
            normalized_name = filename.lower()
            suffix = file_path.suffix.lower()
            present_filenames.add(normalized_name)

            for language, config in LANGUAGE_MARKERS.items():
                if normalized_name in config["files"]:
                    scores[language] += 5
                    if relative_path not in markers[language] and len(markers[language]) < 8:
                        markers[language].append(relative_path)

                if suffix in config["suffixes"]:
                    file_counts[language] += 1
                    scores[language] += 1

    detected_languages = [
        language
        for language in LANGUAGE_MARKERS
        if scores[language] > 0 or file_counts[language] > 0
    ]
    detected_languages.sort(key=lambda language: (-scores[language], language))

    primary_language = detected_languages[0] if detected_languages else None
    return {
        "detected_languages": detected_languages,
        "primary_language": primary_language,
        "markers": {language: values for language, values in markers.items() if values},
        "file_counts": {language: count for language, count in file_counts.items() if count},
        "tooling": _detect_tooling(base_dir, present_filenames),
    }

def _detect_tooling(base_dir: Path, present_filenames: set[str]) -> dict[str, object]:
    return {
        "python": {
            "available": True,
            "command": sys.executable,
        },
        "node": {
            "available": shutil.which("node") is not None,
            "node": shutil.which("node"),
            "npm": shutil.which("npm"),
            "pnpm": shutil.which("pnpm"),
            "yarn": shutil.which("yarn"),
            "bun": shutil.which("bun"),
            "npx": shutil.which("npx"),
            "tsc": shutil.which("tsc"),
            "preferred_package_manager": _detect_preferred_package_manager(present_filenames),
        },
        "dotnet": {
            "available": shutil.which("dotnet") is not None,
            "dotnet": shutil.which("dotnet"),
        },
    }

def _detect_preferred_package_manager(present_filenames: set[str]) -> str | None:
    for manager, filenames in (
        ("bun", ("bun.lock", "bun.lockb")),
        ("pnpm", ("pnpm-lock.yaml",)),
        ("yarn", ("yarn.lock",)),
        ("npm", ("package-lock.json", "npm-shrinkwrap.json")),
    ):
        if any(filename.lower() in present_filenames for filename in filenames):
            return manager

    return None
