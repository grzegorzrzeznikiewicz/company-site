#!/usr/bin/env bash
set -euo pipefail

# This fixture catches case-sensitive technical-verdict matching and any
# weakening of the required Gate C NO-GO or remote-CI evidence markers.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fixture_dir="$(mktemp -d "${TMPDIR:-/tmp}/gama-release-acceptance-contract.XXXXXX")"
fixture_root="$fixture_dir/repository"
fixture_wordpress="$fixture_root/wordpress"
fixture_docs="$fixture_root/docs/agent-workflows/wordpress-migration"
fixture_contract="$fixture_wordpress/tests/release-acceptance-contract.sh"
fixture_gate_report="$fixture_docs/GSWEB-28-gate-c.md"

cleanup() {
  find "$fixture_dir" -type l -delete
  find "$fixture_dir" -type f -delete
  find "$fixture_dir" -depth -type d -exec rmdir {} \;
}
trap cleanup EXIT

mkdir -p "$fixture_wordpress/qa/e2e/specs" "$fixture_wordpress/tests" "$fixture_docs"
ln -s "$ROOT_DIR/tests/release-acceptance-contract.sh" "$fixture_contract"

printf '%s\n' \
  '@release-acceptance-editor' \
  '@release-acceptance-admin' \
  '/wp-admin/plugins.php' \
  '/wp-admin/site-editor.php' \
  '/wp/v2/media' \
  '/wp/v2/users' \
  'wp_template_part' \
  'Start próby stagingu' \
  'Kontakt próby stagingu' \
  'Stopka próby stagingu' \
  >"$fixture_wordpress/qa/e2e/specs/release-acceptance.spec.ts"
printf '%s\n' '#!/usr/bin/env bash' '@contact-form' \
  >"$fixture_wordpress/tests/release-acceptance-runtime.sh"
chmod +x "$fixture_wordpress/tests/release-acceptance-runtime.sh"
printf '%s\n' 'release-acceptance-runtime.sh' \
  >"$fixture_wordpress/tests/staging-rollback-runtime.sh"
printf '%s\n' 'Gate C' 'NO-GO' 'production' \
  >"$fixture_docs/GSWEB-28-staging-acceptance.md"

expect_accepted() {
  local name="$1"
  local gate_report="$2"
  local output

  printf '%s\n' "$gate_report" >"$fixture_gate_report"
  if ! output="$("$fixture_contract" 2>&1)"; then
    printf 'Acceptance contract rejected valid %s evidence:\n%s\n' "$name" "$output" >&2
    exit 1
  fi
}

expect_rejected() {
  local name="$1"
  local gate_report="$2"

  printf '%s\n' "$gate_report" >"$fixture_gate_report"
  if "$fixture_contract" >"$fixture_dir/$name.output" 2>&1; then
    echo "Acceptance contract accepted invalid $name evidence." >&2
    exit 1
  fi
}

expect_accepted historical-lowercase $'- Historical technical verdict\n- VERDICT: NO-GO\n- remote CI'
expect_accepted historical-capitalized $'- Historical Technical verdict\n- VERDICT: NO-GO\n- remote CI'
expect_rejected missing-technical-verdict $'- Historical release assessment\n- VERDICT: NO-GO\n- remote CI'
expect_rejected missing-no-go $'- Historical technical verdict\n- VERDICT: GO\n- remote CI'
expect_rejected missing-remote-ci $'- Historical technical verdict\n- VERDICT: NO-GO\n- local evidence only'

echo 'Release acceptance contract regression fixtures passed.'
