from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .domains import normalize_domain_patterns


@dataclass(frozen=True)
class NetworkPolicy:
    allowed_domains: tuple[str, ...] = ()
    denied_domains: tuple[str, ...] = ()
    block_private_networks: bool = True
    max_response_bytes: int = 2_000_000

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed_domains": list(self.allowed_domains),
            "denied_domains": list(self.denied_domains),
            "block_private_networks": self.block_private_networks,
            "max_response_bytes": self.max_response_bytes,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "NetworkPolicy":
        return cls(
            allowed_domains=normalize_domain_patterns(
                tuple(str(item) for item in payload.get("allowed_domains", ()))
            ),
            denied_domains=normalize_domain_patterns(
                tuple(str(item) for item in payload.get("denied_domains", ()))
            ),
            block_private_networks=bool(payload.get("block_private_networks", True)),
            max_response_bytes=int(payload.get("max_response_bytes", 2_000_000)),
        )


@dataclass(frozen=True)
class SandboxOptions:
    backend: str
    image: str
    timeout: float
    base_dir: Path
    web_search_provider: str = "searxng"
    web_search_base_url: str | None = None


@dataclass(frozen=True)
class SandboxRequest:
    operation: str
    arguments: dict[str, Any]
    network_policy: NetworkPolicy

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "arguments": self.arguments,
            "network_policy": self.network_policy.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SandboxRequest":
        return cls(
            operation=str(payload["operation"]),
            arguments=dict(payload.get("arguments", {})),
            network_policy=NetworkPolicy.from_dict(dict(payload.get("network_policy", {}))),
        )


@dataclass(frozen=True)
class SandboxResponse:
    success: bool
    result: Any | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SandboxResponse":
        return cls(
            success=bool(payload.get("success")),
            result=payload.get("result"),
            error=payload.get("error"),
        )
