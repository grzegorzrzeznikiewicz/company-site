#!/bin/bash

# Frontend log viewer
# Starts Vite in foreground so logs are visible directly.
# Usage: ./scripts/logs-frontend.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT" && npx vite 2>&1
