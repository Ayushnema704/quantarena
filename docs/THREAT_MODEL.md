# Threat model

Attack surface: untrusted contestant code (arbitrary Python in `server.py`) running on shared hardware.

---

## Assets to protect

- Docker socket (submission API only)
- Redis / TimescaleDB (scores, events)
- Other contestants' containers
- Platform host kernel

---

## Mitigations

| Attack | Mitigation | Verification |
|--------|------------|--------------|
| Fork bomb | `pids_limit=256` | `make sandbox-test` |
| Memory exhaustion | `mem_limit=256m`, `memswap_limit=256m` | container OOM kill |
| CPU starvation | `cpuset_cpus`, `cpu_quota` | pinned cores |
| Container escape | gVisor `runsc` + `cap_drop=ALL` + `no-new-privileges` | `docker inspect` runtime |
| Writable rootfs abuse | `read_only=True` + tmpfs `/tmp` only | write `/etc` fails |
| Network exfiltration | `contestant_net` internal, no egress | no route to redis:6379 |
| Syscall abuse (ptrace, mount) | seccomp allowlist `infra/seccomp_profile.json` | self-test blocked |
| Docker API abuse | not mounted in contestant | only submission_api has socket |

---

## Network isolation architecture

```
[ Bots / Locust ] ──► ws_proxy:8787 (default net)
                          │
                          ▼
              contestant_net (internal)
                          │
                    [ contestant:8765 ]
```

Contestants cannot reach `redis`, `timescaledb`, or `172.x` platform services.

---

## Self-test procedure

```bash
make sandbox-test
# Documents results in docs/SANDBOX_SELFTEST_RESULTS.md
```

Manual attempts:

1. `ptrace` attach → blocked (seccomp/caps)
2. Fork loop → blocked at 256 pids
3. Write `/foo` on read-only rootfs → fails
4. `curl redis:6379` from inside contestant → no route (isolated net)

---

## Residual risk

- gVisor not enabled → runc reduces isolation; **set `DOCKER_RUNTIME=runsc` for submission**
- Seccomp profile too permissive → narrow iteratively from audit logs
- WS proxy compromise → treat as platform component; keep minimal code path
