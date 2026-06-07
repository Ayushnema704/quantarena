# Scoring

## Composite formula

```
final = w1 × speed_score + w2 × throughput_score + w3 × correctness_score + w4 × stability_score
```

**Default weights**: `w1=0.35`, `w2=0.25`, `w3=0.25`, `w4=0.15`

Rationale: latency (speed) is primary for HFT narrative; throughput and correctness equally critical; stability prevents "fast but flaky" submissions from winning.

---

## Sub-scores (0–100 each)

### speed_score = f(p99_latency)

Lower p99 is better. Normalized against baseline 50ms:

```
speed = clamp(0, 100, (baseline / p99) × 50)
```

### throughput_score = f(sustained_rps)

Higher RPS is better, target 1000 RPS = 100 points:

```
throughput = clamp(0, 100, (rps / 1000) × 100)
```

### correctness_score = f(fill_match_rate)

From validator replay vs reference engine:

```
correctness = fill_match_rate × 100
```

### stability_score = f(error_rate, latency_variance)

Penalizes timeouts and wide p99−p50 spread:

```
stability = max(0, 100 − error_rate×1000 − variance/1000)
```

---

## Leaderboard storage

Redis sorted set `leaderboard` — member JSON includes all sub-scores for UI sparklines and detail pages.

---

## Implementation

`shared/scoring.py` → `score_breakdown()` used by ingester on each 1s flush.

---

## Tuning for judges

Weights are configurable via env `SCORE_WEIGHTS=0.35,0.25,0.25,0.15` (future). Document any changes in `DECISIONS.md`.
