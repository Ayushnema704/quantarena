#!/usr/bin/env bash
# Week 2: attempt common escape/abuse patterns against sandbox policy (document results).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== Sandbox self-test ==="
echo "Runtime: ${DOCKER_RUNTIME:-runc}"
echo "Seccomp: infra/seccomp_profile.json"

if ! command -v docker >/dev/null; then
  echo "SKIP: docker not installed"
  exit 0
fi

REPORT="$ROOT/docs/SANDBOX_SELFTEST_RESULTS.md"
mkdir -p docs

{
  echo "# Sandbox self-test results"
  echo "Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo
} > "$REPORT"

_try() {
  local name="$1"
  shift
  echo -n "  $name ... "
  if "$@" >/dev/null 2>&1; then
    echo "ALLOWED (unexpected)" | tee -a "$REPORT"
    echo "- **$name**: ALLOWED (unexpected)" >> "$REPORT"
  else
    echo "BLOCKED (expected)" | tee -a "$REPORT"
    echo "- **$name**: BLOCKED (expected)" >> "$REPORT"
  fi
}

echo "1. Fork bomb in contestant (should hit pids_limit)"
_try "fork_bomb" docker run --rm --pids-limit 256 python:3.11-slim python -c \
  "import os; [os.fork() or 0]"

echo "2. ptrace (should fail seccomp/caps)"
_try "ptrace" docker run --rm --cap-drop ALL python:3.11-slim python -c \
  "import ctypes; ctypes.CDLL(None).ptrace(0,0,0,0)"

echo "3. Write to rootfs (read-only)"
_try "readonly_root" docker run --rm --read-only python:3.11-slim touch /foo

echo "Done. See $REPORT"
