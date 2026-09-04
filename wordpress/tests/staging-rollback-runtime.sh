#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
project="gama-wp-staging-$RANDOM-$$"
fixture="$(mktemp -d "${TMPDIR:-/tmp}/gama-staging.XXXXXX")"
env_file="$fixture/staging.env"
marker="GSWEB26-persistent-$(date +%s)-$$"
upload_name="$marker.txt"
base_image=''
candidate_image=''

COMPOSE=(docker compose --project-name "$project" --env-file "$env_file" --file "$ROOT_DIR/deploy/compose.yaml" --file "$ROOT_DIR/deploy/staging.override.yaml")
cleanup() {
  local status=$?
  set +e
  if [[ -f "$env_file" ]]; then "${COMPOSE[@]}" down --volumes --remove-orphans >/dev/null 2>&1; fi
  find "$fixture" -type f -delete 2>/dev/null
  find "$fixture" -depth -type d -exec rmdir {} \; 2>/dev/null
  set -e
  trap - EXIT
  exit "$status"
}
trap cleanup EXIT

write_env() {
  local image="$1"
  printf '%s\n' \
    "WORDPRESS_IMAGE=$image" \
    'WORDPRESS_HTTP_PORT=18090' \
    'WP_DB_NAME=gama_staging' \
    'WP_DB_USER=gama_staging' \
    'WP_DB_PASSWORD=staging-database-test-only' \
    'WP_DB_ROOT_PASSWORD=staging-root-test-only' \
    'WP_HOME=http://wordpress' \
    'WP_SITE_TITLE=Gama Software Staging' \
    'WP_ADMIN_USER=admin' \
    'WP_ADMIN_PASSWORD=staging-admin-test-only' \
    'WP_ADMIN_EMAIL=admin@example.test' \
    'WP_ENVIRONMENT_TYPE=staging' \
    'GAMA_CONTACT_RECIPIENT=sink@example.test' \
    'GAMA_CONTACT_SENDER=no-reply@example.test' \
    'GAMA_MAIL_SINK_HOST=mailpit' \
    'GAMA_MAIL_SINK_PORT=1025' \
    >"$env_file"
  chmod 0600 "$env_file"
}

base_output="$("$ROOT_DIR/bin/build-release" --test-dirty rollback-base)"
base_image="$(sed -n 's/^Image ID: //p' <<<"$base_output")"
[[ "$base_image" =~ ^sha256:[a-f0-9]{64}$ ]]
write_env "$base_image"
"$ROOT_DIR/bin/deploy-staging" --project "$project" --env-file "$env_file" --confirm

"${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap post create --post_type=page --post_status=publish --post_title="$marker" --post_content="$marker" --porcelain --allow-root >/dev/null
source_upload_sha="$("${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap eval "\$uploads=wp_upload_dir(); \$path=\$uploads['basedir'].'/$upload_name'; file_put_contents(\$path,'$marker'); echo hash_file('sha256',\$path);" --allow-root | tail -n 1)"

candidate_output="$("$ROOT_DIR/bin/build-release" --test-dirty candidate)"
candidate_image="$(sed -n 's/^Image ID: //p' <<<"$candidate_output")"
[[ "$candidate_image" =~ ^sha256:[a-f0-9]{64}$ && "$candidate_image" != "$base_image" ]]
write_env "$candidate_image"
"$ROOT_DIR/bin/deploy-staging" --project "$project" --env-file "$env_file" --confirm

wordpress_container="$("${COMPOSE[@]}" ps -q wordpress)"
[[ "$(docker inspect --format '{{.Image}}' "$wordpress_container")" == "$candidate_image" ]]
"${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap post list --post_type=page --search="$marker" --field=ID --allow-root | grep -Eq '^[1-9][0-9]*$'
"${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap eval "\$uploads=wp_upload_dir(); exit(hash_file('sha256',\$uploads['basedir'].'/$upload_name')==='$source_upload_sha' ? 0 : 1);" --allow-root
"${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap plugin is-active gama-local-mailpit --allow-root
docker exec "$wordpress_container" php -r '$html=file_get_contents("http://127.0.0.1/"); exit(str_contains($html,"noindex") ? 0 : 1);'
"${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap eval "exit(wp_mail('sink@example.test','GSWEB26 staging sink','$marker') ? 0 : 1);" --allow-root
mailpit_container="$("${COMPOSE[@]}" ps -q mailpit)"
docker exec "$mailpit_container" wget --quiet --output-document=- http://127.0.0.1:8025/api/v1/messages | grep -Fq "$marker"

write_env "$base_image"
"$ROOT_DIR/bin/rollback-staging" --project "$project" --env-file "$env_file" --confirm
wordpress_container="$("${COMPOSE[@]}" ps -q wordpress)"
[[ "$(docker inspect --format '{{.Image}}' "$wordpress_container")" == "$base_image" ]]
"${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap post list --post_type=page --search="$marker" --field=ID --allow-root | grep -Eq '^[1-9][0-9]*$'
"${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap eval "\$uploads=wp_upload_dir(); exit(hash_file('sha256',\$uploads['basedir'].'/$upload_name')==='$source_upload_sha' ? 0 : 1);" --allow-root

echo "Staging used immutable images, isolated mail, persistent data and a tested code-only rollback ($candidate_image -> $base_image)."
