from __future__ import annotations

import re


DOMAIN_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.IGNORECASE)


def normalize_domain_pattern(pattern: str) -> str:
    value = pattern.strip().lower().rstrip(".")
    if not value:
        raise ValueError("El patron de dominio no puede estar vacio.")

    if "://" in value or "/" in value or ":" in value:
        raise ValueError(f"Patron de dominio invalido: {pattern}")

    if value == "localhost":
        return value

    if value.startswith("*."):
        domain = value[2:]
        _validate_plain_domain(domain, wildcard=True, original=pattern)
        return value

    if "*" in value:
        raise ValueError(f"Wildcard invalido en dominio: {pattern}")

    _validate_plain_domain(value, wildcard=False, original=pattern)
    return value


def normalize_domain_patterns(patterns: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return tuple(normalize_domain_pattern(pattern) for pattern in patterns if pattern.strip())


def domain_matches(hostname: str, pattern: str) -> bool:
    host = hostname.strip().lower().rstrip(".")
    normalized = normalize_domain_pattern(pattern)
    if normalized.startswith("*."):
        suffix = normalized[1:]
        return host.endswith(suffix) and host != normalized[2:]
    return host == normalized


def host_matches_any(hostname: str, patterns: tuple[str, ...] | list[str]) -> bool:
    return any(domain_matches(hostname, pattern) for pattern in patterns)


def _validate_plain_domain(domain: str, *, wildcard: bool, original: str) -> None:
    if domain.startswith(".") or domain.endswith(".") or "." not in domain:
        raise ValueError(f"Dominio demasiado amplio o invalido: {original}")

    labels = domain.split(".")
    if wildcard and len(labels) < 2:
        raise ValueError(f"Wildcard demasiado amplio: {original}")

    if any(not DOMAIN_LABEL_RE.match(label) for label in labels):
        raise ValueError(f"Dominio invalido: {original}")
