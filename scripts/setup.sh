#!/usr/bin/env bash
set -e

echo "=== The Lenny Growth Assistant: Setup ==="

if [ ! -f .env ]; then
  echo "Copying .env.example to .env..."
  cp .env.example .env
fi

echo "Starting Docker Compose services..."
docker compose up -d postgres ollama agent-sidecar

echo "Waiting for PostgreSQL to be ready..."
until docker compose exec postgres pg_isready -U lenny -d lenny_growth; do
  sleep 2
done

echo "Pulling Ollama embedding model..."
docker compose exec ollama ollama pull nomic-embed-text || true

echo "Setup completed successfully."
