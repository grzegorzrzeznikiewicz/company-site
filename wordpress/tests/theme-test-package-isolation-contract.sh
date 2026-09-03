#!/usr/bin/env bash
set -euo pipefail

# This test drives the real theme test-package branch through a controlled
# Docker boundary. It catches missing image isolation and artifact collection,
# including cleanup after a failing lifecycle.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_PACKAGE="$ROOT_DIR/bin/test-package"
ARTIFACT="$ROOT_DIR/dist/gama-software-0.1.0.zip"
fixture_dir="$(mktemp -d "${TMPDIR:-/tmp}/gama-theme-test-package-isolation.XXXXXX")"
fake_bin="$fixture_dir/bin"
log_path="$fixture_dir/docker.log"
mkdir -p "$fake_bin"

cleanup() {
  find "$fixture_dir" -type l -delete
  find "$fixture_dir" -type f -delete
  find "$fixture_dir" -depth -type d -exec rmdir {} \;
}
trap cleanup EXIT

if [[ ! -f "$ARTIFACT" || -L "$ARTIFACT" ]]; then
  echo "Canonical regular theme artifact is required: $ARTIFACT" >&2
  exit 1
fi

ln -s "$ROOT_DIR/tests/fixtures/fake-theme-package-docker.sh" "$fake_bin/docker"

run_case() {
  local mode="$1"
  local expected_status="$2"
  local state_dir="$fixture_dir/$mode"
  local output command_status

  mkdir -p "$state_dir" "$state_dir/artifacts"
  : >"$log_path"
  set +e
  output="$(
    FAKE_DOCKER_MODE="$mode" \
    FAKE_DOCKER_LOG="$log_path" \
    FAKE_DOCKER_STATE="$state_dir" \
    GAMA_THEME_ARTIFACT_ROOT="$state_dir/artifacts" \
    PATH="$fake_bin:$PATH" \
    "$TEST_PACKAGE" "$ARTIFACT" 2>&1
  )"
  command_status=$?
  set -e
  if [[ "$command_status" -ne "$expected_status" ]]; then
    printf 'Theme isolation case %s returned %s instead of %s:\n%s\n' "$mode" "$command_status" "$expected_status" "$output" >&2
    exit 1
  fi
  printf '%s\n' "$output" >"$state_dir/output.log"
  cp "$log_path" "$state_dir/docker.log"
}

run_case image-collision 1
if grep -Fq ' up --detach --wait ' "$fixture_dir/image-collision/docker.log"; then
  echo 'Exact-label image collision reached Compose startup.' >&2
  exit 1
fi

for mode in lifecycle-error collection-error; do
  run_case "$mode" 88
  project_name="$(grep -Eo 'gama-theme-package-[0-9]+-[0-9]+-[0-9]+' "$fixture_dir/$mode/output.log" | head -n 1)"
  [[ -n "$project_name" ]]
  for kind in container network image; do
    if [[ "$(<"$fixture_dir/$mode/$kind-queries")" -ne 2 ]]; then
      echo "Theme cleanup did not preflight and re-query $kind resources." >&2
      exit 1
    fi
  done
  if [[ "$(<"$fixture_dir/$mode/volume-queries")" -ne 3 ]]; then
    echo 'Theme cleanup did not query the artifact volume before collection and after teardown.' >&2
    exit 1
  fi
  collector_line="$(grep -nF ' -C /artifacts -cf - .' "$fixture_dir/$mode/docker.log" | cut -d: -f1)"
  down_line="$(grep -nF ' down --volumes --remove-orphans --rmi local' "$fixture_dir/$mode/docker.log" | cut -d: -f1)"
  if [[ -z "$collector_line" || -z "$down_line" || "$collector_line" -ge "$down_line" ]]; then
    echo 'Browser artifact volume was not streamed before Compose teardown.' >&2
    exit 1
  fi
done

success_archive="$(find "$fixture_dir/lifecycle-error/artifacts" -name browser-artifacts.tar -type f -print -quit)"
if [[ -z "$success_archive" || "$(<"$success_archive")" != 'complete-browser-artifact-volume' ]]; then
  echo 'Successful browser artifact collection did not preserve the whole tar stream.' >&2
  exit 1
fi
if ! grep -Fq 'Browser artifact collection failed with status 75' "$fixture_dir/collection-error/output.log"; then
  echo 'Collection failure was not visible while preserving the lifecycle status.' >&2
  exit 1
fi

echo 'Theme test-package isolation and artifact collection contract passed.'
