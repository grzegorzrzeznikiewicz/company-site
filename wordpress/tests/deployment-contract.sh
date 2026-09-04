#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
dockerfile="$ROOT_DIR/runtime/Dockerfile"
compose="$ROOT_DIR/deploy/compose.yaml"
deploy="$ROOT_DIR/bin/deploy-staging"
rollback="$ROOT_DIR/bin/rollback-staging"
workflow="$ROOT_DIR/../.github/workflows/wordpress-staging.yml"

for file in "$dockerfile" "$compose" "$deploy" "$rollback" "$workflow" "$ROOT_DIR/deploy/staging.override.yaml" "$ROOT_DIR/deploy/nginx-wordpress.conf.example"; do
  [[ -f "$file" ]]
done
grep -Fq 'wordpress:7.1.0-php8.4-apache@sha256:' "$dockerfile"
grep -Fq 'wordpress:cli-2.12.0-php8.4@sha256:' "$dockerfile"
grep -Fq 'org.opencontainers.image.revision' "$dockerfile"
grep -Fq 'mariadb:10.11.18-jammy@sha256:' "$compose"
grep -Fq '${WORDPRESS_IMAGE:?immutable image digest required}' "$compose"
grep -Fq 'database:/var/lib/mysql' "$compose"
grep -Fq 'uploads:/var/www/html/wp-content/uploads' "$compose"
grep -Fq 'uploads:/uploads' "$compose"
grep -Fq 'gama-wordpress-install-release' "$compose"
grep -Fq "define('DISALLOW_FILE_MODS', true);" "$compose"
grep -Fq 'WORDPRESS_IMAGE must be an immutable image digest' "$deploy"
grep -Fq 'gama-wp-staging-' "$deploy"
grep -Fq 'gama-wp-staging-' "$rollback"
grep -Fq "gh run list --workflow 'WordPress Quality Gates'" "$workflow"
grep -Fq 'STAGING_GHCR_TOKEN' "$workflow"
grep -Fq 'environment: wordpress-staging' "$workflow"
if grep -Fq 'environment: production' "$workflow"; then
  echo 'GSWEB-26 staging workflow unexpectedly targets production.' >&2
  exit 1
fi
if grep -Eq '/Users/|/home/|\.\./theme|\.\./plugins' "$compose"; then
  echo 'Deployment Compose contains a checkout or user path.' >&2
  exit 1
fi
if "$deploy" --project gama-wp-production --env-file /tmp/missing --confirm 2>/dev/null; then
  echo 'Staging deploy accepted a production target.' >&2
  exit 1
fi

echo 'Immutable deployment, persistent data and staging-only rollback contract passed.'
