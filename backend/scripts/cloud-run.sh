#!/usr/bin/env sh
set -eu
# Migrations run only through the separately invoked Cloud Run job.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}" --log-level "${LOG_LEVEL:-info}"
