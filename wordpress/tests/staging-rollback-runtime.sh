#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
candidate_image="${GAMA_RELEASE_IMAGE_ID:-}"
candidate_commit="${GAMA_RELEASE_GIT_SHA:-}"
run_id="${GAMA_RELEASE_RUN_ID:-}"
run_attempt="${GAMA_RELEASE_RUN_ATTEMPT:-}"
receipt_dir="${GAMA_RELEASE_RECEIPT_DIR:-}"
receipt="$receipt_dir/release-regression.json"
development_platform="${GAMA_RELEASE_DEVELOPMENT_PLATFORM:-}"

if [[ ! "$candidate_image" =~ ^sha256:[a-f0-9]{64}$ ]]; then
  echo 'GAMA_RELEASE_IMAGE_ID must be an immutable local image ID.' >&2
  exit 64
fi
if [[ ! "$candidate_commit" =~ ^[a-f0-9]{40}$ ]]; then
  echo 'GAMA_RELEASE_GIT_SHA must be a full lowercase Git SHA.' >&2
  exit 64
fi
if [[ ! "$run_id" =~ ^[1-9][0-9]*$ || ! "$run_attempt" =~ ^[1-9][0-9]*$ ]]; then
  echo 'GAMA_RELEASE_RUN_ID and GAMA_RELEASE_RUN_ATTEMPT must be positive integers.' >&2
  exit 64
