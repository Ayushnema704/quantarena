"""Limit order bot — intended-rate scheduling with coordinated-omission-aware timestamps."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
import uuid
from contextlib import suppress
from typing import Any

import redis.asyncio as aioredis
import websockets

from shared.events import LatencyEvent, stream_key

ORDERS_STREAM_PREFIX = "orders:"


class LimitOrderBot:
    """Sends at fixed intervals; records intended latency even when prior request is pending."""

    def __init__(
        self,
        ws_url: str,
        submission_id: str,
        redis_url: str,
        interval_ns: int = 10_000_000,
        bot_id: str = "bot-0",
    ) -> None:
        self.ws_url = ws_url
        self.submission_id = submission_id
        self.redis_url = redis_url
        self.interval_ns = interval_ns
        self.bot_id = bot_id
        self._start_wall_ns = time.time_ns()
        self.errors = 0

    def intended_wall_ts_for_slot(self, slot: int) -> int:
        return self._start_wall_ns + slot * self.interval_ns

    async def run_once(self, ws, r: Any, duration_s: float) -> int:
        deadline = time.monotonic() + duration_s
        count = 0
        slot = 0
        pending: asyncio.Queue[tuple[str, int, int]] = asyncio.Queue()

        async def record_response(
            order_id: str,
            sent_ts_ns: int,
            intended_send_ts_ns: int,
            raw: str | None,
        ) -> None:
            nonlocal count
            if raw:
                try:
                    ack = json.loads(raw)
                    ack_ts_ns = int(ack.get("ack_ts_ns") or time.time_ns())
                    received_ts_ns = int(ack.get("received_ts_ns") or ack_ts_ns)
                    
                    if "fills" in ack and isinstance(ack["fills"], list):
                        for fill in ack["fills"]:
                            asyncio.create_task(
                                r.xadd(
                                    f"contestant_fills:{self.submission_id}",
                                    {
                                        "buy_order_id": str(fill.get("buy_order_id", "")),
                                        "sell_order_id": str(fill.get("sell_order_id", "")),
                                        "price": str(fill.get("price", "")),
                                        "qty": str(fill.get("qty", "")),
                                    },
                                    maxlen=50_000,
                                    approximate=True,
                                )
                            )
                except (json.JSONDecodeError, TypeError, ValueError):
                    ack_ts_ns = None
                    received_ts_ns = None
                    self.errors += 1
            else:
                ack_ts_ns = None
                received_ts_ns = None
                self.errors += 1

            ev = LatencyEvent(
                submission_id=self.submission_id,
                order_id=order_id,
                sent_ts_ns=sent_ts_ns,
                received_ts_ns=received_ts_ns,
                ack_ts_ns=ack_ts_ns,
                intended_send_ts_ns=intended_send_ts_ns,
                bot_id=self.bot_id,
            )
            asyncio.create_task(
                r.xadd(
                    stream_key(self.submission_id),
                    ev.to_redis_fields(),
                    maxlen=100_000,
                    approximate=True,
                )
            )
            count += 1

        receiver_task = asyncio.create_task(self._recv_loop(ws, pending, record_response))

        while time.monotonic() < deadline:
            slot += 1
            intended_send_ts_ns = self.intended_wall_ts_for_slot(slot)
            wait_ns = intended_send_ts_ns - time.time_ns()
            if wait_ns > 0:
                await asyncio.sleep(wait_ns / 1e9)

            order_id = str(uuid.uuid4())[:8]
            sent_ts_ns = time.time_ns()
            side = "buy" if slot % 2 == 0 else "sell"
            price = 100.0 + (slot % 10)
            msg = {
                "type": "limit",
                "order_id": order_id,
                "side": side,
                "price": price,
                "qty": 1,
                "sent_ts_ns": sent_ts_ns,
            }
            asyncio.create_task(
                r.xadd(
                    f"{ORDERS_STREAM_PREFIX}{self.submission_id}",
                    {k: str(v) for k, v in msg.items()},
                    maxlen=50_000,
                    approximate=True,
                )
            )

            try:
                await ws.send(json.dumps(msg))
                await pending.put((order_id, sent_ts_ns, intended_send_ts_ns))
            except websockets.WebSocketException:
                self.errors += 1
                await record_response(order_id, sent_ts_ns, intended_send_ts_ns, None)

        try:
            await pending.join()
        finally:
            receiver_task.cancel()
            with suppress(asyncio.CancelledError):
                await receiver_task
        return count

    async def _recv_loop(self, ws, pending, record_response):
        while True:
            order_id, sent_ts_ns, intended_send_ts_ns = await pending.get()
            try:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                except (asyncio.TimeoutError, websockets.WebSocketException):
                    raw = None
                await record_response(order_id, sent_ts_ns, intended_send_ts_ns, raw)
            finally:
                pending.task_done()

    async def run(self, duration_s: float = 60.0) -> int:
        r: Any = aioredis.from_url(self.redis_url, decode_responses=True)
        async with websockets.connect(self.ws_url) as ws:
            n = await self.run_once(ws, r, duration_s)
        await r.hset(
            f"submission:{self.submission_id}",
            mapping={"bot_errors": str(self.errors), "bot_orders": str(n)},
        )
        return n


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--ws-url", default=os.environ.get("WS_URL", "ws://127.0.0.1:8765"))
    p.add_argument("--submission-id", required=True)
    p.add_argument("--redis-url", default=os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
    p.add_argument("--duration", type=float, default=60.0)
    p.add_argument("--interval-ms", type=float, default=10.0)
    p.add_argument("--bot-id", default="bot-0")
    args = p.parse_args()

    bot = LimitOrderBot(
        ws_url=args.ws_url,
        submission_id=args.submission_id,
        redis_url=args.redis_url,
        interval_ns=int(args.interval_ms * 1_000_000),
        bot_id=args.bot_id,
    )
    n = await bot.run(args.duration)
    print(f"sent {n} orders, errors={bot.errors}")


if __name__ == "__main__":
    asyncio.run(main())
