#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOSITORY_ROOT="$(cd "$ROOT_DIR/.." && pwd)"
project="${GAMA_STAGING_PROJECT:-}"
artifact_root="${GAMA_RELEASE_ARTIFACT_ROOT:-${TMPDIR:-/tmp}/codex-gsweb28-artifacts}"
image="gama-wordpress-browser:gsweb28"
volume="gama-acceptance-browser-artifacts-$$"

if [[ ! "$project" =~ ^gama-wp-staging-[a-z0-9][a-z0-9-]{2,40}$ ]]; then
  echo 'GAMA_STAGING_PROJECT must name the active isolated staging namespace.' >&2
  exit 64
fi
network="${project}_default"
docker network inspect "$network" >/dev/null
mkdir -p "$artifact_root"
archive="$artifact_root/${project}-acceptance-artifacts.tar"
if [[ -e "$archive" || -L "$archive" ]]; then
  echo "Refusing to overwrite acceptance evidence: $archive" >&2
  exit 1
fi

cleanup() {
  local status=$?
  set +e
  if docker volume inspect "$volume" >/dev/null 2>&1; then
    docker run --rm --network none --volume "$volume:/artifacts:ro" --entrypoint tar \
      wordpress:7.1.0-php8.4-apache -C /artifacts -cf - . >"$archive.partial"
    if [[ "$?" -eq 0 ]]; then mv "$archive.partial" "$archive"; else unlink "$archive.partial" 2>/dev/null; fi
    docker volume rm "$volume" >/dev/null 2>&1
  fi
  set -e
  trap - EXIT
  exit "$status"
}
trap cleanup EXIT

docker build \
  --cache-from 'gama-wordpress-browser:ci-cache' \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  --file "$ROOT_DIR/qa/browser.Dockerfile" --tag "$image" "$REPOSITORY_ROOT"
docker volume create --label gama.contract=acceptance-browser "$volume" >/dev/null
docker run --rm \
  --network "$network" \
  --volume "$volume:/artifacts" \
  --env WP_BASE_URL=http://wordpress \
  --env WP_ADMIN_USER=admin \
  --env WP_ADMIN_PASSWORD=staging-admin-test-only \
  --env WP_EDITOR_USER=style-editor \
  --env WP_EDITOR_PASSWORD=style-editor-test-only \
  --env MAILPIT_API_URL=http://mailpit:8025 \
  --env GAMA_PLAYWRIGHT_RUN=release-acceptance \
  "$image" npm test -- --grep '@release-acceptance|@global-styles-editor-choices|@hero|@services|@modules|@blog|@contact-form|@content'
docker run --rm --network none --volume "$volume:/artifacts:ro" --entrypoint sh "$image" -ec \
  'test -f /artifacts/release-acceptance/report/index.html; test -f /artifacts/release-acceptance/test-results/.last-run.json'

echo 'Immutable staging Editor, Administrator, content and contact acceptance passed.'
