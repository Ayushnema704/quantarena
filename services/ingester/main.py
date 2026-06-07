"""Ingester — Redis Streams → HdrHistogram → TimescaleDB + leaderboard + Prometheus."""
from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime, timezone

import asyncpg
import redis.asyncio as aioredis
from aiohttp import web

from shared.events import LEADERBOARD_KEY, LatencyEvent
from shared.metrics import (
    EVENTS_CONSUMED,
    EVENTS_DROPPED,
    INGESTER_QUEUE_SIZE,
    INGEST_LATENCY,
    STREAM_LAG,
    prometheus_response,
)
from shared.scoring import score_breakdown
from services.ingester.histogram import LatencyTracker

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://iicpc:iicpc_dev@localhost:5432/iicpc"
)
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "1000"))
BATCH_INTERVAL_S = float(os.environ.get("BATCH_INTERVAL_S", "0.5"))
FLUSH_INTERVAL_S = float(os.environ.get("FLUSH_INTERVAL_S", "1.0"))
METRICS_PORT = int(os.environ.get("METRICS_PORT", "9100"))
DROP_POLICY = os.environ.get("DROP_POLICY", "drop_oldest")


class Ingester:
    def __init__(self) -> None:
        self.trackers: dict[str, LatencyTracker] = {}
        self.last_ids: dict[str, str] = {}
        self.error_counts: dict[str, int] = {}
        self.db_queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=10_000)
        self.dropped = 0

    def tracker_for(self, submission_id: str) -> LatencyTracker:
        if submission_id not in self.trackers:
            self.trackers[submission_id] = LatencyTracker()
        return self.trackers[submission_id]

    async def load_offsets(self, r: aioredis.Redis) -> None:
        rows = await r.hgetall("ingester:offsets")
        self.last_ids.update(rows)

    async def save_offset(self, r: aioredis.Redis, stream: str, msg_id: str) -> None:
        self.last_ids[stream] = msg_id
        await r.hset("ingester:offsets", stream, msg_id)

    async def process_event(self, submission_id: str, fields: dict) -> None:
        ev = LatencyEvent.from_redis_fields(fields)
        t = self.tracker_for(ev.submission_id)
        if ev.ack_ts_ns is None:
            self.error_counts[submission_id] = self.error_counts.get(submission_id, 0) + 1
        t.record(ev.actual_latency_us, ev.intended_latency_us)
        EVENTS_CONSUMED.labels(submission_id=submission_id).inc()

    async def discover_streams(self, r: aioredis.Redis) -> list[str]:
        return [key async for key in r.scan_iter("events:*")]

    async def consume_loop(self, r: aioredis.Redis) -> None:
        await self.load_offsets(r)
        while True:
            streams = await self.discover_streams(r)
            if not streams:
                await asyncio.sleep(0.5)
                continue

            stream_ids = {s: self.last_ids.get(s, "0-0") for s in streams}
            try:
                results = await r.xread(stream_ids, count=500, block=1000)
            except Exception:
                await asyncio.sleep(1)
                continue

            for stream_name, messages in results:
                sid = stream_name.split(":", 1)[-1]
                lag = await r.xlen(stream_name)
                STREAM_LAG.labels(submission_id=sid).set(lag)
                for msg_id, fields in messages:
                    await self.process_event(sid, fields)
                if messages:
                    last_msg_id = messages[-1][0]
                    await self.save_offset(r, stream_name, last_msg_id)

    async def _correctness_rate(self, r: aioredis.Redis, submission_id: str) -> float:
        raw = await r.get(f"correctness:json:{submission_id}")
        if raw:
            data = json.loads(raw)
            return float(data.get("match_rate", 1.0))
        cr = await r.hget(f"correctness:{submission_id}", "match_rate")
        return float(cr) if cr else 1.0

    async def flush_snapshots(self, r: aioredis.Redis, pool: asyncpg.Pool) -> None:
        while True:
            await asyncio.sleep(FLUSH_INTERVAL_S)
            now = datetime.now(timezone.utc)
            INGESTER_QUEUE_SIZE.set(self.db_queue.qsize())

            for submission_id, tracker in list(self.trackers.items()):
                snap = tracker.snapshot()
                if snap["event_count"] == 0:
                    continue

                name = await r.hget(f"submission:{submission_id}", "name") or submission_id
                errors = self.error_counts.get(submission_id, 0)
                total = int(snap["event_count"]) + errors
                error_rate = errors / max(total, 1)
                variance = snap["p99_us"] - snap["p50_us"]
                match_rate = await self._correctness_rate(r, submission_id)

                breakdown = score_breakdown(
                    p99_us=snap["p99_us"],
                    rps=snap["rps"],
                    fill_match_rate=match_rate,
                    error_rate=error_rate,
                    latency_variance=max(0.0, variance),
                )

                payload = {
                    "id": submission_id,
                    "name": name,
                    "test_status": await r.hget(f"submission:{submission_id}", "test_status")
                    or "unknown",
                    **snap,
                    "speed_score": breakdown.speed,
                    "throughput_score": breakdown.throughput,
                    "correctness_score": breakdown.correctness,
                    "stability_score": breakdown.stability,
                    "composite_score": breakdown.composite,
                    "error_rate": error_rate,
                    "fill_match_rate": match_rate,
                }
                await r.zadd(
                    LEADERBOARD_KEY,
                    {json.dumps(payload): breakdown.composite},
                )
                await r.set(f"snapshot:latest:{submission_id}", json.dumps(payload))

                row = {"time": now, "submission_id": submission_id, **snap, **payload}
                try:
                    if self.db_queue.full() and DROP_POLICY == "drop_oldest":
                        try:
                            self.db_queue.get_nowait()
                            EVENTS_DROPPED.labels(reason="db_queue_oldest").inc()
                        except asyncio.QueueEmpty:
                            pass
                    self.db_queue.put_nowait(row)
                except asyncio.QueueFull:
                    self.dropped += 1
                    EVENTS_DROPPED.labels(reason="db_queue_full").inc()

                tracker.reset_window()
                self.error_counts[submission_id] = 0

    async def db_writer(self, pool: asyncpg.Pool) -> None:
        batch: list[dict] = []
        last_flush = time.monotonic()
        while True:
            try:
                row = await asyncio.wait_for(self.db_queue.get(), timeout=BATCH_INTERVAL_S)
                batch.append(row)
            except asyncio.TimeoutError:
                pass

            should_flush = len(batch) >= BATCH_SIZE or (
                batch and (time.monotonic() - last_flush) >= BATCH_INTERVAL_S
            )
            if should_flush and batch:
                t0 = time.monotonic()
                async with pool.acquire() as conn:
                    await conn.executemany(
                        """
                        INSERT INTO latency_snapshots
                        (time, submission_id, p50_us, p90_us, p99_us,
                         p50_intended_us, p90_intended_us, p99_intended_us,
                         event_count, rps, error_rate,
                         speed_score, throughput_score, correctness_score,
                         stability_score, composite_score)
                        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)
                        """,
                        [
                            (
                                r["time"],
                                r["submission_id"],
                                r["p50_us"],
                                r["p90_us"],
                                r["p99_us"],
                                r.get("p50_intended_us", 0),
                                r.get("p90_intended_us", 0),
                                r.get("p99_intended_us", 0),
                                int(r["event_count"]),
                                r["rps"],
                                r.get("error_rate", 0),
                                r.get("speed_score", 0),
                                r.get("throughput_score", 0),
                                r.get("correctness_score", 0),
                                r.get("stability_score", 0),
                                r.get("composite_score", 0),
                            )
                            for r in batch
                        ],
                    )
                    for r in batch:
                        await conn.execute(
                            """
                            INSERT INTO correctness_results (submission_id, match_rate, total_fills, mismatched)
                            VALUES ($1, $2, $3, $4)
                            ON CONFLICT (submission_id) DO UPDATE
                            SET match_rate = EXCLUDED.match_rate,
                                total_fills = EXCLUDED.total_fills,
                                mismatched = EXCLUDED.mismatched,
                                updated_at = NOW()
                            """,
                            r["submission_id"],
                            r.get("fill_match_rate", 1.0),
                            0,
                            0,
                        )
                INGEST_LATENCY.observe(time.monotonic() - t0)
                batch.clear()
                last_flush = time.monotonic()

    async def run(self) -> None:
        r = aioredis.from_url(REDIS_URL, decode_responses=True)
        pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)

        async def metrics_handler(_request: web.Request) -> web.Response:
            body, ctype = prometheus_response()
            return web.Response(body=body, content_type=ctype.split(";", 1)[0])

        app = web.Application()
        app.router.add_get("/metrics", metrics_handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", METRICS_PORT)
        await site.start()

        await asyncio.gather(
            self.consume_loop(r),
            self.flush_snapshots(r, pool),
            self.db_writer(pool),
        )


def main() -> None:
    asyncio.run(Ingester().run())


if __name__ == "__main__":
    main()
