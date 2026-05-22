from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import urlparse


def normalize_http_url(
    raw_value: str | None,
    *,
    env_name: str | None = None,
    default: str,
    label: str = "URL",
) -> str:
    candidate = raw_value
    if candidate is None and env_name:
        candidate = os.getenv(env_name)
    candidate = (candidate or default).rstrip("/")
    parsed = urlparse(candidate)

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{label} invalida: {candidate}")

    return candidate


def is_loopback_host(host: str) -> bool:
    normalized = host.strip().lower()
    if normalized in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def is_loopback_url(url: str) -> bool:
    parsed = urlparse(url)
    return is_loopback_host(parsed.hostname or "")


def detect_local_lan_cidrs() -> tuple[str, ...]:
    cidrs: set[str] = set()
    for ip in local_ipv4_addresses():
        cidrs.add(str(ipaddress.ip_network(f"{ip}/24", strict=False)))
    return tuple(sorted(cidrs))


def local_ipv4_addresses() -> tuple[ipaddress.IPv4Address, ...]:
    addresses: set[str] = set()

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            addresses.add(sock.getsockname()[0])
    except OSError:
        pass

    try:
        hostname = socket.gethostname()
        for address in socket.gethostbyname_ex(hostname)[2]:
            addresses.add(address)
    except OSError:
        pass

    parsed: list[ipaddress.IPv4Address] = []
    for address in addresses:
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            continue

        if isinstance(ip, ipaddress.IPv4Address) and not (
            ip.is_loopback or ip.is_link_local or ip.is_multicast
        ):
            parsed.append(ip)

    return tuple(sorted(parsed))
