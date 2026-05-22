from __future__ import annotations

import re
from typing import Any

SENSITIVE_KEY_RE = re.compile(
    r"(api[_-]?key|access[_-]?token|auth|authorization|bearer|password|secret|token)",
    re.IGNORECASE,
)

SENSITIVE_LINE_RE = re.compile(
    r"(?im)\b(api[_-]?key|access[_-]?token|authorization|password|secret|token)\b"
    r"\s*[:=]\s*([^\s,;]+)"
)

PRIVATE_KEY_BLOCK_RE = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
    re.DOTALL,
)

def redact_payload(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if SENSITIVE_KEY_RE.search(key_text):
                redacted[key_text] = "<redacted>"
            else:
                redacted[key_text] = redact_payload(item)
        return redacted

    if isinstance(value, list):
        return [redact_payload(item) for item in value]

    if isinstance(value, tuple):
        return [redact_payload(item) for item in value]

    if isinstance(value, str):
        return redact_text(value)

    return value

def redact_text(value: str) -> str:
    redacted = PRIVATE_KEY_BLOCK_RE.sub("<redacted private key>", value)
    return SENSITIVE_LINE_RE.sub(
        lambda match: f"{match.group(1)}=<redacted>",
        redacted,
    )
