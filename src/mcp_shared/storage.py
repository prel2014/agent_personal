from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_text() -> str:
    return utc_now().isoformat()


def new_prefixed_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def new_uuid_text() -> str:
    return str(uuid.uuid4())


def to_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def from_json_dict(raw_value: str | None) -> dict[str, Any]:
    if not raw_value:
        return {}

    value = json.loads(raw_value)
    if isinstance(value, dict):
        return value
    return {}
