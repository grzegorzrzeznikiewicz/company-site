#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
workflow="$REPOSITORY_ROOT/.github/workflows/wordpress-ci.yml"
release_runtime="$REPOSITORY_ROOT/wordpress/tests/release-regression-runtime.sh"
fixture_dir="$(mktemp -d "${TMPDIR:-/tmp}/gama-wordpress-ci-contract.XXXXXX")"

cleanup() {
  find "$fixture_dir" -type f -delete
  find "$fixture_dir" -depth -type d -exec rmdir {} \;
}
trap cleanup EXIT

validate_source_contract_wiring() {
  local candidate="$1"
  local source_contracts

  source_contracts="$(awk '
    /^      - name: Validate source, policy and reproducible packages$/ { found = 1; next }
    found && /^      - name:/ { exit }
    found { print }
  ' "$candidate")"
  grep -Fxq '          wordpress/tests/release-acceptance-contract.sh' <<<"$source_contracts" \
    && grep -Fxq '          wordpress/tests/release-acceptance-contract-regression.sh' <<<"$source_contracts"
}

validate_release_collection_wiring() {
  local candidate="$1"
  local build_line collection_run_line collection_contract_line tls_line

  [[ "$(grep -Fc 'docker run --rm --network none --entrypoint node "$image"' "$candidate")" -eq 1 ]]
  [[ "$(grep -Fc './specs/support/release-matrix-contract.cjs' "$candidate")" -eq 1 ]]
  build_line="$(grep -nF 'docker build \' "$candidate" | cut -d: -f1)"
  collection_run_line="$(grep -nF 'docker run --rm --network none --entrypoint node "$image"' "$candidate" | cut -d: -f1)"
  collection_contract_line="$(grep -nF './specs/support/release-matrix-contract.cjs' "$candidate" | cut -d: -f1)"
  tls_line="$(grep -nF '"$ROOT_DIR/tests/release-https-runtime.sh"' "$candidate" | cut -d: -f1)"
  [[ "$build_line" -lt "$collection_run_line" \
    && "$collection_run_line" -le "$collection_contract_line" \
    && "$collection_contract_line" -lt "$tls_line" ]]
}

[[ -f "$workflow" ]]
[[ -x "$release_runtime" ]]
grep -Fq 'name: WordPress Quality Gates' "$workflow"
grep -Fq 'permissions:' "$workflow"
grep -Fq 'contents: read' "$workflow"
grep -Fq '${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}' "$workflow"
grep -Fq 'WordPress Source and Build' "$workflow"
grep -Fq 'WordPress Package Lifecycle' "$workflow"
grep -Fq 'WordPress Runtime and Restore' "$workflow"
grep -Fq 'WordPress Release Regression' "$workflow"
grep -Fq 'wordpress/tests/ci-failure-contract.sh' "$workflow"
validate_source_contract_wiring "$workflow"
grep -Fq 'wordpress/tests/wordpress-assets-quality.sh' "$workflow"
grep -Fq 'wordpress/tests/wordpress-php-quality.sh' "$workflow"
grep -Fq 'wordpress/tests/wordpress-dependency-audit.sh' "$workflow"
grep -Fq 'wordpress/bin/ci-image-cache restore source' "$workflow"
grep -Fq 'wordpress/bin/ci-image-cache save source' "$workflow"
grep -Fq 'wordpress/bin/ci-image-cache restore browser' "$workflow"
grep -Fq 'wordpress/bin/ci-image-cache save browser' "$workflow"
grep -Fq 'wordpress/tests/backup-restore-runtime.sh' "$workflow"
grep -Fq 'wordpress/tests/mail-transport-plugin-contract.sh' "$workflow"
grep -Fq 'wordpress/tests/production-deployment-contract.sh' "$workflow"
grep -Fq 'wordpress/tests/runtime-smoke.sh --clean' "$workflow"
grep -Fq 'wordpress/tests/staging-rollback-runtime.sh' "$workflow"
grep -Fq 'wordpress-packages-${{ github.sha }}' "$workflow"
grep -Fq 'actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1' "$workflow"
grep -Fq 'actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1' "$workflow"
grep -Fq 'actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c # v8.0.1' "$workflow"
grep -Fq 'actions/cache@55cc8345863c7cc4c66a329aec7e433d2d1c52a9 # v6.1.0' "$workflow"
if grep -E '^[[:space:]]*uses: [^#]+@(v[0-9]+|main|master)([[:space:]]|$)' "$workflow"; then
  echo 'Every third-party WordPress workflow action must use an immutable commit SHA.' >&2
  exit 1
fi
grep -Fq 'if: ${{ always() }}' "$workflow"

sed '/wordpress\/tests\/release-acceptance-contract.sh/d' "$workflow" \
  >"$fixture_dir/missing-acceptance.yml"
if validate_source_contract_wiring "$fixture_dir/missing-acceptance.yml"; then
  echo 'Source wiring contract accepted a workflow without the acceptance guard.' >&2
  exit 1
fi
sed '/wordpress\/tests\/release-acceptance-contract-regression.sh/d' "$workflow" \
  >"$fixture_dir/missing-acceptance-regression.yml"
if validate_source_contract_wiring "$fixture_dir/missing-acceptance-regression.yml"; then
  echo 'Source wiring contract accepted a workflow without the acceptance regression fixture.' >&2
  exit 1
fi

validate_release_collection_wiring "$release_runtime"
sed '/release-matrix-contract.cjs/d' "$release_runtime" \
  >"$fixture_dir/missing-release-collection.sh"
if validate_release_collection_wiring "$fixture_dir/missing-release-collection.sh"; then
  echo 'Release wiring contract accepted a runtime without matrix collection.' >&2
  exit 1
fi

for legacy in ci.yml deploy.yml rollback.yml; do
  [[ -f "$REPOSITORY_ROOT/.github/workflows/$legacy" ]]
done
[[ -f "$REPOSITORY_ROOT/.gitlab-ci.yml" ]]

echo 'WordPress CI workflow and legacy-pipeline preservation contract passed.'
