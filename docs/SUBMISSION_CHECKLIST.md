# IICPC 3-Week Checklist — Completion Status

## Week 1 — End-to-end skeleton
- [x] docker-compose: Redis, TimescaleDB, Redpanda
- [x] sample_orderbook fixture
- [x] POST /submit + builder + sandbox
- [x] limit_order_bot + Locust
- [x] Ingester + HdrHistogram + TimescaleDB + leaderboard
- [x] Next.js leaderboard + SSE + p99 chart
- [x] integration test `tests/integration/full_loop.py`

## Week 2 — Depth
- [x] seccomp_profile.json allowlist
- [x] gVisor via `DOCKER_RUNTIME=runsc`
- [x] contestant_net + ws_proxy edge
- [x] pids_limit, ulimits
- [x] THREAT_MODEL.md + sandbox selftest script
- [x] Intended-rate CO-aware bot
- [x] MEASUREMENT.md (full)
- [x] Reference matching engine + hypothesis tests + replay
- [x] distributed_locust.sh + ARCHITECTURE topology
- [x] Backpressure + Prometheus + BACKPRESSURE.md

## Week 3 — Polish
- [x] SCORING.md + sub-scores in UI
- [x] Frontend detail page + mobile CSS + test status
- [x] self_benchmark.py
- [x] chaos_demo.sh + CHAOS.md
- [x] make demo + Terraform + Helm
- [x] ARCHITECTURE.md (blueprint)
- [x] README quickstart + doc links
- [ ] **You record**: 5-min demo video URL in README
- [ ] **You run**: fresh-machine `make demo` validation
- [ ] **You tag**: `v1.0-submission`
