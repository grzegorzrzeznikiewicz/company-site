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

# Parse real YAML using the existing lock-pinned assets QA dependency. This is
# required by the source gate and also checks deliberate broken graph fixtures.
assets_image='gama-wordpress-assets-qa:gsweb25'
docker build --tag "$assets_image" --file "$REPOSITORY_ROOT/wordpress/qa/assets.Dockerfile" "$REPOSITORY_ROOT" >/dev/null
docker run --rm -i --network none --read-only \
  --mount "type=bind,src=$REPOSITORY_ROOT/.github/workflows,dst=/workflows,readonly" \
  --entrypoint node "$assets_image" <<'JS'
const assert = require('node:assert/strict');
const fs = require('node:fs');
const yaml = require('/qa/node_modules/js-yaml');
assert.equal(require('/qa/node_modules/js-yaml/package.json').version, '4.3.2');
const names = ['wordpress-ci.yml', 'wordpress-production.yml', 'wordpress-production-rollback.yml', 'deploy.yml', 'rollback.yml'];
const files = Object.fromEntries(names.map(name => [name, yaml.load(fs.readFileSync('/workflows/' + name, 'utf8'))]));
function check(all) {
  const wp = all['wordpress-production.yml'];
  const ci = all['wordpress-ci.yml'];
  const list = value => value === undefined ? [] : Array.isArray(value) ? value : [value];
  assert.deepEqual(Object.values(ci.jobs).map(job => job.name), [
    'WordPress Source and Build', 'WordPress Package Lifecycle',
    'WordPress Runtime and Restore', 'WordPress Release Regression']);
  assert.equal(ci.permissions.contents, 'read');
  assert(!JSON.stringify(ci).includes('secrets.'));
  assert.deepEqual(wp.on.workflow_run, {workflows: ['WordPress Quality Gates'], types: ['completed']});
  for (const [name, workflow] of Object.entries(all)) {
    assert(workflow.jobs && workflow.on && workflow.permissions);
    const jobs = workflow.jobs;
    const ancestors = (id, seen = new Set()) => {
      assert(jobs[id], 'missing dependency ' + id);
      assert(!seen.has(id), 'cyclic dependency ' + id);
      const next = new Set(seen).add(id);
      return list(jobs[id].needs).flatMap(parent => [parent, ...ancestors(parent, next)]);
    };
    if (name !== 'wordpress-ci.yml') {
      assert.deepEqual(workflow.concurrency, {group: 'wordpress-production', 'cancel-in-progress': false, queue: 'max'});
      assert(!Object.values(workflow.permissions).includes('write'));
    }
    for (const [id, job] of Object.entries(jobs)) {
      const chain = ancestors(id);
      const permissions = job.permissions || workflow.permissions;
      assert(!('administration' in permissions));
      const text = JSON.stringify(job);
      if (name !== 'wordpress-ci.yml' && (text.includes('secrets.') || Object.values(permissions).includes('write'))) {
        const boundary = name === 'deploy.yml' && id === 'read-only-audit' ? 'audit-guard'
          : name === 'wordpress-production-rollback.yml' ? 'prepare' : 'guard';
        assert(chain.includes(boundary));
      }
      for (const step of job.steps) {
        if (step.uses) assert(/^[^@]+@[a-f0-9]{40}$/.test(step.uses), 'mutable action');
        if ((name === 'wordpress-production.yml' || name === 'wordpress-production-rollback.yml') && step.uses?.startsWith('actions/checkout@')) {
          assert.equal(step.with.ref, 'refs/heads/main');
          assert.equal(step.with['persist-credentials'], false);
        }
        if (step.uses?.startsWith('appleboy/ssh-action@')) {
          assert.notEqual(permissions.packages, 'write');
          assert.equal(step.with.envs, 'RELEASE_REQUEST');
          assert(!/chmod|\binstall\b|candidate-|docker compose|docker login/.test(step.with.script));
          assert(step.with.script.includes('/srv/gama-wordpress-production/tools/wordpress/bin/production-'));
        }
      }
    }
  }
  assert.deepEqual(list(wp.jobs.validate.needs), ['guard', 'owner-gate']);
  assert(wp.jobs.validate.if.includes("needs.guard.outputs.operation == 'standard'"));
  assert(wp.jobs.validate.if.includes('!cancelled()'));
  assert.deepEqual(list(wp.jobs['owner-gate'].needs), ['guard', 'cutover-request']);
  assert.equal(Object.values(wp.jobs).filter(job => job.environment === 'wordpress-production-cutover').length, 1);
  assert.equal(wp.jobs.deploy.environment, 'wordpress-production');
  assert.equal(wp.jobs.publish.permissions.packages, 'write');
  assert.equal(wp.jobs.publish.environment, undefined);
  assert(!/SSH|SMTP|PRODUCTION_SERVER|PROD_MAILER/.test(JSON.stringify(wp.jobs.publish)));
  assert(!/secrets\./.test(JSON.stringify(wp.jobs['owner-gate'])));
  for (const [name, operation] of [['deploy.yml', 'deploy'], ['rollback.yml', 'rollback']]) {
    const guard = all[name].jobs.guard;
    assert.deepEqual(guard.permissions, {contents: 'read'});
    assert.equal(guard.steps.length, 2);
    assert(guard.steps[0].uses.startsWith('actions/checkout@'));
    assert.equal(guard.steps[0].with.ref, 'refs/heads/main');
    assert.equal(guard.steps[0].with['persist-credentials'], false);
    assert.equal(guard.steps[1].run.trim(), 'python3 -m wordpress.release.legacy guard ' + operation);
    assert(!/secrets\./.test(JSON.stringify(guard)));
  }
  const legacy = all['deploy.yml'];
  assert.equal(legacy.jobs.guard.if, "github.event_name != 'workflow_dispatch' || inputs.operation == 'legacy-release'");
  assert.deepEqual(legacy.on.workflow_dispatch.inputs.operation.options, ['legacy-release', 'read-only-audit']);
  const auditGuard = legacy.jobs['audit-guard'];
  const audit = legacy.jobs['read-only-audit'];
  assert.equal(auditGuard.if, "github.event_name == 'workflow_dispatch' && inputs.operation == 'read-only-audit'");
  assert(!JSON.stringify(auditGuard).includes('secrets.'));
  assert.equal(auditGuard.steps[1].run, 'python3 -m wordpress.release.server_audit guard');
  assert.equal(auditGuard.outputs.allowed, '${{ steps.guard.outputs.allowed }}');
  assert.equal(auditGuard.steps[1].id, 'guard');
  assert.deepEqual(list(audit.needs), ['audit-guard']);
  assert.equal(audit.if, "needs.audit-guard.outputs.allowed == 'true'");
  assert.equal(audit.steps[1].run, 'python3 -m wordpress.release.server_audit run');
  assert.deepEqual(Object.keys(audit.steps[1].env).sort(), ['SERVER_HOST', 'SERVER_SSH_FINGERPRINT', 'SERVER_USER', 'SSH_PORT', 'SSH_PRIVATE_KEY']);
  for (const job of [auditGuard, audit]) {
    assert.deepEqual(job.permissions, {contents: 'read'});
    assert.equal(job.steps.length, 2);
    assert.equal(job.steps[0].with.ref, '${{ github.sha }}');
    assert.equal(job.steps[0].with['persist-credentials'], false);
    assert.deepEqual(job.env, {INPUT_OPERATION: '${{ inputs.operation }}', GAMA_DEPLOYMENT_MODE: '${{ vars.GAMA_DEPLOYMENT_MODE }}'});
    assert.equal(job.environment, undefined);
    assert(job['timeout-minutes'] <= 3);
  }
  assert(list(wp.jobs.publish.needs).includes('validate'));
  assert(list(wp.jobs.deploy.needs).includes('publish'));
  assert.equal(all['wordpress-production-rollback.yml'].jobs.recover.environment, 'wordpress-production-rollback');
  const publisherSteps = wp.jobs.publish.steps;
  assert(publisherSteps.findIndex(s => s.name === 'Verify exact transport on publisher runner') < publisherSteps.findIndex(s => s.uses?.startsWith('docker/login-action@')));
  const releaseSteps = ci.jobs['release-regression'].steps;
  const seal = releaseSteps.findIndex(s => s.name === 'Build rehearse and seal one candidate');
  const upload = releaseSteps.findIndex(s => s.name === 'Upload sealed release transport');
  assert(seal >= 0 && upload > seal);
  assert.equal(releaseSteps[upload].if, undefined);
  assert.equal(releaseSteps[upload].with.name, 'wordpress-release-${{ github.sha }}-${{ github.run_id }}-${{ github.run_attempt }}');
  assert.deepEqual(releaseSteps[upload].with.path.trim().split('\n'), ['${{ runner.temp }}/release/image.tar', '${{ runner.temp }}/release/release.json']);
}
check(files);
for (const mutate of [
  f => { f['wordpress-production.yml'].jobs.publish.needs = []; },
  f => { f['wordpress-production.yml'].jobs.publish.env = {SMTP_PASSWORD: '${{ secrets.SMTP_PASSWORD }}'}; },
  f => { f['wordpress-production.yml'].jobs.validate.steps[0].with.ref = '${{ github.event.workflow_run.head_sha }}'; },
  f => { f['wordpress-production.yml'].permissions.packages = 'write'; },
  f => { f['wordpress-production.yml'].jobs.deploy.environment = 'wordpress-production-cutover'; },
  f => { f['deploy.yml'].jobs.deploy.steps[0].uses = 'actions/checkout@main'; },
  f => { f['wordpress-ci.yml'].jobs['release-regression'].steps.find(s => s.name === 'Upload sealed release transport').if = '${{ always() }}'; },
  f => { f['deploy.yml'].jobs.guard.steps[0].with.ref = '${{ github.event.workflow_run.head_sha }}'; },
  f => { f['rollback.yml'].jobs.guard.steps[1].run = 'python3 -m wordpress.release.legacy guard deploy'; },
  f => { f['rollback.yml'].jobs.guard.permissions.packages = 'write'; },
  f => { f['deploy.yml'].jobs.guard.if = 'always()'; },
  f => { f['deploy.yml'].jobs['read-only-audit'].needs = []; },
  f => { f['deploy.yml'].jobs['read-only-audit'].if = 'always()'; },
  f => { f['deploy.yml'].jobs['read-only-audit'].permissions.packages = 'write'; },
  f => { f['deploy.yml'].jobs['read-only-audit'].steps[0].with.ref = 'refs/heads/main'; },
  f => { f['deploy.yml'].jobs['read-only-audit'].steps[1].env.PROD_MAILER_DSN = '${{ secrets.PROD_MAILER_DSN }}'; },
  f => { f['deploy.yml'].jobs['audit-guard'].steps[1].run = 'echo allowed=true'; },
]) {
  const broken = structuredClone(files); mutate(broken);
  assert.throws(() => check(broken), 'broken workflow graph accepted');
}
console.log('Actual workflow YAML and seventeen negative permission/dependency fixtures passed.');
JS

echo 'WordPress CI workflow and legacy-pipeline preservation contract passed.'
