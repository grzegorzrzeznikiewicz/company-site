#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
candidate_image="${GAMA_RELEASE_IMAGE_ID:-}"
candidate_revision="${GAMA_RELEASE_GIT_SHA:-}"
run_id="${GAMA_RELEASE_RUN_ID:-}"
run_attempt="${GAMA_RELEASE_RUN_ATTEMPT:-}"
receipt_dir="${GAMA_RELEASE_RECEIPT_DIR:-}"
receipt="$receipt_dir/production-runtime.json"
development_platform="${GAMA_RELEASE_DEVELOPMENT_PLATFORM:-}"

if [[ ! "$candidate_image" =~ ^sha256:[a-f0-9]{64}$ ]]; then
  echo 'GAMA_RELEASE_IMAGE_ID must be an immutable local image ID.' >&2
  exit 64
fi
if [[ ! "$candidate_revision" =~ ^[a-f0-9]{40}$ ]]; then
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
  echo "Refusing to overwrite production receipt: $receipt" >&2
  exit 1
fi
if [[ -n "$development_platform" && "$development_platform" != 'linux/arm64' ]]; then
  echo 'GAMA_RELEASE_DEVELOPMENT_PLATFORM may only select linux/arm64.' >&2
  exit 64
fi

[[ "$(docker image inspect --format '{{.Id}}' "$candidate_image")" == "$candidate_image" ]]
image_platform="$(docker image inspect --format '{{.Os}}/{{.Architecture}}' "$candidate_image")"
[[ "$(docker image inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$candidate_image")" == "$candidate_revision" ]]
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
[[ "$(git -C "$ROOT_DIR/.." rev-parse HEAD)" == "$candidate_revision" ]]

token="$(openssl rand -hex 8)"
candidate_project="gama-wp-production-candidate-test-$token"
smtp_container="gama-production-smtp-test-$token"
if docker ps -a --filter label=com.docker.compose.project="$candidate_project" --quiet | grep -q . \
  || docker volume ls --filter label=com.docker.compose.project="$candidate_project" --quiet | grep -q . \
  || docker network ls --filter label=com.docker.compose.project="$candidate_project" --quiet | grep -q . \
  || docker ps -a --filter name="^/${smtp_container}$" --quiet | grep -q .; then
  echo 'Generated production rehearsal namespace already exists; refusing ownership.' >&2
  exit 1
fi

fixture_dir="$(mktemp -d "${TMPDIR:-/tmp}/gama-production-runtime-$token.XXXXXX")"
env_file="$fixture_dir/production.env"
base_source_image="gama-wordpress:production-base-test-$token"
base_image=''
base_image_acquired=0
project_acquired=1
smtp_acquired=0
base_ref="${GAMA_ROLLBACK_BASE_REF:-HEAD^}"
base_revision="$(git -C "$ROOT_DIR/.." rev-parse "$base_ref^{commit}")"
[[ "$base_revision" != "$candidate_revision" ]]
printf '%s\n' "$token" >"$fixture_dir/.gama-production-rehearsal-owner"
chmod 0600 "$fixture_dir/.gama-production-rehearsal-owner"

COMPOSE=(docker compose --project-name "$candidate_project" --env-file "$env_file" --file "$ROOT_DIR/deploy/compose.yaml" --file "$ROOT_DIR/tests/production-rehearsal.override.yaml")
cleanup() {
  local status=$?
  set +e
  if [[ "$status" -ne 0 && "$project_acquired" == 1 && -f "$env_file" ]]; then
    GAMA_PRODUCTION_REHEARSAL_FIXTURE="$fixture_dir" WORDPRESS_IMAGE="$candidate_image" WORDPRESS_HTTP_PORT='' \
      "${COMPOSE[@]}" ps >&2
    GAMA_PRODUCTION_REHEARSAL_FIXTURE="$fixture_dir" WORDPRESS_IMAGE="$candidate_image" WORDPRESS_HTTP_PORT='' \
      "${COMPOSE[@]}" logs --no-color wordpress db >&2
  fi
  if [[ "$smtp_acquired" == 1 && "$(docker inspect --format '{{index .Config.Labels "gama.rehearsal.owner"}}' "$smtp_container" 2>/dev/null)" == "$token" ]]; then
    docker rm -f "$smtp_container" >/dev/null 2>&1
  fi
  if [[ "$project_acquired" == 1 && -f "$fixture_dir/.gama-production-rehearsal-owner" && "$(cat "$fixture_dir/.gama-production-rehearsal-owner")" == "$token" ]]; then
    GAMA_PRODUCTION_REHEARSAL_FIXTURE="$fixture_dir" WORDPRESS_IMAGE="$candidate_image" WORDPRESS_HTTP_PORT='' \
      "${COMPOSE[@]}" down --volumes --remove-orphans >/dev/null 2>&1
  fi
  if [[ "$base_image_acquired" == 1 ]]; then docker image rm "$base_source_image" >/dev/null 2>&1; fi
  find "$fixture_dir" -type f -delete 2>/dev/null
  find "$fixture_dir" -depth -type d -exec rmdir {} \; 2>/dev/null
  trap - EXIT
  exit "$status"
}
trap cleanup EXIT

printf '%s\n' \
  '[req]' \
  'distinguished_name = subject' \
  'prompt = no' \
  'x509_extensions = ca_extensions' \
  '[subject]' \
  'CN = Gama production runtime CA' \
  '[ca_extensions]' \
  'basicConstraints = critical,CA:true' \
  'keyUsage = critical,keyCertSign,cRLSign' \
  >"$fixture_dir/ca.cnf"
printf '%s\n' \
  '[req]' \
  'distinguished_name = subject' \
  'prompt = no' \
  '[subject]' \
  'CN = smtp.fixture.test' \
  '[extensions]' \
  'subjectAltName = DNS:smtp.fixture.test' \
  'extendedKeyUsage = serverAuth' \
  >"$fixture_dir/certificate.cnf"
openssl req -x509 -newkey rsa:2048 -nodes -days 1 -config "$fixture_dir/ca.cnf" \
  -keyout "$fixture_dir/ca.key" -out "$fixture_dir/ca.crt" >/dev/null 2>&1
openssl req -newkey rsa:2048 -nodes -config "$fixture_dir/certificate.cnf" \
  -keyout "$fixture_dir/smtp.key" -out "$fixture_dir/smtp.csr" >/dev/null 2>&1
openssl x509 -req -days 1 -sha256 -in "$fixture_dir/smtp.csr" \
  -CA "$fixture_dir/ca.crt" -CAkey "$fixture_dir/ca.key" -CAcreateserial \
  -extfile "$fixture_dir/certificate.cnf" -extensions extensions \
  -out "$fixture_dir/smtp.crt" >/dev/null 2>&1
printf '%s\n' 'openssl.cafile=/run/gama-test-ca/ca.crt' >"$fixture_dir/openssl-ca.ini"
chmod 0600 "$fixture_dir/ca.crt" "$fixture_dir/openssl-ca.ini"

base_source="$fixture_dir/base-source"
mkdir "$base_source"
git -C "$ROOT_DIR/.." archive "$base_revision" | tar -x -C "$base_source"
docker build --platform "$test_platform" --file "$base_source/wordpress/runtime/Dockerfile" \
  --build-arg GAMA_GIT_SHA="$base_revision" --build-arg GAMA_RELEASE_MARKER=rollback-base \
  --tag "$base_source_image" "$base_source" >/dev/null
base_image_acquired=1
base_image="$(docker image inspect --format '{{.Id}}' "$base_source_image")"
[[ "$base_image" =~ ^sha256:[a-f0-9]{64}$ && "$base_image" != "$candidate_image" ]]
export WORDPRESS_IMAGE="$base_image"
export WORDPRESS_HTTP_PORT=''
export GAMA_PRODUCTION_REHEARSAL_FIXTURE="$fixture_dir"

printf '%s\n' \
  'WP_DB_NAME=wordpress' \
  'WP_DB_USER=wordpress' \
  'WP_DB_PASSWORD=runtime-password' \
  'WP_DB_ROOT_PASSWORD=runtime-root-password' \
  'WP_HOME=https://gama-software.com' \
  'WP_SITE_TITLE=Gama Software' \
  'WP_ADMIN_USER=runtime-admin' \
  'WP_ADMIN_PASSWORD=runtime-admin-password' \
  'WP_ADMIN_EMAIL=admin@example.test' \
  'WP_ENVIRONMENT_TYPE=production' \
  'GAMA_CONTACT_RECIPIENT=contact@example.test' \
  'GAMA_CONTACT_SENDER=no-reply@example.test' \
  'GAMA_MAIL_SINK_HOST=' \
  'GAMA_SMTP_HOST=smtp.fixture.test' \
  'GAMA_SMTP_PORT=1025' \
  'GAMA_SMTP_USERNAME=runtime-user' \
  'GAMA_SMTP_PASSWORD=runtime-password' \
  'GAMA_SMTP_ENCRYPTION=tls' \
  >"$env_file"
chmod 0600 "$env_file"

"$ROOT_DIR/bin/deploy-production" \
  --project "$candidate_project" --env-file "$env_file" --image "$base_image" \
  --http-port 0 --confirm-image "$base_image" --rehearsal-fixture "$fixture_dir" --bootstrap >/dev/null
wordpress_container="$("${COMPOSE[@]}" ps -q wordpress)"
[[ "$(docker inspect --format '{{.Image}}' "$wordpress_container")" == "$base_image" ]]

docker run --detach --name "$smtp_container" \
  --label "gama.rehearsal.owner=$token" \
  --network "${candidate_project}_default" --network-alias smtp.fixture.test \
  --publish 127.0.0.1::8025 \
  --volume "$fixture_dir:/certs:ro" \
  axllent/mailpit:v1.30.0@sha256:0059ef81e492a7192af3816281eed6859eb078bd7bdc58b76757c13e10e53a7d \
  --smtp-tls-cert /certs/smtp.crt --smtp-tls-key /certs/smtp.key \
  --smtp-require-starttls --smtp-auth-accept-any >/dev/null
smtp_acquired=1
smtp_http_port="$(docker port "$smtp_container" 8025/tcp | sed -n 's/^127\.0\.0\.1://p')"
for _ in $(seq 1 30); do
  if curl --fail --silent "http://127.0.0.1:$smtp_http_port/api/v1/info" >/dev/null 2>&1; then break; fi
  sleep 1
done
curl --fail --silent "http://127.0.0.1:$smtp_http_port/api/v1/info" >/dev/null

marker="GSWEB29-production-$token"
persistent_post_id="$(docker exec "$wordpress_container" wp --allow-root --url=https://gama-software.com post create \
  --post_type=page --post_status=publish --post_title="$marker" --post_content="$marker" --porcelain)"
[[ "$persistent_post_id" =~ ^[1-9][0-9]*$ ]]
source_upload_sha="$(docker exec "$wordpress_container" wp --allow-root --url=https://gama-software.com eval \
  "\$upload=wp_upload_bits('production-runtime-$token.txt',null,'$marker'); if(!empty(\$upload['error'])){exit(1);} update_option('gama_production_runtime_upload',\$upload['file']); echo hash_file('sha256',\$upload['file']);" | tail -n 1)"
[[ "$source_upload_sha" =~ ^[a-f0-9]{64}$ ]]

assert_persistence() {
  local container="$1" actual_id actual_title actual_content actual_upload_sha
  actual_id="$(docker exec "$container" wp --allow-root --url=https://gama-software.com post get "$persistent_post_id" --field=ID)" || return 1
  actual_title="$(docker exec "$container" wp --allow-root --url=https://gama-software.com post get "$persistent_post_id" --field=post_title)" || return 1
  actual_content="$(docker exec "$container" wp --allow-root --url=https://gama-software.com post get "$persistent_post_id" --field=post_content)" || return 1
  actual_upload_sha="$(docker exec "$container" wp --allow-root --url=https://gama-software.com eval '$path=get_option("gama_production_runtime_upload"); echo is_file($path) ? hash_file("sha256",$path) : "missing";')" || return 1
  [[ "$actual_id" == "$persistent_post_id" ]] || return 1
  [[ "$actual_title" == "$marker" ]] || return 1
  [[ "$actual_content" == "$marker" ]] || return 1
  [[ "$actual_upload_sha" == "$source_upload_sha" ]] || return 1
  echo "Owned persistence verified: post_id=$actual_id title=$actual_title content=$actual_content upload_sha256=$actual_upload_sha"
}

"$ROOT_DIR/bin/deploy-production" \
  --project "$candidate_project" --env-file "$env_file" --image "$candidate_image" \
  --http-port 0 --confirm-image "$candidate_image" --rehearsal-fixture "$fixture_dir" >/dev/null
export WORDPRESS_IMAGE="$candidate_image"
wordpress_container="$("${COMPOSE[@]}" ps -q wordpress)"
[[ "$(docker inspect --format '{{.Image}}' "$wordpress_container")" == "$candidate_image" ]]
assert_persistence "$wordpress_container"
docker exec "$wordpress_container" wp --allow-root --url=https://gama-software.com eval \
  "exit(wp_mail('controlled@example.test','GSWEB-29 SMTP runtime','$marker') ? 0 : 1);"
for _ in $(seq 1 30); do
  message_count="$(curl --fail --silent "http://127.0.0.1:$smtp_http_port/api/v1/messages" | sed -n 's/.*"total":[[:space:]]*\([0-9][0-9]*\).*/\1/p')"
  if [[ "${message_count:-0}" -ge 1 ]]; then break; fi
  sleep 1
done
[[ "${message_count:-0}" -ge 1 ]]
docker exec --env GAMA_SMTP_HOST='bad host' "$wordpress_container" \
  wp --allow-root --url=https://gama-software.com eval 'exit(wp_mail("blocked@example.test", "must fail closed", "invalid SMTP") ? 1 : 0);'

# Deliberately break current PHP in this owned disposable namespace. Recovery
# must copy previous code without running current PHP or requiring a new backup.
docker exec "$wordpress_container" sh -ec 'printf "<?php throw new RuntimeException(\"recovery fixture\");" > /var/www/html/wp-includes/version.php'
if docker exec "$wordpress_container" wp --allow-root core is-installed >/dev/null 2>&1; then
  echo 'Broken-PHP recovery fixture unexpectedly remained executable.' >&2
  exit 1
fi

"$ROOT_DIR/bin/rollback-production" \
  --project "$candidate_project" --env-file "$env_file" --image "$base_image" \
  --http-port 0 --confirm-image "$base_image" --rehearsal-fixture "$fixture_dir" >/dev/null
export WORDPRESS_IMAGE="$base_image"
wordpress_container="$("${COMPOSE[@]}" ps -q wordpress)"
[[ "$(docker inspect --format '{{.Image}}' "$wordpress_container")" == "$base_image" ]]
assert_persistence "$wordpress_container"

# Deliberately damage only the post and upload created in this owned namespace.
# Explicit assertion returns above remain effective inside this Bash conditional.
for loss in title content deleted-post media deleted-media; do
  case "$loss" in
    title) docker exec "$wordpress_container" wp --allow-root post update "$persistent_post_id" --post_title=corrupted-owned-fixture >/dev/null ;;
    content) docker exec "$wordpress_container" wp --allow-root post update "$persistent_post_id" --post_content=corrupted-owned-fixture >/dev/null ;;
    deleted-post) docker exec "$wordpress_container" wp --allow-root post delete "$persistent_post_id" --force >/dev/null ;;
    media) docker exec "$wordpress_container" wp --allow-root eval '$path=get_option("gama_production_runtime_upload"); if(file_put_contents($path,"corrupted-owned-fixture")===false){exit(1);}' ;;
    deleted-media) docker exec "$wordpress_container" wp --allow-root eval '$path=get_option("gama_production_runtime_upload"); if(!unlink($path)){exit(1);}' ;;
  esac
  if assert_persistence "$wordpress_container"; then
    echo "Data-loss verifier incorrectly accepted $loss; receipt withheld." >&2
    exit 1
  fi
  if [[ "$loss" == deleted-post ]]; then
    restored_id="$(docker exec "$wordpress_container" wp --allow-root post create --import_id="$persistent_post_id" --post_type=page --post_status=publish --post_title="$marker" --post_content="$marker" --porcelain)"
    [[ "$restored_id" == "$persistent_post_id" ]]
  else
    docker exec "$wordpress_container" wp --allow-root post update "$persistent_post_id" --post_title="$marker" --post_content="$marker" >/dev/null
  fi
  docker exec "$wordpress_container" wp --allow-root eval "\$path=get_option('gama_production_runtime_upload'); if(file_put_contents(\$path,'$marker')===false){exit(1);}"
  assert_persistence "$wordpress_container"
  echo "Owned data-loss negative refused: $loss; exact fixture restored."
done

umask 077
set -C
printf '%s\n' \
  '{' \
  '  "schema_version": 1,' \
  '  "name": "production-runtime",' \
  '  "status": "passed",' \
  "  \"image_id\": \"$candidate_image\"," \
  "  \"git_sha\": \"$candidate_revision\"," \
  "  \"run_id\": $run_id," \
  "  \"run_attempt\": $run_attempt" \
  '}' \
  >"$receipt"
set +C

echo "Isolated production candidate, encrypted SMTP, exact persistence and code rollback passed ($candidate_image)."
