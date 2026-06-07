# Measurement methodology

This document is the highest-value technical artifact for judges. It explains *how* we measure latency correctly under load.

---

## Coordinated omission (plain English)

When load generators only send the next request after the previous one completes, the system naturally sends fewer requests during slow periods. Tail latency percentiles look artificially good because the load **coordinates with** system slowness — omissions hide pain.

Gil Tene's ["How NOT to Measure Latency"](https://www.youtube.com/watch?v=lJ8ydIuPFeU) is the canonical reference.

---

## How we avoid it

1. **Intended-rate scheduler** — Bots wake on fixed slot boundaries (`interval_ns`), independent of in-flight requests.
2. **`intended_send_ts_ns`** — Wall-clock time when the order *should* have been sent.
3. **Dual histograms** — `actual` (ack − sent) and `intended` (ack − intended_send) in `LatencyTracker`.
4. **Non-blocking recv** — Responses are recorded asynchronously so sends are not blocked by slow acks.

Implementation: `bots/limit_order_bot.py`.

---

## HdrHistogram — why not sorted arrays?

- **Memory**: O(1) bucket structure vs O(n) samples
- **Speed**: O(1) record; percentiles without full sort each flush
- **Range**: Configurable `lowest_trackable` / `highest_trackable` / `significant_digits`

We use the Python `hdrhistogram` package (`hdrh.histogram.HdrHistogram`).

Percentiles: `hist.get_value_at_percentile(99)` → p99 in microseconds.

---

## Timestamp capture

| Field | Source | Purpose |
|-------|--------|---------|
| `intended_send_ts_ns` | Slot scheduler | CO-correct intended latency |
| `sent_ts_ns` | Immediately before `ws.send` | Actual send time |
| `ack_ts_ns` | Contestant JSON or client recv | Completion |
| `received_ts_ns` | Contestant server | Server-side receive (preferred when available) |

**Platform edge vs in-container ack**: We prefer contestant-provided `ack_ts_ns` when present (measures their processing). Client receive is fallback (includes network RTT — documented bias).

---

## Clock synchronization

- **Single host bots**: `time.time_ns()` sufficient
- **Distributed Locust workers**: NTP-synced VMs; residual skew **~1ms typical**
- **Never mix monotonic across hosts** for cross-machine comparison; use wall clock with NTP

---

## Known error sources

| Source | Magnitude | Mitigation |
|--------|-----------|------------|
| NTP skew (multi-region) | ~0.5–2ms | Document bar; same-region workers for finals |
| WS framing + JSON | 10–100µs | Negligible vs trading latency |
| Redis XADD | <1ms LAN | Colocate bots with platform when possible |
| Python GIL on bot | variable | Async I/O; multiple workers |

---

## Percentile computation pipeline

1. Ingester reads `events:<submission_id>` from Redis
2. Records µs into actual + intended HdrHistograms
3. Every 1s: snapshot p50/p90/p99 → leaderboard JSON + TimescaleDB hypertable
4. Frontend charts p99 over time from `latency_snapshots`

---

## Stability and error metrics

- **error_rate** = orders without ack / total attempts
- **latency_variance** = p99 − p50 (spread proxy)
- Both feed `stability_score` in `shared/scoring.py`
