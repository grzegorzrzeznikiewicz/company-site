#!/bin/bash

# Backend log viewer
# Usage: ./scripts/logs-backend.sh [service]
# Services: symfony, symfony-db, mailhog (default: all)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.symfony.yml"

SERVICE="${1:-}"

if [ -n "$SERVICE" ]; then
  docker compose -f "$COMPOSE_FILE" logs -f "$SERVICE"
else
  docker compose -f "$COMPOSE_FILE" logs -f
fi
