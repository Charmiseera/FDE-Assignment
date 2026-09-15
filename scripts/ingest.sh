#!/usr/bin/env bash
# Run the ingestion pipeline from the project root.
# Usage:
#   bash scripts/ingest.sh            # skip unchanged chunks
#   bash scripts/ingest.sh --refresh  # force re-embed everything
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../backend"
TRANSCRIPT_DIR="$SCRIPT_DIR/../data/transcripts"

echo "[ingest] Starting ingestion from $TRANSCRIPT_DIR"
cd "$BACKEND_DIR"

# Ensure DB is running and backend env vars are available
export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://lenny:lenny@localhost:5432/lenny_growth}"
export ALEMBIC_DATABASE_URL="${ALEMBIC_DATABASE_URL:-postgresql://lenny:lenny@localhost:5432/lenny_growth}"
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"

python -m app.ingestion.ingest --dir "$TRANSCRIPT_DIR" "$@"
