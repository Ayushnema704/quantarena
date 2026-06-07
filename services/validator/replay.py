"""Replay captured order stream through reference engine and diff fills."""
from __future__ import annotations

import json
from pathlib import Path

from services.validator.matching_engine import MatchingEngine, Side


def replay_orders(orders: list[dict]) -> list[tuple]:
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
    return [
        (f.buy_order_id, f.sell_order_id, f.price, f.qty) for f in engine.fills
    ]


def diff_fills(reference: list[tuple], contestant: list[tuple]) -> float:
    """Correctness score = 1 - (mismatched / total), clamped."""
    total = max(len(reference), 1)
    matched = 0
    for i, ref in enumerate(reference):
        if i < len(contestant) and contestant[i] == ref:
            matched += 1
    mismatched = total - matched
    return max(0.0, min(1.0, 1.0 - mismatched / total))


def replay_file(path: Path) -> list[tuple]:
    orders = json.loads(path.read_text())
    return replay_orders(orders)
