#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
spec="$ROOT_DIR/qa/e2e/specs/release-acceptance.spec.ts"
runtime="$ROOT_DIR/tests/release-acceptance-runtime.sh"
runbook="$ROOT_DIR/../docs/agent-workflows/wordpress-migration/GSWEB-28-staging-acceptance.md"

test -f "$spec"
test -x "$runtime"
test -f "$runbook"
grep -Fq '@release-acceptance-editor' "$spec"
grep -Fq '@release-acceptance-admin' "$spec"
grep -Fq '/wp-admin/plugins.php' "$spec"
grep -Fq '/wp-admin/site-editor.php' "$spec"
grep -Fq '/wp/v2/media' "$spec"
grep -Fq '/wp/v2/users' "$spec"
grep -Fq 'release-acceptance-runtime.sh' "$ROOT_DIR/tests/staging-rollback-runtime.sh"
grep -Fq 'wp_template_part' "$spec"
grep -Fq 'Start próby stagingu' "$spec"
grep -Fq 'Kontakt próby stagingu' "$spec"
grep -Fq 'Stopka próby stagingu' "$spec"
grep -Fq '@contact-form' "$runtime"
grep -Fq 'Gate C' "$runbook"
grep -Fq 'NO-GO' "$runbook"
grep -Fq 'production' "$runbook"

echo 'GSWEB-28 immutable staging acceptance contract passed.'
