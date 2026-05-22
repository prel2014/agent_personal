from __future__ import annotations

import ast
import fnmatch
import re
from pathlib import Path
from typing import Any

from .common import (
    _SymbolCollector,
    _append_tree,
    _iter_all_files,
    _iter_python_files,
    _iter_text_files,
    _read_text_lines,
    _relative_path_text,
)

def search_code(
    query: str,
    path: str = ".",
    regex: bool = False,
    case_sensitive: bool = False,
    file_glob: str = "*",
    max_results: int = 100,
) -> list[dict[str, Any]]:
    root = Path(path)
    results: list[dict[str, Any]] = []

    if regex:
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = re.compile(query, flags)
        matcher = lambda line: pattern.search(line)
    else:
        needle = query if case_sensitive else query.lower()
        matcher = lambda line: needle in (line if case_sensitive else line.lower())

    for file_path in _iter_text_files(root, file_glob=file_glob):
        for line_number, line in enumerate(_read_text_lines(file_path), start=1):
            if matcher(line):
                results.append(
                    {
                        "path": str(file_path),
                        "line": line_number,
                        "text": line.rstrip("\n"),
                    }
                )
                if len(results) >= max_results:
                    return results

    return results

def find_files(glob: str, path: str = ".", max_results: int = 200) -> list[str]:
    root = Path(path)
    matches: list[str] = []

    for file_path in _iter_all_files(root):
        relative_path = _relative_path_text(file_path, root)
        if fnmatch.fnmatch(file_path.name, glob) or fnmatch.fnmatch(relative_path, glob):
            matches.append(str(file_path))
            if len(matches) >= max_results:
                break

    return matches

def list_tree(path: str = ".", depth: int = 3) -> str:
    root = Path(path)
    if depth < 0:
        raise ValueError("'depth' no puede ser negativo.")

    lines = [root.name or str(root)]
    _append_tree(root, lines, prefix="", current_depth=0, max_depth=depth)
    return "\n".join(lines)

def get_python_symbols(path: str) -> list[dict[str, Any]]:
    file_path = Path(path)
    tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    collector = _SymbolCollector(str(file_path))
    collector.visit(tree)
    return collector.symbols

def find_definition(symbol: str, path: str = ".", max_results: int = 100) -> list[dict[str, Any]]:
    root = Path(path)
    definitions: list[dict[str, Any]] = []

    for file_path in _iter_python_files(root):
        try:
            symbols = get_python_symbols(str(file_path))
        except SyntaxError:
            continue

        for item in symbols:
            if item["name"] == symbol or item["qualified_name"] == symbol:
                definitions.append(item)
                if len(definitions) >= max_results:
                    return definitions

    return definitions

def find_references(symbol: str, path: str = ".", max_results: int = 100) -> list[dict[str, Any]]:
    root = Path(path)
    pattern = re.compile(rf"\b{re.escape(symbol)}\b")
    results: list[dict[str, Any]] = []

    for file_path in _iter_python_files(root):
        for line_number, line in enumerate(_read_text_lines(file_path), start=1):
            for match in pattern.finditer(line):
                results.append(
                    {
                        "path": str(file_path),
                        "line": line_number,
                        "column": match.start() + 1,
                        "text": line.rstrip("\n"),
                    }
                )
                if len(results) >= max_results:
                    return results

    return results

def extract_imports(path: str) -> list[dict[str, Any]]:
    file_path = Path(path)
    tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    imports: list[dict[str, Any]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(
                    {
                        "type": "import",
                        "module": alias.name,
                        "alias": alias.asname,
                        "line": node.lineno,
                    }
                )
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imports.append(
                    {
                        "type": "from",
                        "module": node.module,
                        "name": alias.name,
                        "alias": alias.asname,
                        "level": node.level,
                        "line": node.lineno,
                    }
                )

    return imports
