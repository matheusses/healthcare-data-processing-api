#!/usr/bin/env bash
# Seed the database with sample patients and notes (optional, for demo/local dev).
# Run after ./scripts/initial_db.sh. Does not overwrite existing data by default.
# Usage: ./scripts/seed_db.sh [--force]

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

if [ -f .env ]; then
  set -a
  # shellcheck source=/dev/null
  source .env
  set +a
fi

if command -v uv &>/dev/null; then
  uv run python scripts/seed_sample_data.py "$@"
else
  python scripts/seed_sample_data.py "$@"
fi
