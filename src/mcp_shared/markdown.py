from __future__ import annotations

import re
from dataclasses import dataclass


FENCE_RE = re.compile(
    r"```(?P<info>[^\n`]*)\n(?P<body>.*?)\n```",
    re.DOTALL,
)
SINGLE_FENCE_RE = re.compile(
    r"^\s*```(?P<language>[A-Za-z0-9_+.-]*)[^\n`]*\n(?P<body>.*?)\n```\s*$",
    re.DOTALL,
)


@dataclass(frozen=True)
class FencedBlock:
    info: str
    language: str
    body: str


def iter_fenced_blocks(text: str):
    for match in FENCE_RE.finditer(text):
        info = (match.group("info") or "").strip()
        yield FencedBlock(
            info=info,
            language=info.split()[0] if info else "",
            body=match.group("body"),
        )


def strip_single_fence(value: str) -> tuple[str, str] | None:
    match = SINGLE_FENCE_RE.match(value)
    if not match:
        return None
    return (match.group("body"), (match.group("language") or "").strip().lower())
