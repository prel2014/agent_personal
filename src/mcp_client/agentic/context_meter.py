from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


DEFAULT_CONTEXT_WINDOW_TOKENS = 131_072


@dataclass(frozen=True)
class ContextUsage:
    estimated_tokens: int
    max_tokens: int

    @property
    def ratio(self) -> float:
        if self.max_tokens <= 0:
            return 0.0
        return min(self.estimated_tokens / self.max_tokens, 1.0)

    @property
    def percent(self) -> int:
        return int(round(self.ratio * 100))


def estimate_context_usage(
    *,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    client_context: dict[str, Any],
    max_tokens: int,
) -> ContextUsage:
    payload = {
        "messages": messages,
        "tools": tools,
        "client_context": client_context,
    }
    return ContextUsage(
        estimated_tokens=estimate_tokens(payload),
        max_tokens=max_tokens,
    )


def estimate_tokens(value: Any) -> int:
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    # Practical approximation for mixed Spanish/English/code payloads.
    return max(1, len(text) // 4)
