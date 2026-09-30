#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
runtime="$ROOT_DIR/tests/contact-form-browser-runtime.sh"
spec="$ROOT_DIR/qa/e2e/specs/contact-form.spec.ts"
smoke="$ROOT_DIR/tests/runtime-smoke.sh"

[[ -x "$runtime" ]]
[[ -f "$spec" ]]
grep -Fq '@contact-form' "$spec"
grep -Fq 'MAILPIT_API_URL' "$spec"
grep -Fq 'GAMA_PLAYWRIGHT_RUN=contact-form' "$runtime"
grep -Fq -- '--grep @contact-form' "$runtime"
grep -Fq '/artifacts/contact-form/report/index.html' "$runtime"
grep -Fq '/artifacts/contact-form/test-results/.last-run.json' "$runtime"
grep -Fq 'contact-form-browser-runtime.sh' "$smoke"

echo 'Reproducible browser contact form gate contract passed.'
