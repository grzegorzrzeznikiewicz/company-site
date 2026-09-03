#!/usr/bin/env bash
set -euo pipefail

# This test catches non-portable, incomplete, or non-reproducible plugin ZIPs.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"
ZIP_PATH="$DIST_DIR/gama-contact-0.1.0.zip"
MANIFEST_PATH="$DIST_DIR/gama-contact-0.1.0.manifest.txt"
SHA_PATH="$DIST_DIR/gama-contact-0.1.0.zip.sha256"
fixture_dir="$(mktemp -d "${TMPDIR:-/tmp}/gama-package-contract.XXXXXX")"
injected_symlink="$ROOT_DIR/plugins/gama-contact/forbidden-link.php"
injected_file="$ROOT_DIR/plugins/gama-contact/developer-only.txt"

cleanup() {
  [[ ! -L "$injected_symlink" ]] || unlink "$injected_symlink"
  [[ ! -f "$injected_file" ]] || unlink "$injected_file"
  find "$fixture_dir" -type f -delete
  rmdir "$fixture_dir"
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
gama-contact/gama-contact.php
gama-contact/languages/
gama-contact/languages/gama-contact.pot
gama-contact/readme.txt
gama-contact/src/
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
if [[ "$entry_count" -ne 17 ]]; then
  echo "Expected 17 normalized archive entries; found $entry_count." >&2
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

unzip -p "$ZIP_PATH" gama-contact/gama-contact.php | grep -F 'Version: 0.1.0'
unzip -p "$ZIP_PATH" gama-contact/gama-contact.php | grep -F 'Requires at least: 7.1'
unzip -p "$ZIP_PATH" gama-contact/gama-contact.php | grep -F 'Requires PHP: 8.4'
unzip -p "$ZIP_PATH" gama-contact/gama-contact.php | grep -F 'License: GPL-2.0-or-later'
unzip -p "$ZIP_PATH" gama-contact/readme.txt | grep -F 'Stable tag: 0.1.0'
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

ln -s gama-contact.php "$injected_symlink"
if SOURCE_DATE_EPOCH=1767225600 "$ROOT_DIR/bin/package" plugin gama-contact; then
  echo "Package command accepted a source symlink." >&2
  exit 1
fi
unlink "$injected_symlink"

printf '%s\n' 'development only' >"$injected_file"
if SOURCE_DATE_EPOCH=1767225600 "$ROOT_DIR/bin/package" plugin gama-contact; then
  echo "Package command accepted a file outside its positive allowlist." >&2
  exit 1
fi
unlink "$injected_file"
