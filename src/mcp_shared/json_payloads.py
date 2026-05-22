from __future__ import annotations

import json
from typing import Any


def load_json_object(content: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(content.strip())
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None
    return payload


def iter_json_objects(content: str):
    decoder = json.JSONDecoder()
    for index, character in enumerate(content):
        if character != "{":
            continue

        try:
            payload, _ = decoder.raw_decode(content[index:])
        except json.JSONDecodeError:
            continue

        if isinstance(payload, dict):
            yield payload
