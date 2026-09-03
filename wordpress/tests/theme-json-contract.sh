#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCHEMA_DIR="$ROOT_DIR/qa/schema"
THEME_JSON="$ROOT_DIR/theme/gama-software/theme.json"
fixture_dir="$(mktemp -d "${TMPDIR:-/tmp}/gama-theme-schema.XXXXXX")"
trap 'find "$fixture_dir" -type f -delete; find "$fixture_dir" -depth -type d -exec rmdir {} \;' EXIT

(cd "$SCHEMA_DIR" && shasum -a 256 -c wp-7.1-theme.json.sha256)
grep -Fq '"$schema": "http://json-schema.org/draft-07/schema#"' "$SCHEMA_DIR/wp-7.1-theme.json"
grep -Fq '"$schema": "https://schemas.wp.org/wp/7.1/theme.json"' "$THEME_JSON"

DOCKER_CONFIG="${DOCKER_CONFIG:-/private/tmp/codex-wp-docker-config}" docker build \
  --tag gama-theme-qa:gsweb12 --file "$ROOT_DIR/qa/Dockerfile" "$ROOT_DIR/.."
docker run --rm --network none \
  --volume "$ROOT_DIR/theme/gama-software:/theme:ro" \
  --volume "$SCHEMA_DIR:/schema:ro" \
  gama-theme-qa:gsweb12 php /qa/validate-theme-json.php /theme/theme.json /schema/wp-7.1-theme.json

cp "$THEME_JSON" "$fixture_dir/invalid.json"
sed 's/"version": 3/"version": 999/' "$fixture_dir/invalid.json" >"$fixture_dir/mutated.json"
if docker run --rm --network none \
  --volume "$fixture_dir:/fixture:ro" \
  --volume "$SCHEMA_DIR:/schema:ro" \
  gama-theme-qa:gsweb12 php /qa/validate-theme-json.php /fixture/mutated.json /schema/wp-7.1-theme.json; then
  echo 'Schema validator accepted the deliberate invalid version mutation.' >&2
  exit 1
fi

echo 'Offline WordPress 7.1 theme.json schema contract passed.'
