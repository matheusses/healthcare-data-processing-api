#!/usr/bin/env bash
# Initial DB setup: load env, wait for Postgres, run Alembic migrations.
# Run from project root. Requires: .env (or env vars), uv (or python), alembic.
# Usage: ./scripts/initial_db.sh   or   bash scripts/initial_db.sh

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Load .env if present (POSIX-style; export for child processes)
if [ -f .env ]; then
  set -a
  # shellcheck source=/dev/null
  source .env
  set +a
fi

# Defaults aligned with docker-compose and .env.example
export POSTGRES_USER="${POSTGRES_USER:-user}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-password}"
export POSTGRES_DB="${POSTGRES_DB:-healthcare}"
export PGHOST="${PGHOST:-localhost}"
export PGPORT="${PGPORT:-5434}"

# Build DATABASE_URL if unset or still containing placeholders
if [ -z "${DATABASE_URL:-}" ] || echo "${DATABASE_URL:-}" | grep -q '\${'; then
  export DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${PGHOST}:${PGPORT}/${POSTGRES_DB}"
fi

echo "Waiting for Postgres at ${PGHOST}:${PGPORT} (user ${POSTGRES_USER}, db ${POSTGRES_DB})..."
if command -v uv &>/dev/null; then
  uv run python scripts/wait_for_db.py
else
  python scripts/wait_for_db.py
fi

echo "Running Alembic migrations..."
if command -v uv &>/dev/null; then
  uv run alembic upgrade head
else
  alembic upgrade head
fi

echo "Initial DB setup complete."
