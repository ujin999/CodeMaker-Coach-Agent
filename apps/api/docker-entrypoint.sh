#!/bin/sh
set -e

echo "[entrypoint] running database migrations..."
alembic upgrade head

echo "[entrypoint] starting API server..."
exec uvicorn app.main:app --host "${API_HOST:-0.0.0.0}" --port "${API_PORT:-10000}"
