"""Reference price-time priority matching engine for correctness scoring."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from heapq import heappop, heappush


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass(order=True)
class Order:
    sort_key: tuple
    order_id: str = field(compare=False)
    side: Side = field(compare=False)
    price: float = field(compare=False)
    qty: int = field(compare=False)
    ts: int = field(compare=False, default=0)


@dataclass
class Fill:
    buy_order_id: str
    sell_order_id: str
    price: float
    qty: int
    ts: int


class MatchingEngine:
    def __init__(self) -> None:
        self.buys: list[Order] = []
        self.sells: list[Order] = []
        self.orders: dict[str, Order] = {}
        self.fills: list[Fill] = []
        self._seq = 0

    def _next_ts(self) -> int:
        self._seq += 1
        return self._seq

    def add_limit(self, order_id: str, side: Side, price: float, qty: int) -> list[Fill]:
        ts = self._next_ts()
        order = Order(
            sort_key=self._sort_key(side, price, ts),
            order_id=order_id,
            side=side,
            price=price,
            qty=qty,
            ts=ts,
        )
        self.orders[order_id] = order
        return self._match(order)

    def add_market(self, order_id: str, side: Side, qty: int) -> list[Fill]:
        price = float("inf") if side == Side.BUY else 0.0
        return self.add_limit(order_id, side, price, qty)

    def cancel(self, order_id: str) -> bool:
        if order_id not in self.orders:
            return False
        del self.orders[order_id]
        self.buys = [o for o in self.buys if o.order_id != order_id]
        self.sells = [o for o in self.sells if o.order_id != order_id]
        return True

    def _sort_key(self, side: Side, price: float, ts: int) -> tuple:
        if side == Side.BUY:
            return (-price, ts)
        return (price, ts)

    def _match(self, incoming: Order) -> list[Fill]:
        new_fills: list[Fill] = []
        book = self.sells if incoming.side == Side.BUY else self.buys

        while incoming.qty > 0 and book:
            best = book[0]
            if incoming.side == Side.BUY and best.price > incoming.price:
                break
            if incoming.side == Side.SELL and best.price < incoming.price:
                break
            if best.order_id not in self.orders:
                heappop(book)
                continue

            heappop(book)
            qty = min(incoming.qty, best.qty)
            fill_price = best.price
            ts = self._next_ts()
            buy_id = incoming.order_id if incoming.side == Side.BUY else best.order_id
            sell_id = best.order_id if incoming.side == Side.BUY else incoming.order_id
            f = Fill(buy_id, sell_id, fill_price, qty, ts)
            self.fills.append(f)
            new_fills.append(f)

            incoming.qty -= qty
            best.qty -= qty
            if best.qty > 0:
                heappush(book, best)
            else:
                self.orders.pop(best.order_id, None)

        if incoming.qty > 0:
            heappush(self.buys if incoming.side == Side.BUY else self.sells, incoming)
        else:
            self.orders.pop(incoming.order_id, None)
        return new_fills
