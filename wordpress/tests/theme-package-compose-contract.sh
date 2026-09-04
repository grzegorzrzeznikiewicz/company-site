#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
theme_version="$(sed -nE 's/^[[:space:]]*Version:[[:space:]]*([^[:space:]]+)[[:space:]]*$/\1/p' "$ROOT_DIR/theme/gama-software/style.css")"
[[ "$theme_version" == '0.4.0' ]]
PACKAGE_ZIP="$ROOT_DIR/dist/gama-software-$theme_version.zip"
resolved="$(PACKAGE_ZIP="$PACKAGE_ZIP" docker compose --project-name gama-theme-contract --file "$ROOT_DIR/tests/theme-package-compose.yaml" config --format json)"
resolved_images="$(PACKAGE_ZIP="$PACKAGE_ZIP" docker compose --project-name gama-theme-contract --file "$ROOT_DIR/tests/theme-package-compose.yaml" config --images)"
grep -Fxq 'gama-theme-contract-browser' <<<"$resolved_images"
if grep -Fq 'gama-theme-browser:gsweb12' <<<"$resolved_images"; then
  echo 'Theme browser image must be scoped to the disposable Compose project.' >&2
  exit 1
fi
printf '%s\n' "$resolved" | docker run --rm --interactive \
  --network none \
  --env "EXPECTED_PACKAGE_ZIP=$PACKAGE_ZIP" \
  --volume "$ROOT_DIR/tests:/contract:ro" \
  --entrypoint php wordpress:cli-2.12.0-php8.4@sha256:1e1d1485277d15e0331b598b6e19972243128ead978b7134d758097d82116b99 \
  /contract/assert-theme-package-compose.php
