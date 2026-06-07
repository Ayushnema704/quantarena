"""Locust load generator — drives limit-order bot pattern against contestant WebSocket."""
from __future__ import annotations

import json
import os
import time
import uuid

from locust import User, events, task
from locust.exception import StopUser

try:
    import gevent
    from gevent import monkey

    monkey.patch_all()
except ImportError:
    pass

import redis

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
SUBMISSION_ID = os.environ.get("SUBMISSION_ID", "test")
WS_URL = os.environ.get("WS_URL", "ws://127.0.0.1:8765")
INTERVAL_S = float(os.environ.get("ORDER_INTERVAL_S", "0.01"))

_r = redis.from_url(REDIS_URL, decode_responses=True)
_start_mono = time.monotonic()
_slot = 0


def _intended_send_ts_ns(slot: int) -> int:
    return int((_start_mono + slot * INTERVAL_S) * 1e9)


class WebSocketOrderUser(User):
    abstract = True
    wait_time = lambda self: INTERVAL_S  # noqa: E731

    def on_start(self):
        try:
            import websocket
        except ImportError as e:
            raise StopUser("pip install websocket-client") from e
        self.ws = websocket.create_connection(WS_URL, timeout=5)
        self.slot = 0

    def on_stop(self):
        if hasattr(self, "ws"):
            self.ws.close()

    @task
    def send_order(self):
        global _slot
        _slot += 1
        self.slot = _slot
        intended_send_ts_ns = time.time_ns()
        order_id = str(uuid.uuid4())[:8]
        sent_ts_ns = time.time_ns()
        msg = {
            "order_id": order_id,
            "side": "buy",
            "price": 100.0,
            "qty": 1,
        }
        t0 = time.time()
        self.ws.send(json.dumps(msg))
        raw = self.ws.recv()
        ack_ts_ns = time.time_ns()
        elapsed_ms = (time.time() - t0) * 1000

        try:
            ack = json.loads(raw)
            ack_ts_ns = ack.get("ack_ts_ns", ack_ts_ns)
        except json.JSONDecodeError:
            pass

        fields = {
            "submission_id": SUBMISSION_ID,
            "order_id": order_id,
            "sent_ts_ns": str(sent_ts_ns),
            "received_ts_ns": str(ack_ts_ns),
            "ack_ts_ns": str(ack_ts_ns),
            "intended_send_ts_ns": str(intended_send_ts_ns),
            "bot_id": f"locust-{self.environment.runner.user_count}",
        }
        _r.xadd(f"events:{SUBMISSION_ID}", fields, maxlen=100_000, approximate=True)

        events.request.fire(
            request_type="WS",
            name="order",
            response_time=elapsed_ms,
            response_length=len(raw),
            exception=None,
        )
