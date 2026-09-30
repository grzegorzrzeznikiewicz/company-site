#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/tests/lib/release-evidence.sh"

artifact_root="$(mktemp -d "${TMPDIR:-/tmp}/gama-release-evidence-docker.XXXXXX")"
volume="gama-release-evidence-docker-$$"
fixture_container="$volume-fixture"
export_container="$volume-export"
archive="$artifact_root/evidence.tar"
blocked_archive="$artifact_root/blocked.tar"
promotion_stderr="$artifact_root/promotion.stderr"
volume_acquired=0

cleanup() {
  local status=$?
  trap - EXIT
  set +e
  docker container rm --force "$fixture_container" "$export_container" >/dev/null 2>&1
  if [[ "$volume_acquired" -eq 1 ]] && docker volume inspect "$volume" >/dev/null 2>&1; then
    docker volume rm "$volume" >/dev/null 2>&1
  fi
  [[ -f "$archive" ]] && unlink "$archive"
  [[ -f "$promotion_stderr" ]] && unlink "$promotion_stderr"
  [[ -f "$blocked_archive/content" ]] && unlink "$blocked_archive/content"
  [[ -d "$blocked_archive" ]] && rmdir "$blocked_archive"
  rmdir "$artifact_root" 2>/dev/null
  exit "$status"
}
trap cleanup EXIT

if gama_release_evidence_acquire_volume "$volume" gama.contract=release-evidence-docker; then
  volume_acquired=1
else
  exit $?
fi

docker run --rm --name "$fixture_container" --network none \
  --volume "$volume:/artifacts" --entrypoint sh "$GAMA_RELEASE_EVIDENCE_IMAGE" -ec \
  "printf '%s\\n' 'known non-secret release evidence' > /artifacts/evidence.txt"

set +e
gama_release_evidence_finalize 0 "$volume_acquired" "$volume" "$archive" "$GAMA_RELEASE_EVIDENCE_ACQUIRED_TOKEN"
finalize_status=$?
set -e

if [[ "$finalize_status" -ne 0 ]]; then
  echo "Pinned-image evidence export returned status $finalize_status." >&2
  exit 1
fi
tar -tf "$archive" | grep -Fxq './evidence.txt'
[[ "$(tar -xOf "$archive" ./evidence.txt)" == 'known non-secret release evidence' ]]
if docker container inspect "$fixture_container" >/dev/null 2>&1 \
  || docker container inspect "$export_container" >/dev/null 2>&1; then
  echo 'A disposable evidence container remains after export.' >&2
  exit 1
fi
if docker volume inspect "$volume" >/dev/null 2>&1; then
  echo "Owned evidence volume remains after successful export: $volume" >&2
  exit 1
fi
volume_acquired=0

if gama_release_evidence_acquire_volume "$volume" gama.contract=release-evidence-docker; then
  volume_acquired=1
else
  exit $?
fi
docker run --rm --name "$fixture_container" --network none \
  --volume "$volume:/artifacts" --entrypoint sh "$GAMA_RELEASE_EVIDENCE_IMAGE" -ec \
  "printf '%s\\n' 'known non-secret release evidence' > /artifacts/evidence.txt"
mkdir "$blocked_archive"
printf '%s' 'keep-directory-content' >"$blocked_archive/content"
set +e
gama_release_evidence_finalize 0 "$volume_acquired" "$volume" "$blocked_archive" "$GAMA_RELEASE_EVIDENCE_ACQUIRED_TOKEN" 2>"$promotion_stderr"
promotion_status=$?
set -e
if [[ "$promotion_status" -eq 0 ]]; then
  echo 'A real destination-directory promotion failure returned success.' >&2
  exit 1
fi
grep -Fq 'Evidence archive promotion failed with status' "$promotion_stderr"
[[ "$(<"$blocked_archive/content")" == keep-directory-content ]]
[[ "$(find "$blocked_archive" -mindepth 1 -maxdepth 1 -type f | wc -l | tr -d ' ')" -eq 1 ]]
if docker container inspect "$export_container" >/dev/null 2>&1; then
  echo 'The failed export promotion left its disposable container behind.' >&2
  exit 1
fi
if docker volume inspect "$volume" >/dev/null 2>&1; then
  echo "The failed export promotion left its owned volume behind: $volume" >&2
  exit 1
fi
volume_acquired=0

echo 'Pinned-image release evidence export and cleanup contract passed.'
