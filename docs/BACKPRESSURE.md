# Backpressure and drop policy

## Bounded queues

| Location | Bound | Mechanism |
|----------|-------|-----------|
| Redis Streams | ~100k / stream | `MAXLEN ~` on XADD |
| Ingester DB queue | 10,000 | `asyncio.Queue(maxsize=10000)` |

## Drop policy: `drop_oldest`

When the ingester DB queue is full, we **drop the oldest** pending snapshot row before enqueueing the newest.

**Reasoning**: Leaderboard cares about *recent* tail latency; stale 1s buckets are less valuable than current p99 under overload.

Alternative `drop_newest` would preserve history but starve the leaderboard — rejected for judge-facing live UX.

## Observability

Prometheus counters:

- `iicpc_events_dropped_total{reason="db_queue_oldest|db_queue_full"}`
- `iicpc_ingester_queue_size`
- `iicpc_stream_lag{submission_id}`

Scrape: `http://localhost:9100/metrics` (Prometheus configured in `infra/prometheus/prometheus.yml`).
