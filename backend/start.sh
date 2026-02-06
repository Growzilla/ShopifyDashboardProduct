#!/bin/sh
# Run Alembic migrations then start the server
set -e

echo "[STARTUP] Running database migrations..."
python -m alembic upgrade head || echo "[STARTUP] Migration failed (may be first run or DB unavailable)"

echo "[STARTUP] Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
