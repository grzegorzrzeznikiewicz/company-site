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

if [[ ! -x "$ROOT_DIR/tests/wordpress-assets-quality.sh" \
  || ! -x "$ROOT_DIR/tests/wordpress-php-quality.sh" ]]; then
  echo 'WordPress asset and PHP quality gates must be executable.' >&2
  exit 1
fi

printf '%s\n' 'const broken = ;' >"$fixture/invalid.js"
expect_failure javascript-lint "$ROOT_DIR/tests/wordpress-assets-quality.sh" \
  --javascript "$fixture/invalid.js"

printf '%s\n' 'a { color: #zzzzzz; }' >"$fixture/invalid.css"
expect_failure css-lint "$ROOT_DIR/tests/wordpress-assets-quality.sh" \
  --css "$fixture/invalid.css"

cat >"$fixture/static-analysis-error.php" <<'PHP'
<?php

function gama_ci_requires_string( string $value ): void {
	echo esc_html( $value );
}

gama_ci_requires_string( 42 );
PHP
expect_failure static-analysis "$ROOT_DIR/tests/wordpress-php-quality.sh" \
  --phpstan "$fixture/static-analysis-error.php"

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
echo 'Controlled PHP/JS/CSS lint, static-analysis, test, build and secret-detection failure contracts passed.'
