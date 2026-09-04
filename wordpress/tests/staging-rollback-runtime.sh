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
base_ref="${GAMA_ROLLBACK_BASE_REF:-HEAD^}"
base_commit="$(git -C "$ROOT_DIR/.." rev-parse "$base_ref^{commit}")"
candidate_commit="$(git -C "$ROOT_DIR/.." rev-parse HEAD)"
[[ "$base_commit" != "$candidate_commit" ]]

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
    'WORDPRESS_HTTP_PORT=' \
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

base_source="$fixture/base-source"
mkdir "$base_source"
git -C "$ROOT_DIR/.." archive "$base_commit" | tar -x -C "$base_source"
base_tag="gama-wordpress:rollback-base-$base_commit"
DOCKER_CONFIG="${DOCKER_CONFIG:-/private/tmp/codex-wp-docker-config}" docker build \
  --file "$base_source/wordpress/runtime/Dockerfile" \
  --build-arg "GAMA_GIT_SHA=$base_commit" \
  --build-arg 'GAMA_RELEASE_MARKER=rollback-base' \
  --tag "$base_tag" \
  "$base_source"
base_image="$(docker image inspect --format '{{.Id}}' "$base_tag")"
[[ "$base_image" =~ ^sha256:[a-f0-9]{64}$ ]]
[[ "$(docker image inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$base_tag")" == "$base_commit" ]]
write_env "$base_image"
"$ROOT_DIR/bin/deploy-staging" --project "$project" --env-file "$env_file" --confirm

"${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap post create --post_type=page --post_status=publish --post_title="$marker" --post_content="$marker" --porcelain --allow-root >/dev/null
source_upload_sha="$("${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap eval "\$uploads=wp_upload_dir(); \$path=\$uploads['basedir'].'/$upload_name'; file_put_contents(\$path,'$marker'); echo hash_file('sha256',\$path);" --allow-root | tail -n 1)"

candidate_output="$("$ROOT_DIR/bin/build-release" --test-dirty candidate)"
candidate_image="$(sed -n 's/^Image ID: //p' <<<"$candidate_output")"
[[ "$candidate_image" =~ ^sha256:[a-f0-9]{64}$ && "$candidate_image" != "$base_image" ]]
[[ "$(docker image inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$candidate_image")" == "$candidate_commit" ]]
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
GAMA_STAGING_PROJECT="$project" \
  GAMA_RELEASE_ARTIFACT_ROOT="${GAMA_RELEASE_ARTIFACT_ROOT:-$fixture/evidence}" \
  "$ROOT_DIR/tests/release-regression-runtime.sh"

sample_page_id="$("${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap post list --post_type=page --name=sample-page --field=ID --allow-root | tail -n 1)"
if [[ ! "$sample_page_id" =~ ^[1-9][0-9]*$ ]]; then
  sample_page_id="$("${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap post create --post_type=page --post_title='Sample Page' --post_name=sample-page --post_status=publish --porcelain --allow-root | tail -n 1)"
else
  "${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap post update "$sample_page_id" --post_status=publish --allow-root >/dev/null
fi
[[ "$sample_page_id" =~ ^[1-9][0-9]*$ ]]
navigation_editor_id="$("${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap user create theme-navigation-editor theme-navigation-editor@example.test --role=editor --user_pass=navigation-editor-test-only --porcelain --allow-root | tail -n 1)"
style_editor_id="$("${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap user create style-editor style-editor@example.test --role=editor --user_pass=style-editor-test-only --porcelain --allow-root | tail -n 1)"
[[ "$navigation_editor_id" =~ ^[1-9][0-9]*$ && "$style_editor_id" =~ ^[1-9][0-9]*$ ]]
"${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap post create --post_type=page --post_title='Editor preset fixture' --post_name=editor-preset-fixture --post_status=publish --post_author="$style_editor_id" --post_content='<!-- wp:paragraph --><p>Editor preset fixture</p><!-- /wp:paragraph -->' --allow-root >/dev/null
"${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap post create --post_type=post --post_title='Second fixture article' --post_name=second-fixture-article --post_status=publish --post_date='2026-09-01 12:00:00' --post_content='Staging migration rehearsal article.' --allow-root >/dev/null
"${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap post create --post_type=post --post_title='Focus neighbour' --post_name=focus-neighbour --post_status=publish --post_date='2026-09-02 12:00:00' --allow-root >/dev/null
"${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap option update posts_per_page 1 --allow-root >/dev/null
GAMA_STAGING_PROJECT="$project" \
  GAMA_RELEASE_ARTIFACT_ROOT="${GAMA_RELEASE_ARTIFACT_ROOT:-$fixture/evidence}" \
  "$ROOT_DIR/tests/release-acceptance-runtime.sh"

write_env "$base_image"
"$ROOT_DIR/bin/rollback-staging" --project "$project" --env-file "$env_file" --confirm
wordpress_container="$("${COMPOSE[@]}" ps -q wordpress)"
[[ "$(docker inspect --format '{{.Image}}' "$wordpress_container")" == "$base_image" ]]
"${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap post list --post_type=page --search="$marker" --field=ID --allow-root | grep -Eq '^[1-9][0-9]*$'
"${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap eval "\$uploads=wp_upload_dir(); exit(hash_file('sha256',\$uploads['basedir'].'/$upload_name')==='$source_upload_sha' ? 0 : 1);" --allow-root

echo "Staging used immutable images, isolated mail, persistent data and a tested code-only rollback ($candidate_image -> $base_image)."
