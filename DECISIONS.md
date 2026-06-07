# Decision log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-05-18 | Redis Streams over Kafka hot path | Week-1 velocity; Redpanda in compose for audit only |
| 2026-05-18 | HdrHistogram dual actual+intended | Coordinated omission correctness |
| 2026-05-18 | Python platform | I/O bound; judge story > raw μs |
| 2026-05-18 | WS edge proxy on dual networks | Isolated contestant_net without exposing Redis |
| 2026-05-18 | drop_oldest on ingester DB queue | Live leaderboard prefers fresh p99 |
| 2026-05-18 | Seccomp allowlist file | Week 2 hardening; Docker-mounted into API |
| 2026-05-18 | Composite weights 35/25/25/15 | Speed-first HFT narrative; correctness tied with throughput |
| 2026-05-18 | Async bot recv for in-flight orders | Sends at intended rate even when WS slow |
| 2026-05-18 | Prometheus on ingester :9100 | `events_dropped_total` for judges/ops |
| 2026-05-18 | Helm + Terraform stubs | Submission IaC deliverable without blocking demo |
