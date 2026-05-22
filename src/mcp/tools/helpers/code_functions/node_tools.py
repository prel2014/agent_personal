from __future__ import annotations

from typing import Any

from .common import (
    JS_FILE_EXTENSIONS,
    TS_FILE_EXTENSIONS,
    _build_node_script_command,
    _find_upwards,
    _require_executable,
    _require_existing_path,
    _resolve_node_package_manager,
    _resolve_node_project_root,
    _resolve_tsc_runner,
    _run_subprocess,
)

def node_syntax_check(path: str, timeout: int = 120) -> dict[str, Any]:
    file_path = _require_existing_path(path)
    suffix = file_path.suffix.lower()

    if suffix in TS_FILE_EXTENSIONS:
        return ts_typecheck(str(file_path), timeout=timeout)

    if suffix not in JS_FILE_EXTENSIONS:
        raise ValueError(
            "node_syntax_check espera un archivo JavaScript (.js, .jsx, .mjs o .cjs)."
        )

    _require_executable("node")
    return _run_subprocess(
        ["node", "--check", str(file_path)],
        cwd=str(file_path.parent),
        timeout=timeout,
    )

def node_run_script(
    script: str,
    path: str = ".",
    args: list[str] | None = None,
    timeout: int = 180,
    package_manager: str | None = None,
) -> dict[str, Any]:
    project_root = _resolve_node_project_root(path)
    manager = _resolve_node_package_manager(project_root, package_manager)
    command = _build_node_script_command(manager, script, args or [])
    return _run_subprocess(command, cwd=str(project_root), timeout=timeout)

def node_test(
    path: str = ".",
    args: list[str] | None = None,
    timeout: int = 300,
    package_manager: str | None = None,
) -> dict[str, Any]:
    return node_run_script(
        "test",
        path=path,
        args=args,
        timeout=timeout,
        package_manager=package_manager,
    )

def node_lint(
    path: str = ".",
    args: list[str] | None = None,
    timeout: int = 300,
    package_manager: str | None = None,
) -> dict[str, Any]:
    return node_run_script(
        "lint",
        path=path,
        args=args,
        timeout=timeout,
        package_manager=package_manager,
    )

def node_format(
    path: str = ".",
    args: list[str] | None = None,
    timeout: int = 300,
    package_manager: str | None = None,
) -> dict[str, Any]:
    return node_run_script(
        "format",
        path=path,
        args=args,
        timeout=timeout,
        package_manager=package_manager,
    )

def ts_typecheck(path: str = ".", timeout: int = 300) -> dict[str, Any]:
    target = _require_existing_path(path)
    runner = _resolve_tsc_runner()

    if target.is_file() and target.name == "package.json":
        target = target.parent

    if target.is_file() and target.name == "tsconfig.json":
        tsconfig = target
    else:
        tsconfig = _find_upwards(target if target.is_dir() else target.parent, "tsconfig.json")

    if tsconfig is not None:
        command = [*runner, "--noEmit", "--pretty", "false", "-p", str(tsconfig)]
        return _run_subprocess(command, cwd=str(tsconfig.parent), timeout=timeout)

    if target.is_dir():
        command = [*runner, "--noEmit", "--pretty", "false"]
        return _run_subprocess(command, cwd=str(target), timeout=timeout)

    if target.suffix.lower() not in TS_FILE_EXTENSIONS:
        raise ValueError(
            "ts_typecheck espera un archivo .ts/.tsx, una carpeta o un tsconfig.json."
        )

    command = [*runner, "--noEmit", "--pretty", "false", str(target)]
    return _run_subprocess(command, cwd=str(target.parent), timeout=timeout)
