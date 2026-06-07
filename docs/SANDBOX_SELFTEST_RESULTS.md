# Sandbox self-test results

Run `make sandbox-test` to regenerate this file.

| Test | Expected |
|------|----------|
| fork_bomb (pids_limit) | BLOCKED |
| ptrace (seccomp/caps) | BLOCKED |
| readonly_root write | BLOCKED |
| curl platform Redis from contestant | BLOCKED (no route on isolated net) |

## gVisor verification

```bash
export DOCKER_RUNTIME=runsc
make demo
docker inspect iicpc-<submission_id> --format '{{.HostConfig.Runtime}}'
# expect: runsc
```

## Notes

Document any ALLOWED (unexpected) results and tighten seccomp before submission.
