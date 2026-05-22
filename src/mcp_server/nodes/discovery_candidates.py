from __future__ import annotations

import ipaddress

from src.mcp_shared.urls import local_ipv4_addresses, normalize_http_url

from .models import NodeDiscoverySettings


def candidate_base_urls(settings: NodeDiscoverySettings) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()

    for item in settings.hosts:
        base_url = normalize_candidate(item, settings.port)
        if base_url and base_url not in seen:
            seen.add(base_url)
            candidates.append(base_url)

    remaining_slots = max(settings.max_hosts - len(candidates), 0)
    if remaining_slots == 0:
        return candidates[: settings.max_hosts]

    for cidr in settings.cidrs:
        network = ipaddress.ip_network(cidr, strict=False)
        for ip in _ordered_network_hosts(network):
            if remaining_slots <= 0:
                return candidates[: settings.max_hosts]

            base_url = f"http://{ip}:{settings.port}"
            if base_url in seen:
                continue
            seen.add(base_url)
            candidates.append(base_url)
            remaining_slots -= 1

    return candidates[: settings.max_hosts]


def normalize_candidate(value: str, port: int) -> str | None:
    raw = value.strip()
    if not raw:
        return None

    if raw.startswith("http://") or raw.startswith("https://"):
        return normalize_http_url(raw, default=raw, label="URL candidata de Ollama")
    candidate = f"http://{raw}:{port}"
    return normalize_http_url(candidate, default=candidate, label="URL candidata de Ollama")


def _ordered_network_hosts(network: ipaddress._BaseNetwork) -> list[ipaddress._BaseAddress]:
    hosts = list(network.hosts())
    if not hosts:
        return []

    local_addresses = [
        ip
        for ip in local_ipv4_addresses()
        if ip in network
    ]
    if not local_addresses:
        return hosts

    local_ip = local_addresses[0]
    local_value = int(local_ip)
    first_host = hosts[0]
    gateway_candidates = {int(first_host)}
    if len(hosts) > 1:
        gateway_candidates.add(int(hosts[1]))

    return sorted(
        hosts,
        key=lambda ip: (
            0 if int(ip) in gateway_candidates else 1,
            abs(int(ip) - local_value),
            int(ip),
        ),
    )
