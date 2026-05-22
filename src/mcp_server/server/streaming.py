from __future__ import annotations


def _heartbeat_chunk() -> dict[str, object]:
    return {
        "ok": True,
        "heartbeat": True,
        "done": False,
        "message": {"role": "assistant", "content": ""},
    }


def _stream_heartbeat_interval(request_timeout: float) -> float:
    if request_timeout <= 0:
        return 10.0
    return max(1.0, min(15.0, request_timeout / 6.0))
