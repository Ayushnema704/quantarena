#!/usr/bin/env bash
# Week 2 distributed Locust — master local, workers on remote VMs.
# Usage: ./scripts/distributed_locust.sh <master|worker> [master-host]
set -euo pipefail
MODE="${1:-master}"
MASTER="${2:-127.0.0.1}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export SUBMISSION_ID="${SUBMISSION_ID:?set SUBMISSION_ID}"
export WS_URL="${WS_URL:?set WS_URL}"
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"

if [[ "$MODE" == "master" ]]; then
  echo "Starting Locust master on :8089"
  locust -f services/load_generator/locustfile.py --master --web-port 8089
else
  echo "Starting worker → $MASTER"
  locust -f services/load_generator/locustfile.py --worker --master-host="$MASTER"
fi
