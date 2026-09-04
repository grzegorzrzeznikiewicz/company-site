#!/usr/bin/env bash
set -euo pipefail

# This test catches non-portable, incomplete, or non-reproducible plugin ZIPs.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"
ZIP_PATH="$DIST_DIR/gama-contact-0.2.0.zip"
MANIFEST_PATH="$DIST_DIR/gama-contact-0.2.0.manifest.txt"
SHA_PATH="$DIST_DIR/gama-contact-0.2.0.zip.sha256"
fixture_dir="$(mktemp -d "${TMPDIR:-/tmp}/gama-package-contract.XXXXXX")"
plugin_source="$ROOT_DIR/plugins/gama-contact"
owned_source_paths=()

cleanup_owned_source_paths() {
  local cleanup_status=0
  local owned_path

  for owned_path in ${owned_source_paths[@]+"${owned_source_paths[@]}"}; do
    if [[ -L "$owned_path" || -f "$owned_path" ]]; then
      unlink "$owned_path" || cleanup_status=1
    elif [[ -e "$owned_path" ]]; then
      echo "Refusing to clean changed source fixture: $owned_path" >&2
      cleanup_status=1
    fi
  done
  return "$cleanup_status"
}

create_unique_regular_fixture() {
  local prefix="$1"

  created_path="$(mktemp "$plugin_source/.gama-package-contract-${prefix}.XXXXXX")"
  owned_source_paths+=("$created_path")
}

create_unique_symlink_fixture() {
  local attempt candidate

  for attempt in {1..50}; do
    candidate="$plugin_source/.gama-package-contract-link.$$.$RANDOM.$attempt.php"
    if ln -s gama-contact.php "$candidate" 2>/dev/null; then
      created_path="$candidate"
      owned_source_paths+=("$created_path")
      return 0
    fi
  done
  echo "Could not reserve an exclusive source symlink fixture." >&2
  return 1
}

cleanup() {
  local test_status=$?
  local cleanup_status=0

  set +e
  cleanup_owned_source_paths || cleanup_status=1
  find "$fixture_dir" -type f -delete || cleanup_status=1
  find "$fixture_dir" -depth -type d -exec rmdir {} \; || cleanup_status=1
  set -e
  trap - EXIT
  if [[ "$test_status" -ne 0 ]]; then
    exit "$test_status"
  fi
  exit "$cleanup_status"
}
trap cleanup EXIT

before_status="$(git -C "$ROOT_DIR/.." status --short --untracked-files=all)"

SOURCE_DATE_EPOCH=1767225600 "$ROOT_DIR/bin/package" plugin gama-contact
cp "$ZIP_PATH" "$fixture_dir/first.zip"
cp "$MANIFEST_PATH" "$fixture_dir/first.manifest"
cp "$SHA_PATH" "$fixture_dir/first.sha256"

SOURCE_DATE_EPOCH=1767225600 "$ROOT_DIR/bin/package" plugin gama-contact

cmp "$fixture_dir/first.zip" "$ZIP_PATH"
cmp "$fixture_dir/first.manifest" "$MANIFEST_PATH"
cmp "$fixture_dir/first.sha256" "$SHA_PATH"

after_status="$(git -C "$ROOT_DIR/.." status --short --untracked-files=all)"
if [[ "$before_status" != "$after_status" ]]; then
  echo "Package build changed tracked or untracked source state." >&2
  exit 1
fi

expected_entries="$fixture_dir/expected-entries.txt"
cat >"$expected_entries" <<'EOF'
gama-contact/
gama-contact/CHANGELOG.md
gama-contact/LICENSE
gama-contact/README.md
gama-contact/assets/
gama-contact/assets/contact-form.css
gama-contact/assets/contact-form.js
gama-contact/gama-contact.php
gama-contact/languages/
gama-contact/languages/gama-contact.pot
gama-contact/readme.txt
gama-contact/src/
gama-contact/src/Form/
gama-contact/src/Form/FormRenderer.php
gama-contact/src/Form/SubmissionController.php
gama-contact/src/Form/Validator.php
gama-contact/src/Lifecycle/
gama-contact/src/Lifecycle/Activator.php
gama-contact/src/Lifecycle/Deactivator.php
gama-contact/src/Lifecycle/Uninstaller.php
gama-contact/src/Plugin.php
gama-contact/src/Support/
gama-contact/src/Support/I18n.php
gama-contact/uninstall.php
EOF

unzip -Z1 "$ZIP_PATH" | LC_ALL=C sort >"$fixture_dir/actual-entries.txt"
LC_ALL=C sort "$expected_entries" -o "$expected_entries"
diff -u "$expected_entries" "$fixture_dir/actual-entries.txt"

entry_count="$(unzip -Z1 "$ZIP_PATH" | wc -l | tr -d ' ')"
if [[ "$entry_count" -ne 24 ]]; then
  echo "Expected 24 normalized archive entries; found $entry_count." >&2
  exit 1
