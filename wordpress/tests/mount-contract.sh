#!/usr/bin/env bash
set -euo pipefail

# This test catches bind mounts that make WordPress Core's wp-content parent
# directories read-only during the official image's first-start copy.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
resolved_config="$(
  docker compose \
    --project-name gama-wordpress \
    --env-file "$ROOT_DIR/.env.example" \
    --file "$ROOT_DIR/compose.yaml" \
    config --format json
)"

for parent_target in \
  /var/www/html/wp-content/themes \
  /var/www/html/wp-content/plugins; do
  if grep -Fq "\"target\": \"$parent_target\"" <<<"$resolved_config"; then
    echo "Refusing parent mount at $parent_target; a read-only parent blocks the WordPress Core copy." >&2
    exit 1
  fi
done

for project_target in \
  /var/www/html/wp-content/themes/gama-software \
  /var/www/html/wp-content/plugins/gama-local-mailpit \
  /var/www/html/wp-content/plugins/gama-contact \
  /var/www/html/wp-content/plugins/gama-seo \
  /var/www/html/wp-content/plugins/gama-security; do
  readonly_mount_count="$(
    grep -F -A1 "\"target\": \"$project_target\"" <<<"$resolved_config" |
      grep -Fc '"read_only": true' || true
  )"
  if [[ "$readonly_mount_count" -ne 2 ]]; then
    echo "Expected $project_target to be mounted read-only in wordpress and wp; found $readonly_mount_count mounts." >&2
    exit 1
  fi
done
