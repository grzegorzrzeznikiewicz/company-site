#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOSITORY_ROOT="$(cd "$ROOT_DIR/.." && pwd)"
fixture="$(mktemp -d "${TMPDIR:-/tmp}/gama-ci-failures.XXXXXX")"

cleanup() {
  find "$fixture" -type f -delete 2>/dev/null || true
  find "$fixture" -depth -type d -exec rmdir {} \; 2>/dev/null || true
}
trap cleanup EXIT

expect_failure() {
  local label="$1"
  shift
  if "$@" >"$fixture/$label.output" 2>&1; then
    echo "Controlled $label failure unexpectedly passed." >&2
    exit 1
  fi
}

printf '%s\n' '<?php function broken( {' >"$fixture/invalid.php"
expect_failure lint docker run --rm --network none --volume "$fixture:/fixture:ro" --entrypoint php \
  wordpress:cli-2.12.0-php8.4@sha256:1e1d1485277d15e0331b598b6e19972243128ead978b7134d758097d82116b99 \
  -l /fixture/invalid.php

printf '%s\n' '#!/usr/bin/env bash' 'exit 23' >"$fixture/failing-test.sh"
chmod +x "$fixture/failing-test.sh"
expect_failure test "$fixture/failing-test.sh"

expect_failure build env SOURCE_DATE_EPOCH=999999999999 "$ROOT_DIR/bin/package" plugin gama-contact

secret_repo="$fixture/secret-repo"
mkdir "$secret_repo"
git -C "$secret_repo" init --quiet
printf '%s' 'ghp_' 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJ' >"$secret_repo/fixture.txt"
git -C "$secret_repo" add fixture.txt
expect_failure secret "$ROOT_DIR/bin/check-secrets" "$secret_repo"

"$ROOT_DIR/bin/check-secrets" "$REPOSITORY_ROOT"
echo 'Controlled lint, test, build and secret-detection failure contracts passed.'
