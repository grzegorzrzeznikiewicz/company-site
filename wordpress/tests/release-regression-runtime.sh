#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOSITORY_ROOT="$(cd "$ROOT_DIR/.." && pwd)"
project="${GAMA_STAGING_PROJECT:-}"
artifact_root="${GAMA_RELEASE_ARTIFACT_ROOT:-${TMPDIR:-/tmp}/codex-gsweb27-artifacts}"
image="gama-wordpress-browser:gsweb27"
volume="gama-release-browser-artifacts-$$"

if [[ ! "$project" =~ ^gama-wp-staging-[a-z0-9][a-z0-9-]{2,40}$ ]]; then
  echo 'GAMA_STAGING_PROJECT must name the active isolated staging namespace.' >&2
  exit 64
fi
network="${project}_default"
docker network inspect "$network" >/dev/null
mkdir -p "$artifact_root"
archive="$artifact_root/${project}-browser-artifacts.tar"
if [[ -e "$archive" || -L "$archive" ]]; then
  echo "Refusing to overwrite browser evidence: $archive" >&2
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

DOCKER_CONFIG="${DOCKER_CONFIG:-/private/tmp/codex-wp-docker-config}" docker build \
  --file "$ROOT_DIR/qa/browser.Dockerfile" --tag "$image" "$REPOSITORY_ROOT"
docker volume create --label gama.contract=release-browser "$volume" >/dev/null
docker run --rm \
  --network "$network" \
  --volume "$volume:/artifacts" \
  --env WP_BASE_URL=http://wordpress \
  --env GAMA_PLAYWRIGHT_RUN=release-regression \
  "$image" npm test -- --grep @release-regression
docker run --rm --network none --volume "$volume:/artifacts:ro" --entrypoint sh "$image" -ec \
  'test -f /artifacts/release-regression/report/index.html; test -f /artifacts/release-regression/test-results/.last-run.json'

echo 'Release browser regression, WCAG 2.1 AA and performance budgets passed.'
