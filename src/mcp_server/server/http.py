from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from ..ollama import OllamaAPIError


class MCPHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address, request_handler_class, service):
        super().__init__(server_address, request_handler_class)
        self.service = service


class MCPRequestHandler(BaseHTTPRequestHandler):
    server: MCPHTTPServer

    def do_GET(self) -> None:
        if self.path == "/health":
            if not self._authorize_request(require_auth=not self.server.service.config.public_health):
                return
            self._send_json(200, self.server.service.health())
            return

        if self.path == "/info":
            if not self._authorize_request(require_auth=self.server.service.config.require_auth_for_info):
                return
            self._send_json(200, self.server.service.info())
            return

        if self.path == "/nodes":
            if not self._authorize_request(require_auth=self.server.service.config.require_auth_for_info):
                return
            self._send_json(200, self.server.service.nodes())
            return

        self._send_json(404, {"ok": False, "error": "Ruta no encontrada."})

    def do_POST(self) -> None:
        if self.path != "/v1/chat":
            self._send_json(404, {"ok": False, "error": "Ruta no encontrada."})
            return
        if not self._authorize_request(require_auth=True):
            return

        try:
            payload = self._read_json_body()
            if payload.get("stream") is True:
                self._send_ndjson(200, self.server.service.chat_stream(payload))
            else:
                result = self.server.service.chat(payload)
                self._send_json(200, result)
        except ValueError as exc:
            self._send_json(400, {"ok": False, "error": str(exc)})
        except OllamaAPIError as exc:
            self._send_json(exc.status_code, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self._send_json(500, {"ok": False, "error": str(exc)})

    def log_message(self, format: str, *args) -> None:
        super().log_message(format, *args)

    def _read_json_body(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length else b"{}"
        payload = json.loads(raw_body.decode("utf-8"))

        if not isinstance(payload, dict):
            raise ValueError("El body debe ser un objeto JSON.")

        return payload

    def _send_json(self, status_code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorize_request(self, *, require_auth: bool) -> bool:
        config = self.server.service.config
        if config.auth_mode == "off" or not require_auth:
            return True

        header = self.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            self._send_unauthorized("Falta Authorization: Bearer <token>.")
            return False

        token = header[len("Bearer ") :].strip()
        if token not in config.auth_static_tokens:
            self._send_unauthorized("Token Bearer invalido.")
            return False

        return True

    def _send_unauthorized(self, message: str) -> None:
        body = json.dumps(
            {"ok": False, "error": message},
            ensure_ascii=False,
        ).encode("utf-8")
        self.send_response(401)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("WWW-Authenticate", 'Bearer realm="mcp_server"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_ndjson(self, status_code: int, payloads) -> None:
        self.send_response(status_code)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        try:
            for payload in payloads:
                line = json.dumps(payload, ensure_ascii=False).encode("utf-8") + b"\n"
                self.wfile.write(line)
                self.wfile.flush()
        except OllamaAPIError as exc:
            line = json.dumps(
                {
                    "ok": False,
                    "error": str(exc),
                    "done": True,
                    "message": {"role": "assistant", "content": ""},
                },
                ensure_ascii=False,
            ).encode("utf-8") + b"\n"
            self.wfile.write(line)
            self.wfile.flush()
        except BrokenPipeError:
            return
