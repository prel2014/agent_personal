from __future__ import annotations

import json
import subprocess
from typing import Any
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

from .domains import host_matches_any, normalize_domain_patterns
from .html_extract import extract_html
from .models import NetworkPolicy
from .network import assert_url_allowed


USER_AGENT = "mcp-sandbox-web/0.1"


def run_operation(
    operation: str,
    arguments: dict[str, Any],
    policy: NetworkPolicy,
    *,
    timeout: float,
) -> Any:
    if operation == "web_fetch":
        return web_fetch(policy=policy, timeout=timeout, **arguments)
    if operation == "web_search":
        return web_search(policy=policy, timeout=timeout, **arguments)
    if operation == "sandbox_run":
        return sandbox_run(timeout=timeout, **arguments)
    raise ValueError(f"Operacion de sandbox no soportada: {operation}")


def web_fetch(
    *,
    url: str,
    policy: NetworkPolicy,
    timeout: float,
    max_bytes: int | None = None,
    extract_mode: str = "text",
) -> dict[str, Any]:
    assert_url_allowed(url, policy)
    byte_limit = _effective_byte_limit(max_bytes, policy.max_response_bytes)
    request = Request(
        url,
        headers={
            "Accept": "text/html,application/xhtml+xml,text/plain,application/json,*/*;q=0.8",
            "User-Agent": USER_AGENT,
        },
        method="GET",
    )

    with urlopen(request, timeout=timeout) as response:
        final_url = response.geturl()
        assert_url_allowed(final_url, policy)
        raw = response.read(byte_limit + 1)
        truncated = len(raw) > byte_limit
        if truncated:
            raw = raw[:byte_limit]
        content_type = response.headers.get("content-type", "")
        status_code = getattr(response, "status", response.getcode())

    charset = _charset_from_content_type(content_type)
    text = raw.decode(charset, errors="replace")
    parsed = _extract_payload(text, final_url, content_type, extract_mode)

    return {
        "url": url,
        "final_url": final_url,
        "status_code": int(status_code),
        "content_type": content_type,
        "title": parsed["title"],
        "text": parsed["text"],
        "links": parsed["links"],
        "bytes_read": len(raw),
        "truncated": truncated,
        "untrusted": True,
    }


def web_search(
    *,
    query: str,
    policy: NetworkPolicy,
    timeout: float,
    provider: str = "searxng",
    base_url: str | None = None,
    max_results: int = 5,
    domains: list[str] | None = None,
    recency_days: int | None = None,
) -> dict[str, Any]:
    if provider != "searxng":
        raise ValueError("Proveedor de busqueda no soportado. Usa searxng.")
    if not base_url:
        raise ValueError(
            "web_search requiere MCP_WEB_SEARCH_BASE_URL apuntando a una instancia SearxNG."
        )

    search_url = _build_searxng_url(base_url, query, recency_days)
    assert_url_allowed(search_url, policy)
    request = Request(
        search_url,
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="GET",
    )

    with urlopen(request, timeout=timeout) as response:
        raw = response.read(policy.max_response_bytes + 1)
        if len(raw) > policy.max_response_bytes:
            raise RuntimeError("La respuesta de busqueda excede web_max_response_bytes.")
        payload = json.loads(raw.decode("utf-8", errors="replace"))

    domain_patterns = normalize_domain_patterns(tuple(domains or ()))
    results = []
    for item in payload.get("results", []):
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "")
        if not url:
            continue
        host = urlparse(url).hostname or ""
        if domain_patterns and not host_matches_any(host, domain_patterns):
            continue
        results.append(
            {
                "title": str(item.get("title") or ""),
                "url": url,
                "snippet": str(item.get("content") or item.get("snippet") or ""),
                "source": str(item.get("engine") or "searxng"),
            }
        )
        if len(results) >= max(1, int(max_results)):
            break

    return {
        "query": query,
        "provider": provider,
        "results": results,
        "citations": [result["url"] for result in results],
        "untrusted": True,
    }


def sandbox_run(
    *,
    command: str,
    timeout: float,
    cwd: str | None = None,
) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return {
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _effective_byte_limit(max_bytes: int | None, policy_limit: int) -> int:
    values = [policy_limit]
    if max_bytes is not None:
        values.append(int(max_bytes))
    return max(1, min(values))


def _charset_from_content_type(content_type: str) -> str:
    for part in content_type.split(";"):
        item = part.strip()
        if item.lower().startswith("charset="):
            return item.split("=", 1)[1].strip() or "utf-8"
    return "utf-8"


def _extract_payload(
    text: str,
    final_url: str,
    content_type: str,
    extract_mode: str,
) -> dict[str, Any]:
    normalized_mode = (extract_mode or "text").strip().lower()
    if normalized_mode == "html":
        return {"title": "", "text": text, "links": []}

    if normalized_mode == "metadata":
        parsed = extract_html(text, final_url) if "html" in content_type.lower() else {}
        return {
            "title": str(parsed.get("title") or ""),
            "text": "",
            "links": parsed.get("links") or [],
        }

    if "html" in content_type.lower() or "<html" in text[:500].lower():
        return extract_html(text, final_url)

    return {"title": "", "text": text, "links": []}


def _build_searxng_url(base_url: str, query: str, recency_days: int | None) -> str:
    params = {"q": query, "format": "json"}
    time_range = _searxng_time_range(recency_days)
    if time_range:
        params["time_range"] = time_range
    return urljoin(base_url.rstrip("/") + "/", "search") + "?" + urlencode(params)


def _searxng_time_range(recency_days: int | None) -> str | None:
    if recency_days is None:
        return None
    days = int(recency_days)
    if days <= 1:
        return "day"
    if days <= 7:
        return "week"
    if days <= 31:
        return "month"
    return "year"
