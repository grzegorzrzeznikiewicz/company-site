#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGE_ZIP="$ROOT_DIR/dist/gama-software-0.1.0.zip"
resolved="$(PACKAGE_ZIP="$PACKAGE_ZIP" docker compose --project-name gama-theme-contract --file "$ROOT_DIR/tests/theme-package-compose.yaml" config --format json)"
printf '%s\n' "$resolved" | docker run --rm --interactive \
  --env "EXPECTED_PACKAGE_ZIP=$PACKAGE_ZIP" \
  --volume "$ROOT_DIR/tests:/contract:ro" \
  --entrypoint php wordpress:cli-2.12.0-php8.4 \
  /contract/assert-theme-package-compose.php
