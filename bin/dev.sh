#!/bin/bash

# Full stack (backend + frontend) management script
# Usage: ./scripts/dev.sh [command]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

case "$1" in
  up)
    "$SCRIPT_DIR/backend.sh" up
    "$SCRIPT_DIR/frontend.sh" up
    ;;
  down)
    "$SCRIPT_DIR/frontend.sh" down
    "$SCRIPT_DIR/backend.sh" down
    ;;
  restart)
    "$SCRIPT_DIR/frontend.sh" restart
    "$SCRIPT_DIR/backend.sh" restart
    ;;
  ps|status)
    echo "=== Backend ==="
    "$SCRIPT_DIR/backend.sh" ps
    echo ""
    echo "=== Frontend ==="
    "$SCRIPT_DIR/frontend.sh" ps
    ;;
  logs)
    echo "Use dedicated log scripts:"
    echo "  ./scripts/logs-backend.sh"
    echo "  ./scripts/logs-frontend.sh"
    ;;
  *)
    echo "Full Stack Management Script"
    echo ""
    echo "Usage: ./scripts/dev.sh [command]"
    echo ""
    echo "Commands:"
    echo "  up      - Start backend and frontend"
    echo "  down    - Stop backend and frontend"
    echo "  restart - Restart backend and frontend"
    echo "  ps      - Show status of all services"
    echo "  logs    - Show log commands"
    echo ""
    exit 1
    ;;
esac
