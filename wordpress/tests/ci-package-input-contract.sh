#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fixture_dir="$(mktemp -d "${TMPDIR:-/tmp}/gama-ci-package-input.XXXXXX")"
fixture_root="$fixture_dir/wordpress"
resolver="$fixture_root/bin/require-ci-package"

cleanup() {
  find "$fixture_dir" -type f -delete 2>/dev/null || true
  find "$fixture_dir" -type l -delete 2>/dev/null || true
  find "$fixture_dir" -depth -type d -exec rmdir {} \; 2>/dev/null || true
}
trap cleanup EXIT

mkdir -p \
  "$fixture_root/bin" \
  "$fixture_root/dist" \
  "$fixture_root/plugins/gama-contact" \
  "$fixture_root/theme/gama-software"

if [[ ! -x "$ROOT_DIR/bin/require-ci-package" ]]; then
  echo 'CI package input resolver is missing or not executable.' >&2
  exit 1
fi
ln -s "$ROOT_DIR/bin/require-ci-package" "$resolver"

cat >"$fixture_root/plugins/gama-contact/gama-contact.php" <<'EOF'
<?php
/**
 * Version: 0.3.2
 */
EOF
cat >"$fixture_root/theme/gama-software/style.css" <<'EOF'
/*
Version: 0.4.1
*/
EOF

expect_failure() {
  local label="$1"
  shift
  if "$@" >"$fixture_dir/$label.output" 2>&1; then
    echo "Controlled $label CI package input unexpectedly passed." >&2
    exit 1
  fi
}

touch "$fixture_root/dist/gama-contact-0.3.1.zip"
expect_failure stale-contact \
  "$resolver" plugin gama-contact "$fixture_root/dist/gama-contact-0.3.1.zip"
expect_failure missing-contact \
  "$resolver" plugin gama-contact "$fixture_root/dist/gama-contact-0.3.2.zip"
touch "$fixture_root/dist/gama-contact-0.3.2.zip"
[[ "$("$resolver" plugin gama-contact "$fixture_root/dist/gama-contact-0.3.2.zip")" == "$fixture_root/dist/gama-contact-0.3.2.zip" ]]

touch "$fixture_root/dist/gama-software-0.4.0.zip"
expect_failure stale-theme \
  "$resolver" theme gama-software "$fixture_root/dist/gama-software-0.4.0.zip"
expect_failure missing-theme \
  "$resolver" theme gama-software "$fixture_root/dist/gama-software-0.4.1.zip"
touch "$fixture_root/dist/gama-software-0.4.1.zip"
[[ "$("$resolver" theme gama-software "$fixture_root/dist/gama-software-0.4.1.zip")" == "$fixture_root/dist/gama-software-0.4.1.zip" ]]

echo 'CI package input contract passed.'
