#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
THEME_DIR="$ROOT_DIR/theme/gama-software"
fixture_dir="$(mktemp -d "${TMPDIR:-/tmp}/gama-theme-i18n.XXXXXX")"
trap 'find "$fixture_dir" -type f -delete; find "$fixture_dir" -depth -type d -exec rmdir {} \;' EXIT
mkdir -p "$fixture_dir/first" "$fixture_dir/second"
chmod 0777 "$fixture_dir/first" "$fixture_dir/second"

generate_pot() {
  local output_dir="$1"
  docker run --rm --network none \
    --volume "$THEME_DIR:/theme:ro" \
    --volume "$ROOT_DIR/qa/schema:/schema:ro" \
    --volume "$output_dir:/output" \
    gama-theme-qa:gsweb12 php /qa/extract-theme-json-i18n.php \
      /theme/theme.json /schema/wp-7.1-theme-i18n.json /output/theme-json.pot
  docker run --rm --network none \
    --env TZ=UTC --env LC_ALL=C \
    --volume "$THEME_DIR:/theme:ro" \
    --volume "$output_dir:/output" \
    wordpress:cli-2.12.0-php8.4@sha256:1e1d1485277d15e0331b598b6e19972243128ead978b7134d758097d82116b99 \
    wp i18n make-pot /theme /output/gama-software.pot \
      --domain=gama-software \
      --exclude=languages \
      --merge=/output/theme-json.pot \
      --headers='{"POT-Creation-Date":"","Report-Msgid-Bugs-To":"https://gamasoftware.com/"}' \
      --file-comment='Copyright (C) 2026 Gama Software'
}

(cd "$ROOT_DIR/qa/schema" && shasum -a 256 -c wp-7.1-theme-i18n.json.sha256)
DOCKER_CONFIG="${DOCKER_CONFIG:-/private/tmp/codex-wp-docker-config}" docker build \
  --tag gama-theme-qa:gsweb12 --file "$ROOT_DIR/qa/Dockerfile" "$ROOT_DIR/.." >/dev/null
generate_pot "$fixture_dir/first"
generate_pot "$fixture_dir/second"
cmp "$fixture_dir/first/gama-software.pot" "$fixture_dir/second/gama-software.pot"
cmp "$fixture_dir/first/gama-software.pot" "$THEME_DIR/languages/gama-software.pot"
grep -B1 -F 'msgid "Header"' "$THEME_DIR/languages/gama-software.pot" | grep -Fq 'msgctxt "Template part name"'
grep -B1 -F 'msgid "Footer"' "$THEME_DIR/languages/gama-software.pot" | grep -Fq 'msgctxt "Template part name"'
grep -Fq 'msgid "Page not found"' "$THEME_DIR/languages/gama-software.pot"
grep -Fq '"POT-Creation-Date: \n"' "$THEME_DIR/languages/gama-software.pot"

echo 'Deterministic WP-CLI POT contract passed.'
