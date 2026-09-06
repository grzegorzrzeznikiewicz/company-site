#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOSITORY_ROOT="$(cd "$ROOT_DIR/.." && pwd)"
source "$ROOT_DIR/tests/lib/release-evidence.sh"
project="${GAMA_STAGING_PROJECT:-}"
artifact_root="${GAMA_RELEASE_ARTIFACT_ROOT:-${TMPDIR:-/tmp}/codex-gsweb27-artifacts}"
image="gama-wordpress-browser:gsweb27"
volume="gama-release-browser-artifacts-$$"
volume_acquired=0
volume_ownership_token=''

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
  local final_status
  trap - EXIT
  set +e
  gama_release_evidence_finalize "$status" "$volume_acquired" "$volume" "$archive" "$volume_ownership_token"
  final_status=$?
  set -e
  exit "$final_status"
}
trap cleanup EXIT

docker build \
  --cache-from 'gama-wordpress-browser:ci-cache' \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  --file "$ROOT_DIR/qa/browser.Dockerfile" --tag "$image" "$REPOSITORY_ROOT"
docker run --rm --network none --entrypoint node "$image" \
  ./specs/support/release-matrix-contract.cjs
if gama_release_evidence_acquire_volume "$volume" gama.contract=release-browser; then
  volume_acquired=1
  volume_ownership_token="$GAMA_RELEASE_EVIDENCE_ACQUIRED_TOKEN"
else
  status=$?
  exit "$status"
fi
GAMA_STAGING_PROJECT="$project" \
  GAMA_RELEASE_BROWSER_IMAGE="$image" \
  GAMA_RELEASE_BROWSER_ARTIFACT_VOLUME="$volume" \
  "$ROOT_DIR/tests/release-https-runtime.sh"
docker run --rm --network none --volume "$volume:/artifacts:ro" --entrypoint sh "$image" -ec \
  'test -f /artifacts/release-regression/report/index.html; test -f /artifacts/release-regression/test-results/.last-run.json; test -f /artifacts/tls-probes/reject-untrusted.json; test -f /artifacts/tls-probes/reject-wrong-hostname.json; test -f /artifacts/tls-probes/accept-valid.json; test -f /artifacts/tls-probes/metadata.json'

echo 'Release browser regression over trusted HTTPS, WCAG 2.1 AA and performance budgets passed.'
