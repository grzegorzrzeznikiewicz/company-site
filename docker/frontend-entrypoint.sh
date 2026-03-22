#!/usr/bin/env bash
set -euo pipefail

cd /app

LOCKFILE_STAMP="node_modules/.package-lock.json"
RUNTIME_STAMP="node_modules/.runtime-stamp"
CURRENT_RUNTIME="$(node -v)-$(uname -s)-$(uname -m)"

if [ ! -d node_modules/.bin ] || [ ! -f "$LOCKFILE_STAMP" ] || ! cmp -s package-lock.json "$LOCKFILE_STAMP" || [ ! -f "$RUNTIME_STAMP" ] || [ "$(cat "$RUNTIME_STAMP")" != "$CURRENT_RUNTIME" ]; then
  npm ci --include=dev
  cp package-lock.json "$LOCKFILE_STAMP"
  printf '%s' "$CURRENT_RUNTIME" > "$RUNTIME_STAMP"
fi

exec "$@"
