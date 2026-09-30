#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
docker run --rm --network none \
  --volume "$ROOT_DIR/plugins/gama-security:/plugin:ro" \
  --volume "$ROOT_DIR/tests:/contract:ro" \
  --entrypoint php \
  wordpress:cli-2.12.0-php8.4@sha256:1e1d1485277d15e0331b598b6e19972243128ead978b7134d758097d82116b99 \
  /contract/assert-security-plugin.php /plugin
