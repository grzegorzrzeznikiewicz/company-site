#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
workflow="$REPOSITORY_ROOT/.github/workflows/wordpress-ci.yml"

[[ -f "$workflow" ]]
grep -Fq 'name: WordPress Quality Gates' "$workflow"
grep -Fq 'permissions:' "$workflow"
grep -Fq 'contents: read' "$workflow"
grep -Fq '${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}' "$workflow"
grep -Fq 'WordPress Source and Build' "$workflow"
grep -Fq 'WordPress Package Lifecycle' "$workflow"
grep -Fq 'WordPress Runtime and Restore' "$workflow"
grep -Fq 'WordPress Release Regression' "$workflow"
grep -Fq 'wordpress/tests/ci-failure-contract.sh' "$workflow"
grep -Fq 'wordpress/tests/backup-restore-runtime.sh' "$workflow"
grep -Fq 'wordpress/tests/runtime-smoke.sh --clean' "$workflow"
grep -Fq 'wordpress/tests/staging-rollback-runtime.sh' "$workflow"
grep -Fq 'wordpress-packages-${{ github.sha }}' "$workflow"
grep -Fq 'actions/upload-artifact@v4' "$workflow"
grep -Fq 'actions/download-artifact@v5' "$workflow"
grep -Fq 'if: ${{ always() }}' "$workflow"
for legacy in ci.yml deploy.yml rollback.yml; do
  [[ -f "$REPOSITORY_ROOT/.github/workflows/$legacy" ]]
done
[[ -f "$REPOSITORY_ROOT/.gitlab-ci.yml" ]]

echo 'WordPress CI workflow and legacy-pipeline preservation contract passed.'
