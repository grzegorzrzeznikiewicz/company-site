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
sed 's/"slug": "accent",/"invalidSlug": "accent",/' "$fixture_dir/invalid.json" >"$fixture_dir/mutated.json"
chmod 0755 "$fixture_dir"
chmod 0644 "$fixture_dir/invalid.json" "$fixture_dir/mutated.json"
file_mode() {
  if stat -f '%Lp' "$1" >/dev/null 2>&1; then
    stat -f '%Lp' "$1"
  else
    stat -c '%a' "$1"
  fi
}
if [[ "$(file_mode "$fixture_dir")" != 755 || "$(file_mode "$fixture_dir/mutated.json")" != 644 ]]; then
  echo 'Negative schema fixture is not safely traversable/readable by the container user.' >&2
  exit 1
fi
set +e
mutation_output="$(docker run --rm --network none \
  --volume "$fixture_dir:/fixture:ro" \
  --volume "$SCHEMA_DIR:/schema:ro" \
  gama-theme-qa:gsweb12 php /qa/validate-theme-json.php /fixture/mutated.json /schema/wp-7.1-theme.json 2>&1)"
mutation_status=$?
set -e
if [[ "$mutation_status" -eq 0 ]]; then
  echo 'Schema validator accepted the deliberate invalid palette-preset mutation.' >&2
  exit 1
fi
if ! grep -Fq 'theme.json failed WordPress 7.1 schema validation:' <<<"$mutation_output"; then
  printf 'Negative fixture failed for a reason other than schema rejection:\n%s\n' "$mutation_output" >&2
  exit 1
fi
if grep -Eqi 'permission denied|could not read' <<<"$mutation_output"; then
  printf 'Negative fixture hit a permission/read failure:\n%s\n' "$mutation_output" >&2
  exit 1
fi

echo 'Offline WordPress 7.1 theme.json schema contract passed.'
