from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from time import monotonic
from typing import Callable

from .discovery_candidates import (
    candidate_base_urls as build_candidate_base_urls,
)
from .models import NodeAutoPromotionSettings, NodeDiscoverySettings, NodeProbeResult, OllamaNodeConfig
from .probe import OllamaNodeProbe
from .selection import _infer_auto_promoted_nodes

class NodeDiscoveryCache:
    def __init__(
        self,
        *,
        settings: NodeDiscoverySettings,
        probe: OllamaNodeProbe | None = None,
    ) -> None:
        self.settings = settings
        self.probe = probe or OllamaNodeProbe(timeout=settings.timeout)
        self._probe_cache: dict[str, NodeProbeResult] = {}
        self._last_discovery_at: float | None = None

    @property
    def last_discovery_at(self) -> float | None:
        return self._last_discovery_at

    @property
    def detected_node_count(self) -> int:
        return len(self._probe_cache)

    def ensure(self) -> None:
        if not self.settings.enabled:
            return
        self.refresh(force=False)

    def refresh(
        self,
        *,
        force: bool = False,
        progress_callback: Callable[[str, str, NodeProbeResult | None], None] | None = None,
    ) -> list[NodeProbeResult]:
        if not self.settings.enabled:
            return []

        now = monotonic()
        if (
            not force
            and self._last_discovery_at is not None
            and now - self._last_discovery_at < self.settings.ttl_seconds
        ):
            return list(self._probe_cache.values())

        candidates = self.candidate_base_urls()
        self._probe_cache = self._probe_candidates(
            candidates,
            progress_callback=progress_callback,
        )
        self._last_discovery_at = now
        return list(self._probe_cache.values())

    def _probe_candidates(
        self,
        candidates: list[str],
        *,
        progress_callback: Callable[[str, str, NodeProbeResult | None], None] | None = None,
    ) -> dict[str, NodeProbeResult]:
        if len(candidates) <= 1:
            results: dict[str, NodeProbeResult] = {}
            for base_url in candidates:
                _emit_discovery_progress(progress_callback, "start", base_url, None)
                result = self.probe.probe(base_url)
                _emit_discovery_progress(progress_callback, "finish", base_url, result)
                results[base_url] = result
            return results

        max_workers = min(32, len(candidates))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {}
            for base_url in candidates:
                _emit_discovery_progress(progress_callback, "start", base_url, None)
                future_map[executor.submit(self.probe.probe, base_url)] = base_url

            results: dict[str, NodeProbeResult] = {}
            for future in as_completed(future_map):
                base_url = future_map[future]
                result = future.result()
                _emit_discovery_progress(progress_callback, "finish", base_url, result)
                results[result.base_url] = result
        return results

    def probe_state(self, base_url: str) -> NodeProbeResult | None:
        return self._probe_cache.get(base_url)

    def unmanaged_nodes(
        self,
        configured_nodes: list[OllamaNodeConfig],
    ) -> list[dict[str, object]]:
        managed_urls = {node.base_url for node in configured_nodes}
        nodes: list[dict[str, object]] = []
        for base_url, probe_result in sorted(self._probe_cache.items()):
            if base_url in managed_urls:
                continue
            nodes.append(
                {
                    "node_id": f"discovered:{base_url}",
                    "base_url": base_url,
                    "model": None,
                    "roles": [],
                    "keep_alive": None,
                    "think": None,
                    "enabled": False,
                    "priority": None,
                    "is_local": False,
                    "managed": False,
                    "reachable": probe_result.reachable,
                    "available_models": list(probe_result.available_models),
                    "last_error": probe_result.error,
                    "source": probe_result.source,
                }
            )
        return nodes

    def summary(self) -> dict[str, object]:
        return {
            **self.settings.to_dict(),
            "last_discovery_at_monotonic": self._last_discovery_at,
            "detected_node_count": len(self._probe_cache),
        }

    def candidate_base_urls(self) -> list[str]:
        return build_candidate_base_urls(self.settings)

    def auto_promoted_nodes(
        self,
        configured_nodes: list[OllamaNodeConfig],
        settings: NodeAutoPromotionSettings,
    ) -> list[OllamaNodeConfig]:
        if not settings.enabled:
            return []

        managed_urls = {node.base_url for node in configured_nodes}
        promoted: list[OllamaNodeConfig] = []
        for base_url, probe_result in sorted(self._probe_cache.items()):
            if len(promoted) >= settings.max_nodes:
                break
            if base_url in managed_urls:
                continue
            if not probe_result.reachable or not probe_result.available_models:
                continue

            remaining = settings.max_nodes - len(promoted)
            promoted.extend(
                _infer_auto_promoted_nodes(
                    base_url=base_url,
                    available_models=probe_result.available_models,
                    settings=settings,
                    limit=remaining,
                )
            )

        return promoted[: settings.max_nodes]

def _emit_discovery_progress(
    callback: Callable[[str, str, NodeProbeResult | None], None] | None,
    event: str,
    base_url: str,
    result: NodeProbeResult | None,
) -> None:
    if callback is None:
        return
    callback(event, base_url, result)
