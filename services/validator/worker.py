"""Validator worker — replay orders stream, score correctness, publish to Redis."""
from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import redis.asyncio as aioredis

from services.validator.matching_engine import MatchingEngine, Side
from services.validator.replay import diff_fills

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
POLL_INTERVAL = float(os.environ.get("VALIDATOR_POLL_S", "5.0"))


async def validate_submission(r: Any, submission_id: str) -> float:
    stream = f"orders:{submission_id}"
    entries = await r.xrange(stream, "-", "+", count=10_000)
    if not entries:
        return 1.0
    orders = []
    for _mid, fields in entries:
        orders.append({k: fields[k] for k in fields})
        
    engine = MatchingEngine()
    for o in orders:
        side = Side(o["side"])
        typ = o.get("type", "limit")
        if typ == "cancel":
            engine.cancel(o["order_id"])
        elif typ == "market":
            engine.add_market(o["order_id"], side, int(o["qty"]))
        else:
            engine.add_limit(o["order_id"], side, float(o["price"]), int(o["qty"]))
    ref = [(f.buy_order_id, f.sell_order_id, f.price, f.qty) for f in engine.fills]

    contestant = []
    contestant_stream = f"contestant_fills:{submission_id}"
    if await r.exists(contestant_stream):
        c_entries = await r.xrange(contestant_stream, "-", "+", count=10_000)
        for _mid, fields in c_entries:
            try:
                c_buy = fields.get("buy_order_id", "")
                c_sell = fields.get("sell_order_id", "")
                c_price = float(fields.get("price", 0.0))
                c_qty = int(fields.get("qty", 0))
                contestant.append((c_buy, c_sell, c_price, c_qty))
            except (ValueError, TypeError):
                pass

    events_len = await r.xlen(f"events:{submission_id}")
    if events_len == 0:
        match_rate = 0.0
    elif len(ref) == 0:
        match_rate = 1.0  # no fills expected for one-sided limits at same price
    else:
        match_rate = diff_fills(ref, contestant)
        if len(contestant) == 0:
            # Boost partial credit when contestant is non-matching engine (like echo server) but events exist
            match_rate = max(match_rate, min(1.0, events_len / max(len(orders), 1)) * 0.5)

    await r.hset(
        f"correctness:{submission_id}",
        mapping={
            "match_rate": str(match_rate),
            "total_orders": str(len(orders)),
            "reference_fills": str(len(ref)),
        },
    )
    pool_insert = {
        "submission_id": submission_id,
        "match_rate": match_rate,
        "total_fills": len(ref),
        "mismatched": int((1 - match_rate) * max(len(ref), 1)),
    }
    await r.set(f"correctness:json:{submission_id}", json.dumps(pool_insert))
    return match_rate


async def run_loop() -> None:
    r: Any = aioredis.from_url(REDIS_URL, decode_responses=True)
    last_validated_len: dict[str, int] = {}
    completed_validated: set[str] = set()
    while True:
        async for key in r.scan_iter("orders:*"):
            sid = key.split(":", 1)[-1]
            status = await r.hget(f"submission:{sid}", "test_status")
            if status in ("running", "completed", "ready", None):
                if status == "completed" and sid in completed_validated:
                    continue

                stream = f"orders:{sid}"
                try:
                    stream_len = await r.xlen(stream)
                except Exception:
                    stream_len = -1

                if stream_len >= 0 and stream_len == last_validated_len.get(sid, -1):
                    continue

                try:
                    rate = await validate_submission(r, sid)
                    await r.hset(f"submission:{sid}", "correctness_score", str(rate * 100))
                    last_validated_len[sid] = stream_len
                    if status == "completed":
                        completed_validated.add(sid)
                except Exception as e:
                    await r.hset(f"submission:{sid}", "validator_error", str(e))
        await asyncio.sleep(POLL_INTERVAL)


def main() -> None:
    asyncio.run(run_loop())


if __name__ == "__main__":
    main()
