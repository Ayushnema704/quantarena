"""Property-based tests for reference matching engine."""
from hypothesis import given, strategies as st

from services.validator.matching_engine import MatchingEngine, Side
from services.validator.replay import diff_fills, replay_orders


@given(
    price=st.floats(min_value=1, max_value=1000, allow_nan=False),
    qty=st.integers(min_value=1, max_value=100),
)
def test_no_fill_worse_than_limit(price, qty):
    engine = MatchingEngine()
    engine.add_limit("b1", Side.BUY, price, qty)
    engine.add_limit("s1", Side.SELL, price + 1, qty)
    assert len(engine.fills) == 0


def test_price_time_priority():
    engine = MatchingEngine()
    engine.add_limit("b1", Side.BUY, 100, 1)
    engine.add_limit("b2", Side.BUY, 100, 1)
    engine.add_limit("s1", Side.SELL, 100, 1)
    assert engine.fills[0].buy_order_id == "b1"


def test_partial_fill_quantity():
    engine = MatchingEngine()
    engine.add_limit("b1", Side.BUY, 100, 10)
    engine.add_limit("s1", Side.SELL, 100, 4)
    engine.add_limit("s2", Side.SELL, 100, 10)
    buy_filled = sum(f.qty for f in engine.fills if f.buy_order_id == "b1")
    assert buy_filled == 10


def test_cancel_removes_order():
    engine = MatchingEngine()
    engine.add_limit("b1", Side.BUY, 100, 5)
    assert engine.cancel("b1")
    engine.add_limit("s1", Side.SELL, 100, 5)
    assert len(engine.fills) == 0


def test_market_order_fills():
    engine = MatchingEngine()
    engine.add_limit("s1", Side.SELL, 100, 3)
    engine.add_market("m1", Side.BUY, 2)
    assert sum(f.qty for f in engine.fills) == 2


def test_replay_deterministic():
    orders = [
        {"type": "limit", "order_id": "b1", "side": "buy", "price": 100, "qty": 2},
        {"type": "limit", "order_id": "s1", "side": "sell", "price": 100, "qty": 2},
    ]
    a = replay_orders(orders)
    b = replay_orders(orders)
    assert a == b
    assert len(a) == 1


def test_diff_fills_score():
    ref = [("b", "s", 100.0, 1)]
    assert diff_fills(ref, ref) == 1.0
    assert diff_fills(ref, []) < 1.0


@given(qty=st.integers(min_value=1, max_value=20))
def test_total_filled_quantity_conserved(qty):
    engine = MatchingEngine()
    engine.add_limit("b1", Side.BUY, 50, qty)
    engine.add_limit("s1", Side.SELL, 50, qty)
    assert sum(f.qty for f in engine.fills) == qty
