from __future__ import annotations

import ast
import fnmatch
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from ..read_policy import is_read_protected

SKIP_DIRS = {
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

TEXT_FILE_EXTENSIONS = {
    ".py",
    ".pyi",
    ".txt",
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".env",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".html",
    ".css",
    ".scss",
    ".sql",
    ".sh",
    ".ps1",
    ".xml",
    ".csv",
}

JS_FILE_EXTENSIONS = {
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
}

TS_FILE_EXTENSIONS = {
    ".ts",
    ".tsx",
}

DOTNET_PROJECT_EXTENSIONS = {
    ".csproj",
    ".fsproj",
    ".vbproj",
    ".sln",
}

NODE_PACKAGE_MANAGERS = ("npm", "pnpm", "yarn", "bun")

def _append_tree(
    root: Path,
    output: list[str],
    prefix: str,
    current_depth: int,
    max_depth: int,
) -> None:
    if not root.is_dir():
        return

    if current_depth >= max_depth:
        return

    children = _sorted_children(root)
    for index, child in enumerate(children):
        connector = "\\-- " if index == len(children) - 1 else "|-- "
        output.append(f"{prefix}{connector}{child.name}")

        if child.is_dir():
            extension = "    " if index == len(children) - 1 else "|   "
            _append_tree(
                child,
                output,
                prefix + extension,
                current_depth + 1,
                max_depth,
            )

def _sorted_children(path: Path) -> list[Path]:
    children = [
        child
        for child in path.iterdir()
        if child.name not in SKIP_DIRS
        and not is_read_protected(child, base_dir=path)
    ]
    return sorted(children, key=lambda item: (not item.is_dir(), item.name.lower()))

def _iter_all_files(root: Path):
    if root.is_file():
        if not is_read_protected(root, base_dir=root.parent):
            yield root
        return

    for current_root, dirnames, filenames in os.walk(root):
        current_path = Path(current_root)
        dirnames[:] = [
            name
            for name in dirnames
            if name not in SKIP_DIRS
            and not is_read_protected(current_path / name, base_dir=root)
        ]
        for filename in filenames:
            file_path = current_path / filename
            if is_read_protected(file_path, base_dir=root):
                continue
            yield file_path

def _iter_text_files(root: Path, file_glob: str = "*"):
    for file_path in _iter_all_files(root):
        relative_path = _relative_path_text(file_path, root)
        if not (
            fnmatch.fnmatch(file_path.name, file_glob)
            or fnmatch.fnmatch(relative_path, file_glob)
        ):
            continue

        if file_path.suffix.lower() in TEXT_FILE_EXTENSIONS:
            yield file_path

def _iter_python_files(root: Path):
    for file_path in _iter_all_files(root):
        if file_path.suffix == ".py":
            yield file_path

def _read_text_lines(path: Path):
    try:
        with path.open("r", encoding="utf-8") as handle:
            yield from handle
    except UnicodeDecodeError:
        return

def _require_existing_path(path: str) -> Path:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"No existe la ruta indicada: {path}")

    return target