fi
if [[ "$receipt_dir" != /* || ! -d "$receipt_dir" || -L "$receipt_dir" ]]; then
  echo 'GAMA_RELEASE_RECEIPT_DIR must be an absolute regular directory.' >&2
  exit 64
fi
if [[ -e "$receipt" || -L "$receipt" ]]; then
  echo "Refusing to overwrite release receipt: $receipt" >&2
  exit 1
fi
if [[ -n "$development_platform" && "$development_platform" != 'linux/arm64' ]]; then
  echo 'GAMA_RELEASE_DEVELOPMENT_PLATFORM may only select linux/arm64.' >&2
  exit 64
fi

[[ "$(docker image inspect --format '{{.Id}}' "$candidate_image")" == "$candidate_image" ]]
image_platform="$(docker image inspect --format '{{.Os}}/{{.Architecture}}' "$candidate_image")"
[[ "$(docker image inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$candidate_image")" == "$candidate_commit" ]]
candidate_marker="$(docker image inspect --format '{{index .Config.Labels "com.gamasoftware.wordpress.release-marker"}}' "$candidate_image")"
if [[ -n "$development_platform" ]]; then
  if [[ "$candidate_marker" != 'development' ]]; then
    echo 'The native development override requires a development image marker.' >&2
    exit 64
  fi
  if [[ "$image_platform" != "$development_platform" ]]; then
    echo 'The development image platform does not match the native override.' >&2
    exit 64
  fi
  test_platform="$development_platform"
else
  if [[ "$image_platform" != 'linux/amd64' ]]; then
    echo 'Release rehearsals require linux/amd64 unless the native development override is explicit.' >&2
    exit 64
  fi
  if [[ "$candidate_marker" != 'release' && "$candidate_marker" != 'development' ]]; then
    echo 'Candidate image marker is invalid.' >&2
    exit 64
  fi
  test_platform='linux/amd64'
fi
[[ "$(git -C "$ROOT_DIR/.." rev-parse HEAD)" == "$candidate_commit" ]]

token="$(openssl rand -hex 8)"
project="gama-wp-staging-$token"
if docker ps -a --filter label=com.docker.compose.project="$project" --quiet | grep -q . \
  || docker volume ls --filter label=com.docker.compose.project="$project" --quiet | grep -q . \
  || docker network ls --filter label=com.docker.compose.project="$project" --quiet | grep -q .; then
  echo 'Generated staging namespace already exists; refusing ownership.' >&2
  exit 1
fi
fixture="$(mktemp -d "${TMPDIR:-/tmp}/gama-staging-$token.XXXXXX")"
env_file="$fixture/staging.env"
marker="GSWEB26-persistent-$(date +%s)-$$"
upload_name="$marker.txt"
base_image=''
base_image_acquired=0
project_acquired=1
base_ref="${GAMA_ROLLBACK_BASE_REF:-HEAD^}"
base_commit="$(git -C "$ROOT_DIR/.." rev-parse "$base_ref^{commit}")"
[[ "$base_commit" != "$candidate_commit" ]]

COMPOSE=(docker compose --project-name "$project" --env-file "$env_file" --file "$ROOT_DIR/deploy/compose.yaml" --file "$ROOT_DIR/deploy/staging.override.yaml")
cleanup() {
  local status=$?
  set +e
  if [[ "$status" -ne 0 && "$project_acquired" == 1 && -f "$env_file" ]]; then
    "${COMPOSE[@]}" ps >&2
    "${COMPOSE[@]}" logs --no-color wordpress db >&2
  fi
  if [[ "$project_acquired" == 1 && -f "$env_file" ]]; then "${COMPOSE[@]}" down --volumes --remove-orphans >/dev/null 2>&1; fi
  if [[ "$base_image_acquired" == 1 ]]; then docker image rm "$base_tag" >/dev/null 2>&1; fi
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

assert_persistent_page() {
  local actual_id actual_title actual_content actual_upload_sha
  actual_id="$("${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap post get "$persistent_post_id" --field=ID --allow-root)" || return 1
  actual_title="$("${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap post get "$persistent_post_id" --field=post_title --allow-root)" || return 1
  actual_content="$("${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap post get "$persistent_post_id" --field=post_content --allow-root)" || return 1
  actual_upload_sha="$("${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap eval "\$uploads=wp_upload_dir(); \$path=\$uploads['basedir'].'/$upload_name'; echo is_file(\$path) ? hash_file('sha256',\$path) : 'missing';" --allow-root)" || return 1
  [[ "$actual_id" == "$persistent_post_id" ]] || return 1
  [[ "$actual_title" == "$marker" ]] || return 1
  [[ "$actual_content" == "$marker" ]] || return 1
  [[ "$actual_upload_sha" == "$source_upload_sha" ]] || return 1
}

base_source="$fixture/base-source"
mkdir "$base_source"
git -C "$ROOT_DIR/.." archive "$base_commit" | tar -x -C "$base_source"
base_tag="gama-wordpress:rollback-base-$token"
docker build \
  --platform "$test_platform" \
  --file "$base_source/wordpress/runtime/Dockerfile" \
  --build-arg "GAMA_GIT_SHA=$base_commit" \
  --build-arg 'GAMA_RELEASE_MARKER=rollback-base' \
  --tag "$base_tag" \
  "$base_source"
base_image_acquired=1
base_image="$(docker image inspect --format '{{.Id}}' "$base_tag")"
[[ "$base_image" =~ ^sha256:[a-f0-9]{64}$ ]]
[[ "$(docker image inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$base_tag")" == "$base_commit" ]]
write_env "$base_image"
"$ROOT_DIR/bin/deploy-staging" --project "$project" --env-file "$env_file" --confirm

persistent_post_id="$("${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap post create --post_type=page --post_status=publish --post_title="$marker" --post_content="$marker" --porcelain --allow-root)"
[[ "$persistent_post_id" =~ ^[1-9][0-9]*$ ]]
source_upload_sha="$("${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap eval "\$uploads=wp_upload_dir(); \$path=\$uploads['basedir'].'/$upload_name'; file_put_contents(\$path,'$marker'); echo hash_file('sha256',\$path);" --allow-root | tail -n 1)"
[[ "$source_upload_sha" =~ ^[a-f0-9]{64}$ ]]

[[ "$candidate_image" =~ ^sha256:[a-f0-9]{64}$ && "$candidate_image" != "$base_image" ]]
[[ "$(docker image inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$candidate_image")" == "$candidate_commit" ]]
write_env "$candidate_image"
"$ROOT_DIR/bin/deploy-staging" --project "$project" --env-file "$env_file" --confirm

wordpress_container="$("${COMPOSE[@]}" ps -q wordpress)"
[[ "$(docker inspect --format '{{.Image}}' "$wordpress_container")" == "$candidate_image" ]]
assert_persistent_page
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
assert_persistent_page
"${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap eval "\$uploads=wp_upload_dir(); exit(hash_file('sha256',\$uploads['basedir'].'/$upload_name')==='$source_upload_sha' ? 0 : 1);" --allow-root

# These are deliberately created fixture records in the new owned namespace.
for loss in title content deleted-post media deleted-media; do
  case "$loss" in
    title) "${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap post update "$persistent_post_id" --post_title=corrupted-owned-fixture --allow-root >/dev/null ;;
    content) "${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap post update "$persistent_post_id" --post_content=corrupted-owned-fixture --allow-root >/dev/null ;;
    deleted-post) "${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap post delete "$persistent_post_id" --force --allow-root >/dev/null ;;
    media) "${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap eval "\$uploads=wp_upload_dir(); if(file_put_contents(\$uploads['basedir'].'/$upload_name','corrupted-owned-fixture')===false){exit(1);}" --allow-root ;;
    deleted-media) "${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap eval "\$uploads=wp_upload_dir(); if(!unlink(\$uploads['basedir'].'/$upload_name')){exit(1);}" --allow-root ;;
  esac
  if assert_persistent_page; then
    echo "Data-loss verifier incorrectly accepted $loss; receipt withheld." >&2
    exit 1
  fi
  if [[ "$loss" == deleted-post ]]; then
    restored_id="$("${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap post create --import_id="$persistent_post_id" --post_type=page --post_status=publish --post_title="$marker" --post_content="$marker" --porcelain --allow-root)"
    [[ "$restored_id" == "$persistent_post_id" ]]
  else
    "${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap post update "$persistent_post_id" --post_title="$marker" --post_content="$marker" --allow-root >/dev/null
  fi
  "${COMPOSE[@]}" run --rm --no-deps --entrypoint wp bootstrap eval "\$uploads=wp_upload_dir(); if(file_put_contents(\$uploads['basedir'].'/$upload_name','$marker')===false){exit(1);}" --allow-root
  assert_persistent_page
  echo "Owned data-loss negative refused: $loss; exact fixture restored."
done

umask 077
set -C
printf '%s\n' \
  '{' \
  '  "schema_version": 1,' \
  '  "name": "release-regression",' \
  '  "status": "passed",' \
  "  \"image_id\": \"$candidate_image\"," \
  "  \"git_sha\": \"$candidate_commit\"," \
  "  \"run_id\": $run_id," \
  "  \"run_attempt\": $run_attempt" \
  '}' \
  >"$receipt"
set +C

echo "Staging used immutable images, isolated mail, persistent data and a tested code-only rollback ($candidate_image -> $base_image)."
