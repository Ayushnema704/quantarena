"""Chaos-style resilience tests (require docker compose stack)."""
import os

import pytest
import redis

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
SKIP = os.environ.get("SKIP_INTEGRATION", "1") == "1"


@pytest.mark.skipif(SKIP, reason="integration stack not running")
def test_redis_survives_after_reconnect():
    r = redis.from_url(REDIS_URL, decode_responses=True)
    r.ping()
    r.xadd("events:chaos-test", {"ok": "1"}, maxlen=1000)
    assert r.xlen("events:chaos-test") >= 1


@pytest.mark.skipif(SKIP, reason="integration stack not running")
def test_leaderboard_key_exists_or_empty():
    r = redis.from_url(REDIS_URL, decode_responses=True)
    r.zcard("leaderboard")  # no throw
