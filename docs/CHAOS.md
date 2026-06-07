# Chaos testing

## Scenarios

| # | Fault | Expected behavior |
|---|-------|-------------------|
| 1 | Kill Locust/bot worker mid-test | Other workers continue; leaderboard updates |
| 2 | Kill ingester | Redis Streams buffer; ingester resumes from `ingester:offsets` |
| 3 | Kill contestant container | `test_status=failed`; platform stays up |

## Run

```bash
make demo
# submit + get id/url, then:
./scripts/chaos_demo.sh <submission_id> <ws_url>
```

Record 1-minute screen capture for submission backup.

## Metrics to watch

- `iicpc_events_dropped_total` — should stay flat or spike only under overload
- `iicpc_stream_lag` — recovers after ingester restart
- Leaderboard `ZCARD` — non-zero after test
