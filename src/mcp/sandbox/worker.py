from __future__ import annotations

import json
import sys
from pathlib import Path

from .models import SandboxRequest, SandboxResponse
from .operations import run_operation


def run_request(request_path: Path, response_path: Path, *, timeout: float) -> int:
    try:
        request = SandboxRequest.from_dict(
            json.loads(request_path.read_text(encoding="utf-8"))
        )
        result = run_operation(
            request.operation,
            request.arguments,
            request.network_policy,
            timeout=timeout,
        )
        response = SandboxResponse(success=True, result=result)
    except Exception as exc:
        response = SandboxResponse(success=False, error=str(exc))

    response_path.write_text(
        json.dumps(response.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return 0 if response.success else 1


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    if len(args) not in {2, 3}:
        print(
            "Uso: python -m src.mcp.sandbox.worker request.json response.json [timeout]",
            file=sys.stderr,
        )
        return 2

    timeout = float(args[2]) if len(args) == 3 else 30.0
    return run_request(Path(args[0]), Path(args[1]), timeout=timeout)


if __name__ == "__main__":
    raise SystemExit(main())
