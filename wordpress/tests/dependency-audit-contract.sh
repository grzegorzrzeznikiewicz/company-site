#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -x "$ROOT_DIR/tests/wordpress-dependency-audit.sh" ]]; then
  echo 'WordPress dependency audit gate must be executable.' >&2
  exit 1
fi

if NPM_CONFIG_REGISTRY='http://127.0.0.1:9' \
  "$ROOT_DIR/tests/wordpress-dependency-audit.sh" --npm assets >/dev/null 2>&1; then
  echo 'Dependency audit passed while the advisory service was unavailable.' >&2
  exit 1
fi

echo 'Dependency audit fails closed when the advisory service is unavailable.'
