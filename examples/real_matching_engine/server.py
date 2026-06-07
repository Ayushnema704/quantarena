"""Real WebSocket price-time priority matching engine contestant.

Matches Limit, Market, and Cancel orders and sends executed fills in the websocket JSON ack.
"""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from enum import Enum
import websockets


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class Order:
    order_id: str
    side: Side
    price: float
    qty: int
    ts: int


@dataclass
class Fill:
    buy_order_id: str
    sell_order_id: str
    price: float
    qty: int


class MatchingEngine:
    def __init__(self) -> None:
        self.buys: list[Order] = []
        self.sells: list[Order] = []
        self.orders: dict[str, Order] = {}
        self._seq = 0

    def add_limit(self, order_id: str, side: Side, price: float, qty: int) -> list[Fill]:
        self._seq += 1
        order = Order(order_id, side, price, qty, self._seq)
        self.orders[order_id] = order

        new_fills: list[Fill] = []
        book = self.sells if side == Side.BUY else self.buys

        while order.qty > 0 and book:
            # Sort book: Buy book descending price, oldest first
            # Sell book ascending price, oldest first
            if side == Side.BUY:
                book.sort(key=lambda o: (-o.price, o.ts))
            else:
                book.sort(key=lambda o: (o.price, o.ts))

            best = book[0]
            if side == Side.BUY and best.price > order.price:
                break
            if side == Side.SELL and best.price < order.price:
                break

            qty = min(order.qty, best.qty)
            fill_price = best.price
            buy_id = order.order_id if side == Side.BUY else best.order_id
            sell_id = best.order_id if side == Side.BUY else order.order_id

            f = Fill(buy_id, sell_id, fill_price, qty)
            new_fills.append(f)

            order.qty -= qty
            best.qty -= qty

            if best.qty == 0:
                book.pop(0)
                self.orders.pop(best.order_id, None)

        if order.qty > 0:
            if side == Side.BUY:
                self.buys.append(order)
            else:
                self.sells.append(order)
        else:
            self.orders.pop(order.order_id, None)

        return new_fills

    def add_market(self, order_id: str, side: Side, qty: int) -> list[Fill]:
        price = float("inf") if side == Side.BUY else 0.0
        return self.add_limit(order_id, side, price, qty)

    def cancel(self, order_id: str) -> bool:
        if order_id not in self.orders:
            return False
        order = self.orders.pop(order_id)
        if order.side == Side.BUY:
            self.buys = [o for o in self.buys if o.order_id != order_id]
        else:
            self.sells = [o for o in self.sells if o.order_id != order_id]
        return True


engine = MatchingEngine()


async def handler(ws) -> None:
    async for raw in ws:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            await ws.send(json.dumps({"error": "invalid_json"}))
            continue

        order_id = msg.get("order_id")
        side_str = msg.get("side")
        price = msg.get("price")
        qty = msg.get("qty")
        typ = msg.get("type", "limit")

        fills: list[Fill] = []
        if typ == "cancel" and order_id:
            engine.cancel(order_id)
        elif side_str in ("buy", "sell") and order_id:
            side = Side(side_str)
            if typ == "market":
                fills = engine.add_market(order_id, side, int(qty or 0))
            else:
                fills = engine.add_limit(
                    order_id, side, float(price or 0.0), int(qty or 0)
                )

        ack = {
            "type": "ack",
            "order_id": order_id,
            "side": side_str,
            "price": price,
            "qty": qty,
            "ack_ts_ns": time.time_ns(),
            "received_ts_ns": time.time_ns(),
            "fills": [
                {
                    "buy_order_id": f.buy_order_id,
                    "sell_order_id": f.sell_order_id,
                    "price": f.price,
                    "qty": f.qty,
                }
                for f in fills
            ],
        }
        await ws.send(json.dumps(ack))


async def main() -> None:
    async with websockets.serve(handler, "0.0.0.0", 8765):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
