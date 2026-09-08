#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOSITORY_ROOT="$ROOT_DIR/.."
staging_workflow="$REPOSITORY_ROOT/.github/workflows/wordpress-staging.yml"
production_workflow="$REPOSITORY_ROOT/.github/workflows/wordpress-production.yml"
rollback_workflow="$REPOSITORY_ROOT/.github/workflows/wordpress-production-rollback.yml"
deploy="$ROOT_DIR/bin/deploy-production"
rollback="$ROOT_DIR/bin/rollback-production"

for file in "$production_workflow" "$rollback_workflow" "$deploy" "$rollback"; do
  [[ -f "$file" ]]
done
[[ ! -e "$staging_workflow" ]]
# Workflow trust/permission/dependency checks run through the pinned YAML parser
# in wordpress-ci-contract.sh; extracted shell and host boundaries run separately.
for workflow in "$production_workflow" "$rollback_workflow"; do
  if grep -Eq 'docker/build-push-action|docker build|build-release|gama-wp-production-candidate-|docker volume rm|rm -rf' "$workflow"; then
    echo 'Production entry points must consume verified artifacts and preserve runtime data.' >&2
    exit 1
  fi
done

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
