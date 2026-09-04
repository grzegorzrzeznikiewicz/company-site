#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOSITORY_ROOT="$ROOT_DIR/.."
staging_workflow="$REPOSITORY_ROOT/.github/workflows/wordpress-staging.yml"
production_workflow="$REPOSITORY_ROOT/.github/workflows/wordpress-production.yml"
rollback_workflow="$REPOSITORY_ROOT/.github/workflows/wordpress-production-rollback.yml"
deploy="$ROOT_DIR/bin/deploy-production"
rollback="$ROOT_DIR/bin/rollback-production"

for file in "$staging_workflow" "$production_workflow" "$rollback_workflow" "$deploy" "$rollback"; do
  [[ -f "$file" ]]
done

grep -Fq 'wordpress-staging-release-${{ inputs.git_sha }}' "$staging_workflow"
grep -Fq 'actions/upload-artifact@' "$staging_workflow"
grep -Fq 'staging-release.json' "$staging_workflow"

grep -Fq 'name: WordPress Production Deployment' "$production_workflow"
grep -Fq 'workflow_dispatch:' "$production_workflow"
grep -Fq 'staging_run_id:' "$production_workflow"
grep -Fq "gh run view" "$production_workflow"
grep -Fq "gh run download" "$production_workflow"
grep -Fq 'WordPress Staging Deployment|success' "$production_workflow"
grep -Fq 'environment: wordpress-production' "$production_workflow"
grep -Fq 'environment: wordpress-production-cutover' "$production_workflow"
grep -Fq 'gama-wp-production-candidate-' "$production_workflow"
grep -Fq 'cleanup_candidate' "$production_workflow"
grep -Fq 'name: Remove isolated candidate resources' "$production_workflow"
grep -Fq 'candidate.env' "$production_workflow"
grep -Fq 'down --volumes --remove-orphans' "$production_workflow"
grep -Fq 'No running production WordPress exists, but its namespace is not empty' "$production_workflow"
grep -Fq 'PRODUCTION_BACKUP_ROOT' "$production_workflow"
grep -Fq 'PRODUCTION_BACKUP_EXPECTED_SOURCE' "$production_workflow"
grep -Fq 'PRODUCTION_SMOKE_RECIPIENT' "$production_workflow"
grep -Fq 'wordpress/bin/backup' "$production_workflow"
grep -Fq 'wp_mail' "$production_workflow"
grep -Fq '/usr/local/sbin/gama-wordpress-cutover' "$production_workflow"
grep -Fq 'recover_stable_on_error' "$production_workflow"
grep -Fq 'if: ${{ failure() }}' "$production_workflow"
grep -Fq '/usr/local/sbin/gama-wordpress-rollback-routing' "$production_workflow"
grep -Fq 'gama-wp-production' "$production_workflow"
grep -Fq 'deploy-production' "$production_workflow"
if grep -Eq 'docker/build-push-action|docker build|build-release' "$production_workflow"; then
  echo 'Production must promote the staging-tested image without rebuilding it.' >&2
  exit 1
fi
if grep -Eq 'uses:[[:space:]]+[^[:space:]]+@(v[0-9]|main|master)([[:space:]#]|$)' "$production_workflow" "$rollback_workflow"; then
  echo 'Production workflows must pin third-party actions to full commit SHAs.' >&2
  exit 1
fi
if grep -Fq 'cp "$target/.env"' "$production_workflow" "$rollback_workflow"; then
  echo 'Production workflows must not duplicate the secret-bearing host env file.' >&2
  exit 1
fi
if grep -Eq '^  (push|pull_request|schedule):' "$production_workflow" "$rollback_workflow"; then
  echo 'Production deployment and rollback must remain manual-only workflows.' >&2
  exit 1
fi
if grep -Eq -- "--project-name gama-wp-production([ \"']|$).*(down|rm).*(--volumes|-v)|docker volume rm|rm -rf" "$production_workflow"; then
  echo 'Production deployment must not remove stable persistent data.' >&2
  exit 1
fi

grep -Fq 'name: WordPress Production Rollback' "$rollback_workflow"
grep -Fq 'workflow_dispatch:' "$rollback_workflow"
grep -Fq 'environment: wordpress-production-rollback' "$rollback_workflow"
grep -Fq 'rollback-production' "$rollback_workflow"
grep -Fq '/usr/local/sbin/gama-wordpress-rollback-routing' "$rollback_workflow"
grep -Fq '"$target/bin/backup"' "$rollback_workflow"
if grep -Eq 'docker compose[^\n]*(down|rm).*(--volumes|-v)|docker volume rm|rm -rf' "$rollback_workflow"; then
  echo 'Production rollback must preserve database and uploads.' >&2
  exit 1
fi

grep -Fq 'gama-wp-production' "$deploy"
grep -Fq 'gama-wp-production-candidate-' "$deploy"
grep -Fq -- '--http-port' "$deploy"
grep -Fq 'WP_ENVIRONMENT_TYPE must be production' "$deploy"
grep -Fq 'Production mail sink must be disabled' "$deploy"
grep -Fq 'This command does not switch public traffic' "$deploy"
grep -Fq 'exec "$ROOT_DIR/bin/deploy-production"' "$rollback"
grep -Fq 'wordpress/tests/production-deployment-runtime.sh' "$REPOSITORY_ROOT/.github/workflows/wordpress-ci.yml"

zero_image="sha256:$(printf '0%.0s' {1..64})"
if "$deploy" --project gama-wp-production --env-file /tmp/missing --image "$zero_image" --http-port 8080 --confirm-image "$zero_image" 2>/dev/null; then
  echo 'Production deploy accepted a missing environment file.' >&2
  exit 1
fi

fixture_dir="$(mktemp -d "${TMPDIR:-/tmp}/gama-production-contract.XXXXXX")"
trap 'find "$fixture_dir" -type f -delete; rmdir "$fixture_dir"' EXIT
invalid_env="$fixture_dir/invalid.env"
printf '%s\n' \
  'WP_ENVIRONMENT_TYPE=production' \
  'WP_HOME=https://gama-software.com' \
  'GAMA_MAIL_SINK_HOST=' \
  'GAMA_SMTP_HOST=bad host' \
  'GAMA_SMTP_PORT=587' \
  'GAMA_SMTP_USERNAME=user' \
  'GAMA_SMTP_PASSWORD=password' \
  'GAMA_SMTP_ENCRYPTION=tls' \
  >"$invalid_env"
if "$deploy" --project gama-wp-production --env-file "$invalid_env" --image "$zero_image" --http-port 8080 --confirm-image "$zero_image" >"$fixture_dir/output" 2>&1; then
  echo 'Production deploy accepted an SMTP host rejected by the runtime plugin.' >&2
  exit 1
fi
grep -Fq 'Production SMTP host must be external.' "$fixture_dir/output"

echo 'Gated production promotion and data-preserving rollback contract passed.'
