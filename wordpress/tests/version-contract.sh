#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -f "$ROOT_DIR/.env" ]]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
fi

docker compose --project-name gama-wordpress --env-file "$ROOT_DIR/.env" --file "$ROOT_DIR/compose.yaml" config |
  grep -Fx '    image: wordpress:7.1.0-php8.4-apache'
"$ROOT_DIR/bin/wp" core version | grep -Fx '7.1'
