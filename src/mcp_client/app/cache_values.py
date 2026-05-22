from __future__ import annotations

import json
from typing import Any


def parse_cache_value(raw_value: str) -> Any:
    try:
        return json.loads(raw_value)
    except json.JSONDecodeError:
        return raw_value
