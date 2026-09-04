#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
spec="$ROOT_DIR/qa/e2e/specs/release-regression.spec.ts"
runtime="$ROOT_DIR/tests/release-regression-runtime.sh"

[[ -f "$spec" && -x "$runtime" ]]
grep -Fq "from '@axe-core/playwright'" "$spec"
grep -Fq "['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']" "$spec"
grep -Fq '@release-regression' "$spec"
grep -Fq 'timeToFirstByte' "$spec"
grep -Fq 'transferredBytes' "$spec"
grep -Fq 'consoleErrors: []' "$spec"
grep -Fq 'failedRequests: []' "$spec"
grep -Fq 'report/index.html' "$runtime"
grep -Fq 'test-results/.last-run.json' "$runtime"
grep -Fq 'browser-artifacts.tar' "$runtime"
grep -Fq 'release-regression-runtime.sh' "$ROOT_DIR/tests/staging-rollback-runtime.sh"

echo 'Release regression, WCAG and performance evidence contract passed.'
