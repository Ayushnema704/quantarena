#!/usr/bin/env bash
# Run bot against a submission for N seconds
set -euo pipefail
SUBMISSION_ID="${1:?submission id}"
WS_URL="${2:?ws url}"
DURATION="${3:-30}"
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
python3 bots/limit_order_bot.py \
  --submission-id "$SUBMISSION_ID" \
  --ws-url "$WS_URL" \
  --duration "$DURATION" \
  --redis-url "$REDIS_URL"