def _require_executable(name: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        raise RuntimeError(f"No se encontro el ejecutable requerido: {name}")

    return executable

def _find_upwards(start: Path, filename: str) -> Path | None:
    current = start.resolve()
    while True:
        candidate = current / filename
        if candidate.exists():
            return candidate

        if current.parent == current:
            return None

        current = current.parent

def _resolve_node_project_root(path: str) -> Path:
    target = _require_existing_path(path)
    if target.is_file() and target.name == "package.json":
        return target.parent

    start = target if target.is_dir() else target.parent
    package_json = _find_upwards(start, "package.json")
    if package_json is not None:
        return package_json.parent

    return start

def _resolve_node_package_manager(project_root: Path, package_manager: str | None) -> str:
    if package_manager:
        normalized = package_manager.strip().lower()
        if normalized not in NODE_PACKAGE_MANAGERS:
            raise ValueError("package_manager debe ser uno de: npm, pnpm, yarn o bun.")
        _require_executable(normalized)
        return normalized

    for manager, filenames in (
        ("bun", ("bun.lock", "bun.lockb")),
        ("pnpm", ("pnpm-lock.yaml",)),
        ("yarn", ("yarn.lock",)),
        ("npm", ("package-lock.json", "npm-shrinkwrap.json")),
    ):
        if any((project_root / filename).exists() for filename in filenames):
            _require_executable(manager)
            return manager

    for candidate in NODE_PACKAGE_MANAGERS:
        if shutil.which(candidate):
            return candidate

    raise RuntimeError("No se encontro npm, pnpm, yarn ni bun para ejecutar scripts Node.")

def _build_node_script_command(
    package_manager: str,
    script: str,
    args: list[str],
) -> list[str]:
    if package_manager == "npm":
        command = ["npm", "run", script]
        if args:
            command.extend(["--", *args])
        return command

    if package_manager == "pnpm":
        command = ["pnpm", "run", script]
        if args:
            command.extend(["--", *args])
        return command

    if package_manager == "yarn":
        return ["yarn", "run", script, *args]

    if package_manager == "bun":
        return ["bun", "run", script, *args]

    raise ValueError(f"Package manager Node no soportado: {package_manager}")

def _resolve_tsc_runner() -> list[str]:
    if shutil.which("tsc"):
        return ["tsc"]

    if shutil.which("npx"):
        return ["npx", "--no-install", "tsc"]

    raise RuntimeError("No se encontro 'tsc' ni 'npx' para ejecutar TypeScript.")

def _resolve_dotnet_target(path: str, *, allow_solution: bool = True) -> Path:
    target = _require_existing_path(path)

    if target.is_file():
        suffix = target.suffix.lower()
        if suffix not in DOTNET_PROJECT_EXTENSIONS:
            raise ValueError("La ruta debe apuntar a un .csproj, .fsproj, .vbproj o .sln.")
        if not allow_solution and suffix == ".sln":
            raise ValueError("dotnet_run no acepta archivos .sln; usa un proyecto o carpeta.")

    return target

def _dotnet_cwd(target: Path) -> str:
    return str(target if target.is_dir() else target.parent)

def _run_subprocess(
    command: list[str],
    cwd: str,
    timeout: int,
    extra_env: dict[str, str] | None = None,
) -> dict[str, Any]:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)

    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    return {
        "command": command,
        "cwd": cwd,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "success": completed.returncode == 0,
    }

def _detect_newline(text: str) -> str:
    if "\r\n" in text:
        return "\r\n"

    return "\n"

def _relative_path_text(file_path: Path, root: Path) -> str:
    if root.is_file():
        return file_path.name

    return file_path.relative_to(root).as_posix()

def _command_cwd(path: str) -> str:
    target = Path(path)
    return str(target if target.is_dir() else target.parent)

class _SymbolCollector(ast.NodeVisitor):
    def __init__(self, path: str):
        self.path = path
        self.class_stack: list[str] = []
        self.symbols: list[dict[str, Any]] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        qualified_name = ".".join([*self.class_stack, node.name]) if self.class_stack else node.name
        self.symbols.append(
            {
                "path": self.path,
                "name": node.name,
                "qualified_name": qualified_name,
                "kind": "class",
                "line": node.lineno,
                "end_line": getattr(node, "end_lineno", node.lineno),
            }
        )

        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self._append_function_symbol(node, "method" if self.class_stack else "function")
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        self._append_function_symbol(
            node,
            "async_method" if self.class_stack else "async_function",
        )
        self.generic_visit(node)

    def _append_function_symbol(self, node: ast.AST, kind: str) -> None:
        name = node.name
        qualified_name = ".".join([*self.class_stack, name]) if self.class_stack else name
        self.symbols.append(
            {
                "path": self.path,
                "name": name,
                "qualified_name": qualified_name,
                "kind": kind,
                "line": node.lineno,
                "end_line": getattr(node, "end_lineno", node.lineno),
            }
        )
