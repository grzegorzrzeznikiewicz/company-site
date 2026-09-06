#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_project="gama-wp-staging-backup-$RANDOM-$$"
restore_project="gama-restore-$RANDOM-$$"
fixture="$(mktemp -d "${TMPDIR:-/tmp}/gama-backup-contract.XXXXXX")"
env_file="$fixture/deployment.env"
backup="$fixture/backup"
marker="GSWEB24-restore-$(date +%s)-$$"
upload_name="$marker.txt"

cleanup() {
  local status=$?
  set +e
  if [[ -f "$env_file" ]]; then
    docker compose --project-name "$restore_project" --env-file "$env_file" --file "$ROOT_DIR/deploy/compose.yaml" --file "$ROOT_DIR/deploy/restore.override.yaml" down --volumes --remove-orphans >/dev/null 2>&1
    docker compose --project-name "$source_project" --env-file "$env_file" --file "$ROOT_DIR/deploy/compose.yaml" --file "$ROOT_DIR/deploy/staging.override.yaml" down --volumes --remove-orphans >/dev/null 2>&1
  fi
  find "$fixture" -type f -delete 2>/dev/null
  find "$fixture" -depth -type d -exec rmdir {} \; 2>/dev/null
  set -e
  trap - EXIT
  exit "$status"
}
trap cleanup EXIT

build_output="$("$ROOT_DIR/bin/build-release" --test-dirty backup-restore-source)"
source_image="$(sed -n 's/^Image ID: //p' <<<"$build_output")"
[[ "$source_image" =~ ^sha256:[a-f0-9]{64}$ ]]
printf '%s\n' \
  "WORDPRESS_IMAGE=$source_image" \
  'WORDPRESS_HTTP_PORT=' \
  'WP_DB_NAME=gama_backup_source' \
  'WP_DB_USER=gama_backup_source' \
  'WP_DB_PASSWORD=backup-database-test-only' \
  'WP_DB_ROOT_PASSWORD=backup-root-test-only' \
  'WP_HOME=http://wordpress' \
  'WP_SITE_TITLE=Gama Software Backup Source' \
  'WP_ADMIN_USER=admin' \
  'WP_ADMIN_PASSWORD=backup-admin-test-only' \
  'WP_ADMIN_EMAIL=admin@example.test' \
  'WP_ENVIRONMENT_TYPE=staging' \
  'GAMA_CONTACT_RECIPIENT=sink@example.test' \
  'GAMA_CONTACT_SENDER=no-reply@example.test' \
  'GAMA_MAIL_SINK_HOST=mailpit' \
  'GAMA_MAIL_SINK_PORT=1025' \
  >"$env_file"
chmod 0600 "$env_file"

SOURCE_COMPOSE=(docker compose --project-name "$source_project" --env-file "$env_file" --file "$ROOT_DIR/deploy/compose.yaml" --file "$ROOT_DIR/deploy/staging.override.yaml")
RESTORE_COMPOSE=(docker compose --project-name "$restore_project" --env-file "$env_file" --file "$ROOT_DIR/deploy/compose.yaml" --file "$ROOT_DIR/deploy/restore.override.yaml")

"$ROOT_DIR/bin/deploy-staging" --project "$source_project" --env-file "$env_file" --confirm
source_post_id="$("${SOURCE_COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap post create --post_type=page --post_status=publish --post_title="$marker" --post_content="$marker" --porcelain --allow-root)"
[[ "$source_post_id" =~ ^[1-9][0-9]*$ ]]
source_upload_sha="$("${SOURCE_COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap eval "\$uploads=wp_upload_dir(); \$path=\$uploads['basedir'].'/$upload_name'; file_put_contents(\$path,'$marker'); echo hash_file('sha256',\$path);" --allow-root | tail -n 1)"
[[ "$source_upload_sha" =~ ^[a-f0-9]{64}$ ]]

backup_output="$("$ROOT_DIR/bin/backup" --project "$source_project" "$backup")"
grep -Fq "Backup created: $backup" <<<"$backup_output"
grep -Fxq "source_project=$source_project" "$backup/manifest.txt"
grep -Fxq "source_wordpress_image=$source_image" "$backup/manifest.txt"
grep -Fxq "source_wordpress_image_revision=$(git -C "$ROOT_DIR/.." rev-parse HEAD)" "$backup/manifest.txt"
if ! backup_permissions="$(stat -c '%a' "$backup" 2>/dev/null)"; then
  backup_permissions="$(stat -f '%Lp' "$backup")"
fi
[[ "$backup_permissions" == 700 ]]

restore_output="$("$ROOT_DIR/bin/restore" --project "$restore_project" --env-file "$env_file" --confirm "$backup")"
grep -Fq "Restore completed: $restore_project" <<<"$restore_output"
grep -Fq "Restored image: $source_image" <<<"$restore_output"
elapsed="$(sed -n 's/^Elapsed seconds: //p' <<<"$restore_output")"
[[ "$elapsed" =~ ^[0-9]+$ && "$elapsed" -le 180 ]]

restored_wordpress_container="$("${RESTORE_COMPOSE[@]}" ps -q wordpress)"
[[ "$(docker inspect --format '{{.Image}}' "$restored_wordpress_container")" == "$source_image" ]]
restored_post_id="$("${RESTORE_COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap post get "$source_post_id" --field=ID --allow-root)"
restored_post_title="$("${RESTORE_COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap post get "$source_post_id" --field=post_title --allow-root)"
restored_post_content="$("${RESTORE_COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap post get "$source_post_id" --field=post_content --allow-root)"
[[ "$restored_post_id" == "$source_post_id" ]]
[[ "$restored_post_title" == "$marker" ]]
[[ "$restored_post_content" == "$marker" ]]
restored_upload_sha="$("${RESTORE_COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap eval "\$uploads=wp_upload_dir(); echo hash_file('sha256',\$uploads['basedir'].'/$upload_name');" --allow-root | tail -n 1)"
[[ "$restored_upload_sha" == "$source_upload_sha" ]]

echo "Full deployment-model database/uploads restore passed in ${elapsed}s for exact image $source_image."
