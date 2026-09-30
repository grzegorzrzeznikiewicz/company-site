#!/usr/bin/env bash
set -euo pipefail

# This test catches package lifecycle input validation that follows symlinks or
# accepts a same-named artifact from outside the canonical dist directory.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fixture_dir="$(mktemp -d "${TMPDIR:-/tmp}/gama-test-package-input.XXXXXX")"
fixture_root="$fixture_dir/wordpress"
TEST_PACKAGE="$fixture_root/bin/test-package"
ARTIFACT="$fixture_root/dist/gama-contact-0.1.0.zip"
docker_marker="$fixture_dir/docker-reached"
failures=0

cleanup() {
  find "$fixture_dir" -type l -delete
  find "$fixture_dir" -type f -delete
  find "$fixture_dir" -depth -type d -exec rmdir {} \;
}
trap cleanup EXIT

mkdir -p "$fixture_root/bin" "$fixture_root/dist"
ln -s "$ROOT_DIR/bin/test-package" "$TEST_PACKAGE"

docker() {
  printf '%s\n' 'reached' >"$FAKE_DOCKER_MARKER"
  return 97
}
export -f docker
export FAKE_DOCKER_MARKER="$docker_marker"

expect_rejected() {
  local name="$1"
  local candidate="$2"
  local output command_status

  unlink "$docker_marker" 2>/dev/null || true
  set +e
  output="$(PATH="$PATH" "$TEST_PACKAGE" "$candidate" 2>&1)"
  command_status=$?
  set -e
  if [[ "$command_status" -ne 64 || -e "$docker_marker" ]]; then
    printf 'Input contract failed for %s (status %s):\n%s\n' "$name" "$command_status" "$output" >&2
    failures=$((failures + 1))
  fi
}

outside="$fixture_dir/gama-contact-0.1.0.zip"
printf '%s\n' 'outside-dist' >"$outside"
expect_rejected outside-dist "$outside"

symlink_target="$fixture_dir/symlink-target.zip"
printf '%s\n' 'symlink-target' >"$symlink_target"
ln -s "$symlink_target" "$ARTIFACT"
expect_rejected symlink "$ARTIFACT"
unlink "$ARTIFACT"

mkdir "$ARTIFACT"
expect_rejected non-regular "$ARTIFACT"
rmdir "$ARTIFACT"

printf '%s\n' 'canonical-regular-artifact' >"$ARTIFACT"
unlink "$docker_marker" 2>/dev/null || true
set +e
valid_output="$(PATH="$PATH" "$TEST_PACKAGE" "$ARTIFACT" 2>&1)"
valid_status=$?
set -e
if [[ "$valid_status" -ne 97 || ! -e "$docker_marker" ]]; then
  printf 'Canonical regular artifact did not reach Docker validation boundary (status %s):\n%s\n' "$valid_status" "$valid_output" >&2
  failures=$((failures + 1))
fi

if [[ "$failures" -ne 0 ]]; then
  exit 1
fi

echo 'test-package input contract passed.'
