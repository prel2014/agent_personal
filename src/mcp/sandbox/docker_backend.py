from __future__ import annotations

import base64
import json
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any

from .models import NetworkPolicy, SandboxRequest, SandboxResponse


class DockerSandboxBackend:
    def __init__(self, *, image: str, base_dir: Path, timeout: float) -> None:
        self.image = image
        self.base_dir = base_dir
        self.timeout = timeout

    def run(
        self,
        operation: str,
        arguments: dict[str, Any],
        policy: NetworkPolicy,
    ) -> SandboxResponse:
        if shutil.which("docker") is None:
            return SandboxResponse(
                success=False,
                error="Docker no esta disponible en PATH. Instala Docker Desktop o usa MCP_SANDBOX_BACKEND=local solo para pruebas.",
            )

        daemon_check = self._run_docker(["info"], check=False)
        if daemon_check.returncode != 0:
            return SandboxResponse(
                success=False,
                error=(
                    "Docker esta instalado pero el daemon no responde. "
                    "Inicia Docker Desktop y vuelve a intentar. "
                    f"Detalle: {daemon_check.stderr.strip() or daemon_check.stdout.strip()}"
                ),
            )

        image_check = self._run_docker(["image", "inspect", self.image], check=False)
        if image_check.returncode != 0:
            return SandboxResponse(
                success=False,
                error=(
                    f"La imagen Docker '{self.image}' no existe. "
                    "Construyela con: docker build -f docker/sandbox/Dockerfile -t "
                    f"{self.image} ."
                ),
            )

        session_id = uuid.uuid4().hex[:12]
        session_dir = self.base_dir / ".mcp_sandbox" / "sessions" / session_id
        session_dir.mkdir(parents=True, exist_ok=False)
        request_path = session_dir / "request.json"
        response_path = session_dir / "response.json"
        request = SandboxRequest(operation, arguments, policy)
        request_path.write_text(
            json.dumps(request.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        internal_network = f"mcp_sandbox_{session_id}_internal"
        egress_network = f"mcp_sandbox_{session_id}_egress"
        proxy_name = f"mcp_sandbox_{session_id}_proxy"
        worker_name = f"mcp_sandbox_{session_id}_worker"
        policy_b64 = base64.b64encode(
            json.dumps(policy.to_dict(), ensure_ascii=False).encode("utf-8")
        ).decode("ascii")

        try:
            self._run_docker(["network", "create", egress_network])
            self._run_docker(["network", "create", "--internal", internal_network])
            self._run_docker(
                [
                    "run",
                    "-d",
                    "--name",
                    proxy_name,
                    "--network",
                    egress_network,
                    "-e",
                    f"MCP_SANDBOX_POLICY_B64={policy_b64}",
                    self.image,
                    "python",
                    "-m",
                    "src.mcp.sandbox.proxy",
                ]
            )
            self._run_docker(
                [
                    "network",
                    "connect",
                    "--alias",
                    "sandbox_proxy",
                    internal_network,
                    proxy_name,
                ]
            )
            worker = self._run_docker(
                [
                    "run",
                    "--rm",
                    "--name",
                    worker_name,
                    "--network",
                    internal_network,
                    "-v",
                    f"{session_dir}:/sandbox:rw",
                    "-e",
                    "HTTP_PROXY=http://sandbox_proxy:8080",
                    "-e",
                    "HTTPS_PROXY=http://sandbox_proxy:8080",
                    "-e",
                    "http_proxy=http://sandbox_proxy:8080",
                    "-e",
                    "https_proxy=http://sandbox_proxy:8080",
                    "-e",
                    "NO_PROXY=localhost,127.0.0.1,::1",
                    "-e",
                    "no_proxy=localhost,127.0.0.1,::1",
                    self.image,
                    "python",
                    "-m",
                    "src.mcp.sandbox.worker",
                    "/sandbox/request.json",
                    "/sandbox/response.json",
                    str(self.timeout),
                ],
                check=False,
            )
            if not response_path.exists():
                return SandboxResponse(
                    success=False,
                    error=(
                        "El worker no genero response.json. "
                        f"stdout={worker.stdout.strip()} stderr={worker.stderr.strip()}"
                    ),
                )
            return SandboxResponse.from_dict(
                json.loads(response_path.read_text(encoding="utf-8"))
            )
        except Exception as exc:
            return SandboxResponse(success=False, error=str(exc))
        finally:
            self._run_docker(["rm", "-f", proxy_name], check=False)
            self._run_docker(["network", "rm", internal_network], check=False)
            self._run_docker(["network", "rm", egress_network], check=False)

    def _run_docker(
        self,
        args: list[str],
        *,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            ["docker", *args],
            capture_output=True,
            text=True,
            timeout=max(self.timeout, 5.0),
        )
        if check and completed.returncode != 0:
            raise RuntimeError(
                f"docker {' '.join(args)} fallo con codigo {completed.returncode}: "
                f"{completed.stderr.strip() or completed.stdout.strip()}"
            )
        return completed
