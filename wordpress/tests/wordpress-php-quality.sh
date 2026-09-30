#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOSITORY_ROOT="$(cd "$ROOT_DIR/.." && pwd)"
IMAGE='gama-theme-qa:gsweb12'
cache_from=()
if docker image inspect "$IMAGE" >/dev/null 2>&1; then
  cache_from=(--cache-from "$IMAGE")
fi

docker build \
  "${cache_from[@]}" \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  --tag "$IMAGE" \
  --file "$ROOT_DIR/qa/Dockerfile" \
  "$REPOSITORY_ROOT" >/dev/null

run_phpstan_fixture() {
  local source_path="$1"
  local source_directory source_name

  if [[ ! -f "$source_path" || -L "$source_path" ]]; then
    echo "Static-analysis input must be a regular, non-symlink file: $source_path" >&2
    exit 64
  fi
  source_directory="$(cd "$(dirname "$source_path")" && pwd -P)"
  source_name="$(basename "$source_path")"
  docker run --rm --network none \
    --volume "$source_directory:/fixture:ro" \
    "$IMAGE" /qa/vendor/bin/phpstan analyze \
    --configuration=/qa/phpstan.neon.dist --memory-limit=1G \
    --no-progress "/fixture/$source_name"
}

if [[ "${1:-}" == '--phpstan' ]]; then
  [[ "$#" -eq 2 ]] || { echo "Usage: $0 --phpstan <file>" >&2; exit 64; }
  run_phpstan_fixture "$2"
  exit
fi
if [[ "$#" -ne 0 ]]; then
  echo "Usage: $0 [--phpstan <file>]" >&2
  exit 64
fi

standards="$(docker run --rm --network none "$IMAGE" /qa/vendor/bin/phpcs -i)"
for standard in WordPress WordPress-Core WordPress-Docs WordPress-Extra; do
  grep -Eq "(^|[ ,])$standard([, ]|$)" <<<"$standards"
done

docker run --rm --network none \
  --volume "$ROOT_DIR/theme/gama-software:/theme:ro" \
  --volume "$ROOT_DIR/qa/phpcs.xml.dist:/qa/phpcs.xml.dist:ro" \
  "$IMAGE" /qa/vendor/bin/phpcs --standard=/qa/phpcs.xml.dist \
  --extensions=php -p -s /theme/functions.php /theme/patterns

docker run --rm --network none \
  --volume "$ROOT_DIR/plugins:/plugins:ro" \
  --volume "$ROOT_DIR/qa/phpcs-plugins.xml.dist:/qa/phpcs-plugins.xml.dist:ro" \
  "$IMAGE" /qa/vendor/bin/phpcs --standard=/qa/phpcs-plugins.xml.dist \
  -n -p -s /plugins

docker run --rm --network none \
  --volume "$ROOT_DIR/plugins/gama-mail-transport:/plugin:ro" \
  "$IMAGE" /qa/vendor/bin/phpcs --standard=WordPress -p -s /plugin

docker run --rm --network none \
  --volume "$ROOT_DIR:/workspace:ro" \
  "$IMAGE" /qa/vendor/bin/phpstan analyze \
  --configuration=/qa/phpstan.neon.dist --memory-limit=1G --no-progress

echo 'Pinned WPCS/PHPCS and PHPStan WordPress production-PHP gate passed.'
