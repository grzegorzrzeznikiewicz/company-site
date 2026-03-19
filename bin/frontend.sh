#!/bin/bash

# Frontend (Vite dev server) management script
# Usage: ./scripts/frontend.sh [command]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PIDFILE="$PROJECT_ROOT/.vite.pid"

start_frontend() {
  if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "Frontend is already running (PID: $(cat "$PIDFILE"))"
    return 1
  fi
  echo "Starting frontend (Vite dev server)..."
  cd "$PROJECT_ROOT" && npm run dev &
  echo $! > "$PIDFILE"
  echo "Frontend started (PID: $!)"
}

stop_frontend() {
  if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if kill -0 "$PID" 2>/dev/null; then
      echo "Stopping frontend (PID: $PID)..."
      kill "$PID"
      rm -f "$PIDFILE"
      echo "Frontend stopped."
    else
      echo "Frontend process not found. Cleaning up PID file."
      rm -f "$PIDFILE"
    fi
  else
    echo "No PID file found. Frontend may not be running."
    echo "Checking for Vite processes..."
    pkill -f "vite" 2>/dev/null && echo "Vite processes stopped." || echo "No Vite processes found."
  fi
}

case "$1" in
  up|start)
    start_frontend
    ;;
  down|stop)
    stop_frontend
    ;;
  restart)
    stop_frontend
    sleep 1
    start_frontend
    ;;
  logs)
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
      echo "Attaching to Vite output. Use ./scripts/logs-frontend.sh for dedicated log monitoring."
      echo "Tip: Frontend logs are also visible in the terminal where Vite was started."
    else
      echo "Frontend is not running. Start it with: ./scripts/frontend.sh up"
    fi
    ;;
  ps|status)
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
      echo "Frontend is running (PID: $(cat "$PIDFILE"))"
    else
      echo "Frontend is not running."
    fi
    ;;
  *)
    echo "Frontend Management Script"
    echo ""
    echo "Usage: ./scripts/frontend.sh [command]"
    echo ""
    echo "Commands:"
    echo "  up|start  - Start Vite dev server"
    echo "  down|stop - Stop Vite dev server"
    echo "  restart   - Restart Vite dev server"
    echo "  logs      - Show log info"
    echo "  ps|status - Check if frontend is running"
    echo ""
    exit 1
    ;;
esac
