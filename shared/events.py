"""Event schema shared across bots, ingester, and API."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class LatencyEvent:
    submission_id: str
    order_id: str
    sent_ts_ns: int
    received_ts_ns: int | None
    ack_ts_ns: int | None
    intended_send_ts_ns: int
    bot_id: str = "default"

    @property
    def actual_latency_us(self) -> float | None:
        if self.ack_ts_ns is None or self.sent_ts_ns is None:
            return None
        return (self.ack_ts_ns - self.sent_ts_ns) / 1000.0

    @property
    def intended_latency_us(self) -> float | None:
        if self.ack_ts_ns is None:
            return None
        return (self.ack_ts_ns - self.intended_send_ts_ns) / 1000.0

    def to_redis_fields(self) -> dict[str, str]:
        d = asdict(self)
        return {k: str(v) if v is not None else "" for k, v in d.items()}

    @classmethod
    def from_redis_fields(cls, fields: dict[str, str | bytes]) -> LatencyEvent:
        def _get(k: str) -> str:
            v = fields.get(k, fields.get(k.encode(), b""))
            if isinstance(v, bytes):
                return v.decode()
            return str(v or "")

        def _int(k: str) -> int | None:
            s = _get(k)
            return int(s) if s else None

        return cls(
            submission_id=_get("submission_id"),
            order_id=_get("order_id"),
            sent_ts_ns=int(_get("sent_ts_ns") or 0),
            received_ts_ns=_int("received_ts_ns"),
            ack_ts_ns=_int("ack_ts_ns"),
            intended_send_ts_ns=int(_get("intended_send_ts_ns") or 0),
            bot_id=_get("bot_id") or "default",
        )


def stream_key(submission_id: str) -> str:
    return f"events:{submission_id}"


LEADERBOARD_KEY = "leaderboard"
