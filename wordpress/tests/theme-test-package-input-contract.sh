#!/usr/bin/env bash
set -euo pipefail

# This test catches non-SemVer theme artifact names, filename/header mismatch,
# duplicate Version headers, symlink traversal and artifacts outside dist.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fixture_dir="$(mktemp -d "${TMPDIR:-/tmp}/gama-theme-test-package-input.XXXXXX")"
fixture_root="$fixture_dir/wordpress"
test_package="$fixture_root/bin/test-package"
docker_marker="$fixture_dir/docker-reached"
failures=0

cleanup() {
  find "$fixture_dir" -type l -delete
  find "$fixture_dir" -type f -delete
  find "$fixture_dir" -depth -type d -exec rmdir {} \;
}
trap cleanup EXIT

mkdir -p "$fixture_root/bin" "$fixture_root/dist" "$fixture_dir/build/gama-software"
ln -s "$ROOT_DIR/bin/test-package" "$test_package"

docker() {
  printf '%s\n' 'reached' >"$FAKE_DOCKER_MARKER"
  return 97
}
export -f docker
export FAKE_DOCKER_MARKER="$docker_marker"

make_theme_zip() {
  local destination="$1"
  local header="$2"
  local source_dir="$fixture_dir/build/gama-software"

  find "$source_dir" -type f -delete
  printf '%b\n' "$header" >"$source_dir/style.css"
  (cd "$fixture_dir/build" && zip -X -q "$destination" gama-software/style.css)
}

expect_rejected() {
  local name="$1"
  local candidate="$2"
  local output command_status

  unlink "$docker_marker" 2>/dev/null || true
  set +e
  output="$(PATH="$PATH" "$test_package" "$candidate" 2>&1)"
  command_status=$?
  set -e
  if [[ "$command_status" -ne 64 || -e "$docker_marker" ]]; then
    printf 'Theme input contract failed for %s (status %s):\n%s\n' "$name" "$command_status" "$output" >&2
    failures=$((failures + 1))
  fi
}

for invalid_name in \
  gama-software-01.2.3.zip \
  gama-software-1.02.3.zip \
  gama-software-1.2.zip \
  gama-software-1.2.3-beta.zip \
  other-theme-1.2.3.zip; do
  printf '%s\n' 'invalid-name' >"$fixture_root/dist/$invalid_name"
  expect_rejected "$invalid_name" "$fixture_root/dist/$invalid_name"
done

outside="$fixture_dir/gama-software-1.2.3.zip"
make_theme_zip "$outside" 'Version: 1.2.3'
expect_rejected outside-dist "$outside"

symlink_target="$fixture_dir/gama-software-2.3.4.zip"
make_theme_zip "$symlink_target" 'Version: 2.3.4'
ln -s "$symlink_target" "$fixture_root/dist/gama-software-2.3.4.zip"
expect_rejected symlink "$fixture_root/dist/gama-software-2.3.4.zip"

mismatch="$fixture_root/dist/gama-software-3.4.5.zip"
make_theme_zip "$mismatch" 'Version: 3.4.6'
expect_rejected filename-header-mismatch "$mismatch"

duplicate="$fixture_root/dist/gama-software-4.5.6.zip"
make_theme_zip "$duplicate" 'Version: 4.5.6\nVersion: 4.5.6'
expect_rejected duplicate-version-header "$duplicate"

missing_style="$fixture_root/dist/gama-software-5.6.7.zip"
printf '%s\n' 'missing-style' >"$fixture_dir/build/README.md"
(cd "$fixture_dir/build" && zip -X -q "$missing_style" README.md)
expect_rejected missing-style "$missing_style"

valid="$fixture_root/dist/gama-software-12.34.56.zip"
make_theme_zip "$valid" 'Version: 12.34.56'
unlink "$docker_marker" 2>/dev/null || true
set +e
valid_output="$(PATH="$PATH" "$test_package" "$valid" 2>&1)"
valid_status=$?
set -e
if [[ "$valid_status" -ne 97 || ! -e "$docker_marker" ]]; then
  printf 'Strict SemVer artifact did not reach Docker validation (status %s):\n%s\n' "$valid_status" "$valid_output" >&2
  failures=$((failures + 1))
fi

if [[ "$failures" -ne 0 ]]; then
  exit 1
fi

echo 'Theme test-package strict SemVer input contract passed.'
