#!/bin/sh
# CogniCare AI - preview/dev entrypoint.
#
# Boots the FastAPI backend (repo root) in the background and runs the
# Next.js frontend dev server in the foreground. The frontend is the
# process the preview platform monitors; it must bind to 0.0.0.0 and use
# the PORT injected by Freebuff ($PORT), defaulting to 3000 locally.
set -e

BACKEND_PORT="${BACKEND_PORT:-8000}"
PORT="${PORT:-3000}"

# The backend requires Supabase credentials at import time (see backend/database/db.py).
# Warn clearly instead of silently failing when keys are missing.
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SERVICE_ROLE_KEY" ]; then
  echo "[cognicare] WARNING: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY are not set."
  echo "[cognicare] The FastAPI backend will NOT start until you add these keys (API Keys tab)."
fi

# 1) FastAPI backend (background)
python3 -m uvicorn main:app --host 0.0.0.0 --port "$BACKEND_PORT" &
BACKEND_PID=$!

# Stop the backend when the preview process exits
trap 'kill "$BACKEND_PID" 2>/dev/null || true' EXIT INT TERM

# 2) Next.js frontend (foreground - this is the preview's primary process)
cd frontend
exec next dev --hostname 0.0.0.0 --port "$PORT"
