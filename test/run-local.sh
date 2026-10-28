#!/usr/bin/env bash
# Phase A: build the frontend, start the backend on a fresh temp DB with the mock LLM,
# run the Playwright suite against it, then stop the server.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${PORT:-8012}"
TMP="$(mktemp -d)"

(cd "$ROOT/frontend" && npm run build >/dev/null)

cd "$ROOT/backend"
DB_PATH="$TMP/finally.db" STATIC_DIR="$ROOT/frontend/out" LLM_MOCK=true \
  uv run uvicorn app.main:app --host 127.0.0.1 --port "$PORT" >"$TMP/server.log" 2>&1 &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null; echo "server log: $TMP/server.log"' EXIT

for _ in $(seq 1 30); do
  curl -sf "http://127.0.0.1:$PORT/api/health" >/dev/null && break
  sleep 0.5
done

cd "$ROOT/test"
BASE_URL="http://127.0.0.1:$PORT" npx playwright test "$@"
