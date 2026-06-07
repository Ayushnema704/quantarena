"""Prometheus metrics shared across services."""
from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, generate_latest

EVENTS_CONSUMED = Counter(
    "iicpc_events_consumed_total",
    "Events consumed from Redis streams",
    ["submission_id"],
)
EVENTS_DROPPED = Counter(
    "iicpc_events_dropped_total",
    "Events dropped due to backpressure",
    ["reason"],
)
INGESTER_QUEUE_SIZE = Gauge("iicpc_ingester_queue_size", "Ingester DB write queue depth")
INGEST_LATENCY = Histogram(
    "iicpc_ingest_batch_seconds",
    "TimescaleDB batch write latency",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
)
STREAM_LAG = Gauge("iicpc_stream_lag", "Unread messages in event stream", ["submission_id"])


def prometheus_response() -> tuple[bytes, str]:
    return generate_latest(), "text/plain; version=0.0.4; charset=utf-8"
