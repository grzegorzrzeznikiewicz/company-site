#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCKER_CONFIG="${DOCKER_CONFIG:-/private/tmp/codex-wp-docker-config}" docker build \
  --tag gama-theme-qa:gsweb12 --file "$ROOT_DIR/qa/Dockerfile" "$ROOT_DIR/.." >/dev/null

standards="$(docker run --rm --network none gama-theme-qa:gsweb12 /qa/vendor/bin/phpcs -i)"
for standard in WordPress WordPress-Core WordPress-Docs WordPress-Extra; do
  grep -Eq "(^|[ ,])$standard([, ]|$)" <<<"$standards"
done

docker run --rm --network none \
  --volume "$ROOT_DIR/theme/gama-software:/theme:ro" \
  --volume "$ROOT_DIR/qa/phpcs.xml.dist:/qa/phpcs.xml.dist:ro" \
  gama-theme-qa:gsweb12 /qa/vendor/bin/phpcs --standard=/qa/phpcs.xml.dist -p -s /theme/functions.php /theme/patterns

docker run --rm --network none \
  --volume "$ROOT_DIR/plugins/gama-mail-transport:/plugin:ro" \
  gama-theme-qa:gsweb12 /qa/vendor/bin/phpcs --standard=WordPress -p -s /plugin

echo 'Pinned WPCS/PHPCS theme and production-mail contract passed.'
