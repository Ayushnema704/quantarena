"""Integration test: upload sample → run bot → assert leaderboard populates."""
from __future__ import annotations

import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import httpx
import pytest
import redis

ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DIR = ROOT / "examples" / "sample_orderbook"
API_URL = os.environ.get("SUBMISSION_API_URL", "http://localhost:8000")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
SKIP_DOCKER = os.environ.get("SKIP_DOCKER_TESTS", "1") == "1"


def _make_sample_zip() -> bytes:
    import io

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for f in SAMPLE_DIR.iterdir():
            if f.is_file() and f.name != "Dockerfile.template":
                zf.write(f, f.name)
    return buf.getvalue()


@pytest.mark.skipif(SKIP_DOCKER, reason="Docker not available")
@pytest.mark.integration
def test_full_loop():
    """30s loop: submit zip, run bot, check Redis stream + leaderboard."""
    r = redis.from_url(REDIS_URL, decode_responses=True)

    try:
        httpx.get(f"{API_URL}/health", timeout=5).raise_for_status()
    except Exception as e:
        pytest.skip(f"submission API not reachable: {e}")

    zip_bytes = _make_sample_zip()
    resp = httpx.post(
        f"{API_URL}/submit",
        files={"file": ("sample_orderbook.zip", zip_bytes, "application/zip")},
        timeout=180,
    )
    if resp.status_code == 503:
        pytest.skip("docker unavailable for submission API")
    resp.raise_for_status()
    data = resp.json()
    submission_id = data["submission_id"]
    ws_url = data["ws_url"]

    httpx.post(f"{API_URL}/submissions/{submission_id}/test/start", timeout=5)

    time.sleep(3)

    proc = subprocess.Popen(
        [
            sys.executable,
            str(ROOT / "bots" / "limit_order_bot.py"),
            "--submission-id",
            submission_id,
            "--ws-url",
            ws_url,
            "--duration",
            "20",
            "--redis-url",
            REDIS_URL,
            "--interval-ms",
            "25",
        ],
        cwd=str(ROOT),
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    proc.wait(timeout=90)

    stream_len = r.xlen(f"events:{submission_id}")
    assert stream_len > 0, "events should land in Redis stream"

    httpx.post(f"{API_URL}/submissions/{submission_id}/test/complete", timeout=5)

    deadline = time.time() + 45
    score = None
    while time.time() < deadline:
        if r.zcard("leaderboard") > 0:
            score = r.zrevrange("leaderboard", 0, 0, withscores=True)
            break
        time.sleep(1)

    assert score is not None, "leaderboard should populate after load test"
