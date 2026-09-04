#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fixture_dir="$(mktemp -d "${TMPDIR:-/tmp}/gama-theme-package.XXXXXX")"
theme_source="$ROOT_DIR/theme/gama-software"
theme_version="$(sed -nE 's/^[[:space:]]*Version:[[:space:]]*([^[:space:]]+)[[:space:]]*$/\1/p' "$theme_source/style.css")"
[[ "$theme_version" == '0.3.0' ]]
ZIP_PATH="$ROOT_DIR/dist/gama-software-$theme_version.zip"
MANIFEST_PATH="$ROOT_DIR/dist/gama-software-$theme_version.manifest.txt"
SHA_PATH="$ROOT_DIR/dist/gama-software-$theme_version.zip.sha256"
owned_source_paths=()

cleanup() {
  local test_status=$? cleanup_status=0 owned_path
  set +e
  for owned_path in ${owned_source_paths[@]+"${owned_source_paths[@]}"}; do
    if [[ -L "$owned_path" || -f "$owned_path" ]]; then unlink "$owned_path" || cleanup_status=1; fi
  done
  find "$fixture_dir" -type f -delete || cleanup_status=1
  find "$fixture_dir" -depth -type d -exec rmdir {} \; || cleanup_status=1
  set -e
  trap - EXIT
  [[ "$test_status" -eq 0 ]] || exit "$test_status"
  exit "$cleanup_status"
}
trap cleanup EXIT

before_status="$(git -C "$ROOT_DIR/.." status --short --untracked-files=all)"
SOURCE_DATE_EPOCH=1767225600 "$ROOT_DIR/bin/package" theme gama-software
cp "$ZIP_PATH" "$fixture_dir/first.zip"
cp "$MANIFEST_PATH" "$fixture_dir/first.manifest"
cp "$SHA_PATH" "$fixture_dir/first.sha256"
SOURCE_DATE_EPOCH=1767225600 "$ROOT_DIR/bin/package" theme gama-software
cmp "$fixture_dir/first.zip" "$ZIP_PATH"
cmp "$fixture_dir/first.manifest" "$MANIFEST_PATH"
cmp "$fixture_dir/first.sha256" "$SHA_PATH"
[[ "$before_status" == "$(git -C "$ROOT_DIR/.." status --short --untracked-files=all)" ]]

cat >"$fixture_dir/expected-files.txt" <<'EOF'
CHANGELOG.md
LICENSE
README.md
functions.php
languages/gama-software.pot
parts/footer.html
parts/header.html
patterns/hero.php
patterns/not-found.php
style.css
templates/404.html
templates/archive.html
templates/front-page.html
templates/home.html
templates/index.html
templates/page.html
templates/search.html
templates/single.html
theme.json
EOF
while IFS= read -r file; do printf 'gama-software/%s\n' "$file"; done <"$fixture_dir/expected-files.txt" >"$fixture_dir/expected-entries.txt"
printf '%s\n' 'gama-software/' 'gama-software/languages/' 'gama-software/parts/' 'gama-software/patterns/' 'gama-software/templates/' >>"$fixture_dir/expected-entries.txt"
LC_ALL=C sort -o "$fixture_dir/expected-entries.txt" "$fixture_dir/expected-entries.txt"
unzip -Z1 "$ZIP_PATH" | LC_ALL=C sort >"$fixture_dir/actual-entries.txt"
diff -u "$fixture_dir/expected-entries.txt" "$fixture_dir/actual-entries.txt"
[[ "$(unzip -Z1 "$ZIP_PATH" | wc -l | tr -d ' ')" -eq 24 ]]
[[ "$(zipinfo -T "$ZIP_PATH" | awk '$NF ~ /^gama-software\// { print $(NF - 1) }' | LC_ALL=C sort -u)" == '20260101.000000' ]]
if zipinfo -l "$ZIP_PATH" | awk '$NF ~ /^gama-software\// { print $1 }' | grep -Ev '^(drwxr-xr-x|-rw-r--r--)$'; then exit 1; fi
if unzip -Z1 "$ZIP_PATH" | grep -Eq '(^/|(^|/)\.\.(/|$)|(^|/)(vendor|node_modules|tests|qa|uploads|cache|logs)(/|$)|(^|/)\.env|\.log$)'; then exit 1; fi
LC_ALL=C sort -c "$MANIFEST_PATH"
[[ "$(cut -d' ' -f1 "$SHA_PATH")" == "$(shasum -a 256 "$ZIP_PATH" | cut -d' ' -f1)" ]]
unzip -p "$ZIP_PATH" gama-software/style.css | grep -Fq "Version: $theme_version"
unzip -p "$ZIP_PATH" gama-software/LICENSE | grep -Fq 'GNU GENERAL PUBLIC LICENSE'

if grep -Eq 'gama-software-0\.[0-9]+\.[0-9]+' "$ROOT_DIR/bin/package" "$ROOT_DIR/bin/test-package"; then
  echo 'Shared package consumers hard-code a concrete theme version.' >&2
  exit 1
fi

for kind in symlink extra; do
  candidate="$theme_source/.gama-theme-package-$$-$RANDOM-$kind"
  if [[ "$kind" == symlink ]]; then ln -s style.css "$candidate"; else (set -o noclobber; printf 'fixture\n' >"$candidate"); fi
  owned_source_paths+=("$candidate")
  if SOURCE_DATE_EPOCH=1767225600 "$ROOT_DIR/bin/package" theme gama-software; then
    echo "Theme package accepted forbidden $kind fixture." >&2
    exit 1
  fi
  unlink "$candidate"
done

echo 'Deterministic theme package contract passed.'
