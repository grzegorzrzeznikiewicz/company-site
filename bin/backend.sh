#!/bin/bash

# Backend (Symfony API + DB + MailHog) management script
# Usage: ./scripts/backend.sh [command]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.symfony.yml"

case "$1" in
  up)
    echo "Starting backend..."
    docker compose -f "$COMPOSE_FILE" up -d
    ;;
  down)
    echo "Stopping backend..."
    docker compose -f "$COMPOSE_FILE" down
    ;;
  restart)
    echo "Restarting backend..."
    docker compose -f "$COMPOSE_FILE" restart
    ;;
  logs)
    docker compose -f "$COMPOSE_FILE" logs -f
    ;;
  ps)
    docker compose -f "$COMPOSE_FILE" ps
    ;;
  build)
    echo "Building backend images..."
    docker compose -f "$COMPOSE_FILE" build --no-cache
    ;;
  rebuild)
    echo "Rebuilding backend..."
    docker compose -f "$COMPOSE_FILE" down
    docker compose -f "$COMPOSE_FILE" build --no-cache
    docker compose -f "$COMPOSE_FILE" up -d
    ;;
  shell)
    docker compose -f "$COMPOSE_FILE" exec symfony bash
    ;;
  *)
    echo "Backend Management Script"
    echo ""
    echo "Usage: ./scripts/backend.sh [command]"
    echo ""
    echo "Commands:"
    echo "  up        - Start backend containers (API + DB + MailHog)"
    echo "  down      - Stop backend containers"
    echo "  restart   - Restart backend containers"
    echo "  logs      - Follow backend logs"
    echo "  ps        - Show container status"
    echo "  build     - Build images"
    echo "  rebuild   - Rebuild and restart everything"
    echo "  shell     - Open shell in Symfony container"
    echo ""
    exit 1
    ;;
esac