fi

archive_timestamps="$(zipinfo -T "$ZIP_PATH" | awk '$NF ~ /^gama-contact\// { print $(NF - 1) }' | LC_ALL=C sort -u)"
if [[ "$archive_timestamps" != '20260101.000000' ]]; then
  echo "Package timestamps do not match SOURCE_DATE_EPOCH in UTC: $archive_timestamps" >&2
  exit 1
fi
if zipinfo -l "$ZIP_PATH" | awk '$NF ~ /^gama-contact\// { print $1 }' | grep -Ev '^(drwxr-xr-x|-rw-r--r--)$'; then
  echo "Package contains a non-normalized file mode." >&2
  exit 1
fi

if unzip -Z1 "$ZIP_PATH" | grep -Eq '(^/|(^|/)\.\.(/|$)|(^|/)(vendor|node_modules|tests|uploads|cache|logs)(/|$)|(^|/)\.env|\.log$)'; then
  echo "Package contains an unsafe or development-only path." >&2
  exit 1
fi

if unzip -Z1 "$ZIP_PATH" | cut -d/ -f1 | LC_ALL=C sort -u | grep -Fvx 'gama-contact'; then
  echo "Package contains more than the gama-contact top-level directory." >&2
  exit 1
fi

unzip -p "$ZIP_PATH" gama-contact/gama-contact.php | grep -F 'Version: 0.2.0'
unzip -p "$ZIP_PATH" gama-contact/gama-contact.php | grep -F 'Requires at least: 7.1'
unzip -p "$ZIP_PATH" gama-contact/gama-contact.php | grep -F 'Requires PHP: 8.4'
unzip -p "$ZIP_PATH" gama-contact/gama-contact.php | grep -F 'License: GPL-2.0-or-later'
unzip -p "$ZIP_PATH" gama-contact/readme.txt | grep -F 'Stable tag: 0.2.0'
unzip -p "$ZIP_PATH" gama-contact/LICENSE | grep -F 'GNU GENERAL PUBLIC LICENSE'

LC_ALL=C sort -c "$MANIFEST_PATH"
recorded_zip_sha="$(cut -d' ' -f1 "$SHA_PATH")"
actual_zip_sha="$(shasum -a 256 "$ZIP_PATH" | cut -d' ' -f1)"
if [[ "$recorded_zip_sha" != "$actual_zip_sha" ]]; then
  echo "Recorded ZIP checksum does not match the artifact." >&2
  exit 1
fi

if "$ROOT_DIR/bin/package" theme gama-contact; then
  echo "Package command accepted an unsupported type." >&2
  exit 1
fi

if "$ROOT_DIR/bin/package" plugin ../gama-contact; then
  echo "Package command accepted an unsafe slug." >&2
  exit 1
fi

create_unique_symlink_fixture
injected_symlink="$created_path"
if SOURCE_DATE_EPOCH=1767225600 "$ROOT_DIR/bin/package" plugin gama-contact; then
  echo "Package command accepted a source symlink." >&2
  exit 1
fi
unlink "$injected_symlink"

old_static_sentinel="$plugin_source/developer-only.txt"
if ! (set -o noclobber; printf '%s\n' 'pre-existing-user-sentinel' >"$old_static_sentinel") 2>/dev/null; then
  echo "Static sentinel path already exists; refusing to overwrite it: $old_static_sentinel" >&2
  exit 1
fi
owned_source_paths+=("$old_static_sentinel")
sentinel_sha_before="$(shasum -a 256 "$old_static_sentinel" | cut -d' ' -f1)"

create_unique_regular_fixture extra-file
injected_file="$created_path"
printf '%s\n' 'development only' >"$injected_file"
if SOURCE_DATE_EPOCH=1767225600 "$ROOT_DIR/bin/package" plugin gama-contact; then
  echo "Package command accepted a file outside its positive allowlist." >&2
  exit 1
fi
sentinel_sha_after="$(shasum -a 256 "$old_static_sentinel" | cut -d' ' -f1)"
if [[ "$sentinel_sha_after" != "$sentinel_sha_before" ]]; then
  echo "Package contract changed the pre-existing static sentinel." >&2
  exit 1
fi
unlink "$injected_file"
unlink "$old_static_sentinel"

failure_fixture_record="$fixture_dir/failure-fixture-path.txt"
set +e
(
  owned_source_paths=()
  trap 'failure_status=$?; cleanup_owned_source_paths; exit "$failure_status"' EXIT
  create_unique_regular_fixture forced-failure
  printf '%s\n' "$created_path" >"$failure_fixture_record"
  exit 73
)
failure_status=$?
set -e
failure_fixture="$(<"$failure_fixture_record")"
if [[ "$failure_status" -ne 73 || -e "$failure_fixture" || -L "$failure_fixture" ]]; then
  echo "Failure-path cleanup did not remove only its owned source fixture." >&2
  exit 1
fi
