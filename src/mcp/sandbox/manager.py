from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from .domains import host_matches_any
from .docker_backend import DockerSandboxBackend
from .models import NetworkPolicy, SandboxOptions, SandboxResponse
from .operations import run_operation


class LocalSandboxBackend:
    def __init__(self, *, timeout: float) -> None:
        self.timeout = timeout

    def run(
        self,
        operation: str,
        arguments: dict[str, Any],
        policy: NetworkPolicy,
    ) -> SandboxResponse:
        try:
            return SandboxResponse(
                success=True,
                result=run_operation(operation, arguments, policy, timeout=self.timeout),
            )
        except Exception as exc:
            return SandboxResponse(success=False, error=str(exc))


class SandboxManager:
    def __init__(self, options: SandboxOptions, policy: NetworkPolicy) -> None:
        self.options = options
        self.policy = policy
        if options.backend == "local":
            self.backend = LocalSandboxBackend(timeout=options.timeout)
        elif options.backend == "docker":
            self.backend = DockerSandboxBackend(
                image=options.image,
                base_dir=options.base_dir,
                timeout=options.timeout,
            )
        else:
            raise ValueError(f"Backend de sandbox no soportado: {options.backend}")

    @classmethod
    def from_runtime_config(cls, config) -> "SandboxManager":
        options = SandboxOptions(
            backend=config.sandbox_backend,
            image=config.sandbox_image,
            timeout=config.sandbox_timeout,
            base_dir=config.base_dir,
            web_search_provider=config.web_search_provider,
            web_search_base_url=config.web_search_base_url,
        )
        policy = NetworkPolicy(
            allowed_domains=tuple(config.web_allowed_domains),
            denied_domains=tuple(config.web_denied_domains),
            block_private_networks=config.web_block_private_networks,
            max_response_bytes=int(config.web_max_response_bytes),
        )
        return cls(options, policy)

    def web_fetch(
        self,
        *,
        url: str,
        max_bytes: int | None = None,
        extract_mode: str = "text",
    ) -> SandboxResponse:
        return self.backend.run(
            "web_fetch",
            {
                "url": url,
                "max_bytes": max_bytes,
                "extract_mode": extract_mode,
            },
            self.policy,
        )

    def web_search(
        self,
        *,
        query: str,
        max_results: int = 5,
        domains: list[str] | None = None,
        recency_days: int | None = None,
    ) -> SandboxResponse:
        search_policy = self._policy_with_search_host()
        return self.backend.run(
            "web_search",
            {
                "query": query,
                "provider": self.options.web_search_provider,
                "base_url": self.options.web_search_base_url,
                "max_results": max_results,
                "domains": domains,
                "recency_days": recency_days,
            },
            search_policy,
        )

    def sandbox_run(
        self,
        *,
        command: str,
        cwd: str | None = None,
    ) -> SandboxResponse:
        return self.backend.run(
            "sandbox_run",
            {"command": command, "cwd": cwd},
            self.policy,
        )

    def _policy_with_search_host(self) -> NetworkPolicy:
        base_url = self.options.web_search_base_url
        if not base_url or not self.policy.allowed_domains:
            return self.policy

        host = urlparse(base_url).hostname
        if not host or host_matches_any(host, self.policy.allowed_domains):
            return self.policy

        return NetworkPolicy(
            allowed_domains=(*self.policy.allowed_domains, host),
            denied_domains=self.policy.denied_domains,
            block_private_networks=self.policy.block_private_networks,
            max_response_bytes=self.policy.max_response_bytes,
        )
