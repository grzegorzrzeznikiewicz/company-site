#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOSITORY_ROOT="$(cd "$ROOT_DIR/.." && pwd)"
IMAGE='gama-wordpress-assets-qa:gsweb25'
cache_from=()
if docker image inspect "$IMAGE" >/dev/null 2>&1; then
  cache_from=(--cache-from "$IMAGE")
fi

docker build \
  "${cache_from[@]}" \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  --tag "$IMAGE" \
  --file "$ROOT_DIR/qa/assets.Dockerfile" \
  "$REPOSITORY_ROOT" >/dev/null

run_linter() {
  local linter="$1"
  local config="$2"
  local source_path="$3"
  local source_directory source_name

  if [[ ! -f "$source_path" || -L "$source_path" ]]; then
    echo "Quality input must be a regular, non-symlink file: $source_path" >&2
    exit 64
  fi
  source_directory="$(cd "$(dirname "$source_path")" && pwd -P)"
  source_name="$(basename "$source_path")"
  docker run --rm --network none \
    --volume "$source_directory:/qa/source:ro" \
    "$IMAGE" "/qa/node_modules/.bin/$linter" \
    --config "/qa/$config" --max-warnings=0 "/qa/source/$source_name"
}

case "${1:-}" in
  --javascript)
    [[ "$#" -eq 2 ]] || { echo "Usage: $0 --javascript <file>" >&2; exit 64; }
    run_linter eslint eslint.config.mjs "$2"
    ;;
  --css)
    [[ "$#" -eq 2 ]] || { echo "Usage: $0 --css <file>" >&2; exit 64; }
    run_linter stylelint stylelint.config.mjs "$2"
    ;;
  '')
    [[ "$#" -eq 0 ]]
    run_linter eslint eslint.config.mjs \
      "$ROOT_DIR/plugins/gama-contact/assets/contact-form.js"
    run_linter stylelint stylelint.config.mjs \
      "$ROOT_DIR/theme/gama-software/style.css"
    run_linter stylelint stylelint.config.mjs \
      "$ROOT_DIR/plugins/gama-contact/assets/contact-form.css"
    ;;
  *)
    echo "Usage: $0 [--javascript <file>|--css <file>]" >&2
    exit 64
    ;;
esac

echo 'Pinned JavaScript and CSS quality gate passed.'
