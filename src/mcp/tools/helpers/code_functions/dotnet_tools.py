from __future__ import annotations

from typing import Any

from .common import _dotnet_cwd, _require_executable, _resolve_dotnet_target, _run_subprocess

def dotnet_restore(path: str = ".", timeout: int = 600) -> dict[str, Any]:
    target = _resolve_dotnet_target(path)
    _require_executable("dotnet")
    return _run_subprocess(
        ["dotnet", "restore", str(target)],
        cwd=_dotnet_cwd(target),
        timeout=timeout,
    )

def dotnet_build(
    path: str = ".",
    configuration: str | None = None,
    framework: str | None = None,
    no_restore: bool = False,
    timeout: int = 600,
) -> dict[str, Any]:
    target = _resolve_dotnet_target(path)
    _require_executable("dotnet")
    command = ["dotnet", "build", str(target)]
    if configuration:
        command.extend(["-c", configuration])
    if framework:
        command.extend(["-f", framework])
    if no_restore:
        command.append("--no-restore")

    return _run_subprocess(command, cwd=_dotnet_cwd(target), timeout=timeout)

def dotnet_test(
    path: str = ".",
    filter: str | None = None,
    configuration: str | None = None,
    no_build: bool = False,
    timeout: int = 600,
) -> dict[str, Any]:
    target = _resolve_dotnet_target(path)
    _require_executable("dotnet")
    command = ["dotnet", "test", str(target)]
    if filter:
        command.extend(["--filter", filter])
    if configuration:
        command.extend(["-c", configuration])
    if no_build:
        command.append("--no-build")

    return _run_subprocess(command, cwd=_dotnet_cwd(target), timeout=timeout)

def dotnet_run(
    path: str = ".",
    args: list[str] | None = None,
    framework: str | None = None,
    configuration: str | None = None,
    no_build: bool = False,
    timeout: int = 600,
) -> dict[str, Any]:
    target = _resolve_dotnet_target(path, allow_solution=False)
    _require_executable("dotnet")
    command = ["dotnet", "run", "--project", str(target)]
    if framework:
        command.extend(["-f", framework])
    if configuration:
        command.extend(["-c", configuration])
    if no_build:
        command.append("--no-build")
    if args:
        command.append("--")
        command.extend(args)

    return _run_subprocess(command, cwd=_dotnet_cwd(target), timeout=timeout)
