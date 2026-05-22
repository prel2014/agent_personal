from __future__ import annotations

import base64
import json
import os
import select
import socket
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlsplit

from .models import NetworkPolicy
from .network import NetworkPolicyError, assert_host_allowed, assert_url_allowed


HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "proxy-connection",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


class FilteringProxyServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, server_address, handler_class, policy: NetworkPolicy):
        super().__init__(server_address, handler_class)
        self.policy = policy


class FilteringProxyHandler(BaseHTTPRequestHandler):
    server: FilteringProxyServer
    timeout = 30

    def do_CONNECT(self) -> None:
        try:
            host, port = _split_authority(self.path)
            assert_host_allowed(host, self.server.policy)
        except Exception as exc:
            self._send_proxy_error(403, str(exc))
            return

        try:
            upstream = socket.create_connection((host, port), timeout=self.timeout)
        except OSError as exc:
            self._send_proxy_error(502, f"No se pudo conectar al destino: {exc}")
            return

        self.send_response(200, "Connection Established")
        self.end_headers()
        self._tunnel(upstream)

    def do_GET(self) -> None:
        self._forward_http()

    def do_HEAD(self) -> None:
        self._forward_http()

    def do_POST(self) -> None:
        self._forward_http()

    def do_PUT(self) -> None:
        self._forward_http()

    def do_DELETE(self) -> None:
        self._forward_http()

    def do_OPTIONS(self) -> None:
        self._forward_http()

    def log_message(self, format: str, *args) -> None:
        return None

    def _forward_http(self) -> None:
        parsed = urlsplit(self.path)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            self._send_proxy_error(400, "El proxy requiere URL absoluta http/https.")
            return

        try:
            assert_url_allowed(self.path, self.server.policy)
        except NetworkPolicyError as exc:
            self._send_proxy_error(403, str(exc))
            return

        if parsed.scheme == "https":
            self._send_proxy_error(400, "HTTPS debe usar CONNECT.")
            return

        port = parsed.port or 80
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query

        body = self._read_request_body()
        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in HOP_BY_HOP_HEADERS
        }
        headers["Host"] = parsed.netloc

        connection = None
        try:
            connection = HTTPConnection(parsed.hostname, port, timeout=self.timeout)
            connection.request(self.command, path, body=body, headers=headers)
            response = connection.getresponse()
            self.send_response(response.status, response.reason)
            for key, value in response.getheaders():
                if key.lower() not in HOP_BY_HOP_HEADERS:
                    self.send_header(key, value)
            self.end_headers()

            remaining = self.server.policy.max_response_bytes
            while remaining > 0:
                chunk = response.read(min(64 * 1024, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                self.wfile.write(chunk)
        except OSError as exc:
            self._send_proxy_error(502, f"Error reenviando request: {exc}")
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass

    def _read_request_body(self) -> bytes | None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return None
        return self.rfile.read(length)

    def _tunnel(self, upstream: socket.socket) -> None:
        sockets = [self.connection, upstream]
        try:
            while True:
                readable, _, errored = select.select(sockets, [], sockets, self.timeout)
                if errored or not readable:
                    break
                for sock in readable:
                    data = sock.recv(64 * 1024)
                    if not data:
                        return
                    target = upstream if sock is self.connection else self.connection
                    target.sendall(data)
        finally:
            upstream.close()

    def _send_proxy_error(self, status: int, message: str) -> None:
        body = json.dumps(
            {"success": False, "error": message},
            ensure_ascii=False,
        ).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _split_authority(value: str) -> tuple[str, int]:
    if ":" not in value:
        return value.strip("[]"), 443
    host, raw_port = value.rsplit(":", 1)
    return host.strip("[]"), int(raw_port)


def policy_from_env() -> NetworkPolicy:
    raw = os.getenv("MCP_SANDBOX_POLICY_B64")
    if not raw:
        return NetworkPolicy()
    payload = json.loads(base64.b64decode(raw).decode("utf-8"))
    return NetworkPolicy.from_dict(payload)


def serve_forever(
    *,
    host: str = "0.0.0.0",
    port: int = 8080,
    policy: NetworkPolicy | None = None,
) -> None:
    server = FilteringProxyServer(
        (host, port),
        FilteringProxyHandler,
        policy or policy_from_env(),
    )
    try:
        server.serve_forever()
    finally:
        server.server_close()


def main() -> int:
    port = int(os.getenv("MCP_SANDBOX_PROXY_PORT") or "8080")
    serve_forever(port=port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
