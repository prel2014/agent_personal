from __future__ import annotations

import ast
import os
import py_compile
import shutil
import sys
from pathlib import Path
from typing import Any

from .common import _command_cwd, _require_existing_path, _run_subprocess

def syntax_check_python(path: str) -> dict[str, Any]:
    file_path = Path(path)
    source = file_path.read_text(encoding="utf-8")

    try:
        ast.parse(source, filename=str(file_path))
    except SyntaxError as exc:
        return {
            "valid": False,
            "path": str(file_path),
            "line": exc.lineno,
            "offset": exc.offset,
            "message": exc.msg,
            "text": exc.text.strip() if exc.text else None,
        }

    return {
        "valid": True,
        "path": str(file_path),
    }

def python_compile_check(path: str) -> dict[str, Any]:
    file_path = _require_existing_path(path)
    if file_path.suffix.lower() not in {".py", ".pyi"}:
        raise ValueError("python_compile_check espera un archivo Python (.py o .pyi).")

    descriptor, compiled_path = tempfile.mkstemp(suffix=".pyc")
    os.close(descriptor)

    try:
        py_compile.compile(str(file_path), cfile=compiled_path, doraise=True)
    except py_compile.PyCompileError as exc:
        return {
            "valid": False,
            "path": str(file_path),
            "message": str(exc),
        }
    finally:
        try:
            os.remove(compiled_path)
        except OSError:
            pass

    return {
        "valid": True,
        "path": str(file_path),
    }

def run_python_file(path: str, args: list[str] | None = None, timeout: int = 120) -> dict[str, Any]:
    file_path = Path(path)
    command = [sys.executable, str(file_path), *(args or [])]
    return _run_subprocess(command, cwd=str(file_path.parent), timeout=timeout)

def python_interpreter(
    code: str,
    path: str = ".",
    timeout: int = 120,
) -> dict[str, Any]:
    if not code.strip():
        raise ValueError("python_interpreter requiere codigo Python en el argumento 'code'.")

    command = [sys.executable, "-c", code]
    return _run_subprocess(command, cwd=_command_cwd(path), timeout=timeout)

def run_module(
    module: str,
    path: str = ".",
    args: list[str] | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    command = [sys.executable, "-m", module, *(args or [])]
    return _run_subprocess(command, cwd=path, timeout=timeout)

def run_tests(
    path: str = ".",
    pattern: str | None = None,
    timeout: int = 180,
) -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-p",
        "no:cacheprovider",
        "--ignore-glob=pytest-cache-files-*",
        path,
    ]
    if pattern:
        command.extend(["-k", pattern])

    return _run_subprocess(
        command,
        cwd=_command_cwd(path),
        timeout=timeout,
        extra_env={"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
    )

def lint_python(path: str = ".", timeout: int = 180) -> dict[str, Any]:
    if shutil.which("ruff"):
        command = ["ruff", "check", path]
        return _run_subprocess(command, cwd=_command_cwd(path), timeout=timeout)

    if shutil.which("flake8"):
        command = ["flake8", path]
        return _run_subprocess(command, cwd=_command_cwd(path), timeout=timeout)

    raise RuntimeError("No se encontro 'ruff' ni 'flake8' instalados para lint_python.")

def format_python(path: str = ".", timeout: int = 180) -> dict[str, Any]:
    if shutil.which("ruff"):
        command = ["ruff", "format", path]
        return _run_subprocess(command, cwd=_command_cwd(path), timeout=timeout)

    if shutil.which("black"):
        command = ["black", path]
        return _run_subprocess(command, cwd=_command_cwd(path), timeout=timeout)

    raise RuntimeError("No se encontro 'ruff' ni 'black' instalados para format_python.")
