#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOSITORY_ROOT="$(cd "$ROOT_DIR/.." && pwd)"
PHP_IMAGE='gama-theme-qa:gsweb12'
NODE_IMAGE='node:24.14.0-alpine@sha256:7fddd9ddeae8196abf4a3ef2de34e11f7b1a722119f91f28ddf1e99dcafdf114'
php_cache_from=()
if docker image inspect "$PHP_IMAGE" >/dev/null 2>&1; then
  php_cache_from=(--cache-from "$PHP_IMAGE")
fi

audit_npm_lock() {
  local package_directory="$1"
  docker run --rm \
    --env "NPM_CONFIG_REGISTRY=${NPM_CONFIG_REGISTRY:-https://registry.npmjs.org}" \
    --env NPM_CONFIG_UPDATE_NOTIFIER=false \
    --volume "$package_directory:/package:ro" \
    --workdir /package \
    "$NODE_IMAGE" npm audit --package-lock-only --audit-level=low --ignore-scripts
}

if [[ "${1:-}" == '--npm' ]]; then
  [[ "$#" -eq 2 ]] || { echo "Usage: $0 --npm <assets|e2e>" >&2; exit 64; }
  case "$2" in
    assets) audit_npm_lock "$ROOT_DIR/qa/assets" ;;
    e2e) audit_npm_lock "$ROOT_DIR/qa/e2e" ;;
    *) echo "Usage: $0 --npm <assets|e2e>" >&2; exit 64 ;;
  esac
  exit
fi
if [[ "$#" -ne 0 ]]; then
  echo "Usage: $0 [--npm <assets|e2e>]" >&2
  exit 64
fi

docker build \
  "${php_cache_from[@]}" \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  --tag "$PHP_IMAGE" \
  --file "$ROOT_DIR/qa/Dockerfile" \
  "$REPOSITORY_ROOT" >/dev/null
docker run --rm --env COMPOSER_CACHE_DIR=/tmp/composer-cache "$PHP_IMAGE" composer audit \
  --locked --abandoned=fail --no-interaction --no-ansi
audit_npm_lock "$ROOT_DIR/qa/assets"
audit_npm_lock "$ROOT_DIR/qa/e2e"

echo 'Strict Composer and npm dependency vulnerability audits passed.'
