from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from .domains import host_matches_any, normalize_domain_patterns
from .models import NetworkPolicy


PRIVATE_NETWORKS = tuple(
    ipaddress.ip_network(value)
    for value in (
        "0.0.0.0/8",
        "10.0.0.0/8",
        "100.64.0.0/10",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "224.0.0.0/4",
        "::1/128",
        "fc00::/7",
        "fe80::/10",
    )
)


class NetworkPolicyError(PermissionError):
    pass


def validate_url(url: str) -> tuple[str, str, int]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise NetworkPolicyError("Solo se permiten URLs http y https.")
    if not parsed.hostname:
        raise NetworkPolicyError("La URL no contiene host valido.")

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return parsed.scheme, parsed.hostname.rstrip(".").lower(), int(port)


def assert_url_allowed(url: str, policy: NetworkPolicy) -> None:
    _, host, _ = validate_url(url)
    assert_host_allowed(host, policy)


def assert_host_allowed(host: str, policy: NetworkPolicy) -> None:
    normalized_host = host.strip().lower().strip("[]").rstrip(".")
    denied_domains = normalize_domain_patterns(policy.denied_domains)
    allowed_domains = normalize_domain_patterns(policy.allowed_domains)

    if host_matches_any(normalized_host, denied_domains):
        raise NetworkPolicyError(f"Dominio bloqueado por politica: {normalized_host}")

    if allowed_domains and not host_matches_any(normalized_host, allowed_domains):
        raise NetworkPolicyError(f"Dominio fuera de allowlist: {normalized_host}")

    if policy.block_private_networks and host_resolves_private(normalized_host):
        raise NetworkPolicyError(f"Destino bloqueado por red privada/local: {normalized_host}")


def host_resolves_private(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
        return is_private_ip(ip)
    except ValueError:
        pass

    try:
        records = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise NetworkPolicyError(f"No se pudo resolver el host: {host}") from exc

    addresses = {
        record[4][0]
        for record in records
        if record and len(record) >= 5 and record[4]
    }
    if not addresses:
        raise NetworkPolicyError(f"No se encontraron direcciones para host: {host}")

    return any(is_private_ip(ipaddress.ip_address(address)) for address in addresses)


def is_private_ip(ip: ipaddress._BaseAddress) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or any(ip in network for network in PRIVATE_NETWORKS)
    )
