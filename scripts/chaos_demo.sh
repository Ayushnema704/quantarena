#!/usr/bin/env bash
# Week 3 chaos scenarios — run while platform is up (make demo).
set -euo pipefail
SUBMISSION_ID="${1:?submission id}"
WS_URL="${2:?ws url}"

echo "=== Chaos demo (60s) ==="
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"

echo "[1] Start load in background"
./scripts/run_load_test.sh "$SUBMISSION_ID" "$WS_URL" 45 &
BOT_PID=$!

sleep 10
echo "[2] Kill ingester (expect Redis buffer, recovery on restart)"
docker compose kill ingester || true
sleep 5
docker compose up -d ingester

sleep 10
echo "[3] Mark test failed if contestant stopped"
curl -s -X POST "http://localhost:8000/submissions/${SUBMISSION_ID}/test/complete?failed=true" || true

wait "$BOT_PID" || true
echo "[4] Check leaderboard still has entries"
docker compose exec -T redis redis-cli ZCARD leaderboard

echo "Chaos demo complete. Record screen capture for submission."
