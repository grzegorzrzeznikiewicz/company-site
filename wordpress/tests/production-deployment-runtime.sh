#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/deploy/compose.yaml"
stable_project='gama-wp-production'
candidate_project="gama-wp-production-candidate-test-$$"
marker="$(date +%s)-$$"
smtp_container="gama-production-smtp-$marker"
fixture_dir="$(mktemp -d "${TMPDIR:-/tmp}/gama-production-runtime.XXXXXX")"
env_file="$fixture_dir/production.env"
base_source_image="gama-wordpress:test-production-base-$marker"
candidate_source_image="gama-wordpress:test-production-candidate-$marker"
base_image="gama-wordpress:test-production-base-trusted-$marker"
candidate_image="gama-wordpress:test-production-candidate-trusted-$marker"
base_revision="$(printf 'a%.0s' {1..40})"
candidate_revision="$(printf 'b%.0s' {1..40})"

cleanup() {
  set +e
  docker rm -f "$smtp_container" >/dev/null 2>&1
  for project in "$candidate_project" "$stable_project"; do
    WORDPRESS_IMAGE="$candidate_image" WORDPRESS_HTTP_PORT='' docker compose \
      --project-name "$project" --env-file "$env_file" --file "$COMPOSE_FILE" \
      down --volumes --remove-orphans >/dev/null 2>&1
  done
  docker image rm "$base_image" "$candidate_image" "$base_source_image" "$candidate_source_image" >/dev/null 2>&1
  find "$fixture_dir" -mindepth 1 -delete 2>/dev/null
  rmdir "$fixture_dir" 2>/dev/null
}
trap cleanup EXIT

if docker ps -a --filter label=com.docker.compose.project="$stable_project" --quiet | grep -q . \
  || docker volume ls --filter label=com.docker.compose.project="$stable_project" --quiet | grep -q . \
  || docker network ls --filter label=com.docker.compose.project="$stable_project" --quiet | grep -q .; then
  echo 'Refusing to touch an existing gama-wp-production namespace.' >&2
  exit 1
fi

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
openssl req -x509 -newkey rsa:2048 -nodes -days 1 \
  -subj '/CN=Gama production runtime CA' \
  -keyout "$fixture_dir/ca.key" -out "$fixture_dir/ca.crt" >/dev/null 2>&1
openssl req -newkey rsa:2048 -nodes -config "$fixture_dir/certificate.cnf" \
  -keyout "$fixture_dir/smtp.key" -out "$fixture_dir/smtp.csr" >/dev/null 2>&1
openssl x509 -req -days 1 -sha256 -in "$fixture_dir/smtp.csr" \
  -CA "$fixture_dir/ca.crt" -CAkey "$fixture_dir/ca.key" -CAcreateserial \
  -extfile "$fixture_dir/certificate.cnf" -extensions extensions \
  -out "$fixture_dir/smtp.crt" >/dev/null 2>&1

docker build --quiet --file "$ROOT_DIR/runtime/Dockerfile" \
  --build-arg GAMA_GIT_SHA="$base_revision" --build-arg GAMA_RELEASE_MARKER=production-base \
  --tag "$base_source_image" "$ROOT_DIR/.." >/dev/null
docker build --quiet --file "$ROOT_DIR/runtime/Dockerfile" \
  --build-arg GAMA_GIT_SHA="$candidate_revision" --build-arg GAMA_RELEASE_MARKER=production-candidate \
  --tag "$candidate_source_image" "$ROOT_DIR/.." >/dev/null
printf '%s\n' \
  'ARG BASE_IMAGE' \
  'FROM ${BASE_IMAGE}' \
  'COPY ca.crt /usr/local/share/ca-certificates/gama-production-runtime-ca.crt' \
  'RUN update-ca-certificates' \
  >"$fixture_dir/Dockerfile"
docker build --quiet --build-arg BASE_IMAGE="$base_source_image" --tag "$base_image" "$fixture_dir" >/dev/null
docker build --quiet --build-arg BASE_IMAGE="$candidate_source_image" --tag "$candidate_image" "$fixture_dir" >/dev/null
base_image_id="$(docker image inspect --format '{{.Id}}' "$base_image")"
candidate_image_id="$(docker image inspect --format '{{.Id}}' "$candidate_image")"

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

"$ROOT_DIR/bin/deploy-production" \
  --project "$candidate_project" --env-file "$env_file" \
  --image "$candidate_image_id" --http-port 0 --confirm-image "$candidate_image_id" >/dev/null
candidate_container="$(docker ps --filter label=com.docker.compose.project="$candidate_project" --filter label=com.docker.compose.service=wordpress --format '{{.ID}}')"
[[ "$(docker inspect --format '{{.State.Health.Status}}' "$candidate_container")" == healthy ]]
[[ "$(docker inspect --format '{{.Config.Image}}' "$candidate_container")" == "$candidate_image_id" ]]

"$ROOT_DIR/bin/deploy-production" \
  --project "$stable_project" --env-file "$env_file" \
  --image "$base_image_id" --http-port 8080 --confirm-image "$base_image_id" >/dev/null
stable_container="$(docker ps --filter label=com.docker.compose.project="$stable_project" --filter label=com.docker.compose.service=wordpress --format '{{.ID}}')"
[[ "$(docker inspect --format '{{.Config.Image}}' "$stable_container")" == "$base_image_id" ]]

docker run --detach --name "$smtp_container" \
  --network "${stable_project}_default" --network-alias smtp.fixture.test \
  --publish 127.0.0.1::8025 \
  --volume "$fixture_dir:/certs:ro" \
  axllent/mailpit:v1.30.0@sha256:0059ef81e492a7192af3816281eed6859eb078bd7bdc58b76757c13e10e53a7d \
  --smtp-tls-cert /certs/smtp.crt --smtp-tls-key /certs/smtp.key \
  --smtp-require-starttls --smtp-auth-accept-any >/dev/null
smtp_http_port="$(docker port "$smtp_container" 8025/tcp | sed -n 's/^127\.0\.0\.1://p')"
for _ in $(seq 1 30); do
  if curl --fail --silent "http://127.0.0.1:$smtp_http_port/api/v1/info" >/dev/null 2>&1; then break; fi
  sleep 1
done
curl --fail --silent "http://127.0.0.1:$smtp_http_port/api/v1/info" >/dev/null

docker exec "$stable_container" wp --allow-root --url=https://gama-software.com eval '
  update_option("gama_production_runtime_identity", "persistent");
  $upload = wp_upload_bits("production-runtime.txt", null, "persistent-media");
  if (!empty($upload["error"])) { exit(1); }
  update_option("gama_production_runtime_upload", $upload["file"]);
  if (!wp_mail("controlled@example.test", "GSWEB-29 SMTP runtime", "encrypted SMTP fixture")) { exit(1); }
'
for _ in $(seq 1 30); do
  message_count="$(curl --fail --silent "http://127.0.0.1:$smtp_http_port/api/v1/messages" | sed -n 's/.*"total":[[:space:]]*\([0-9][0-9]*\).*/\1/p')"
  if [[ "${message_count:-0}" -ge 1 ]]; then break; fi
  sleep 1
done
[[ "${message_count:-0}" -ge 1 ]]
docker exec --env GAMA_SMTP_HOST='bad host' "$stable_container" \
  wp --allow-root --url=https://gama-software.com eval 'exit(wp_mail("blocked@example.test", "must fail closed", "invalid SMTP") ? 1 : 0);'

"$ROOT_DIR/bin/deploy-production" \
  --project "$stable_project" --env-file "$env_file" \
  --image "$candidate_image_id" --http-port 8080 --confirm-image "$candidate_image_id" >/dev/null
stable_container="$(docker ps --filter label=com.docker.compose.project="$stable_project" --filter label=com.docker.compose.service=wordpress --format '{{.ID}}')"
docker exec "$stable_container" wp --allow-root --url=https://gama-software.com eval '
  $path = get_option("gama_production_runtime_upload");
  exit("persistent" === get_option("gama_production_runtime_identity") && is_file($path) && "persistent-media" === file_get_contents($path) ? 0 : 1);
'

"$ROOT_DIR/bin/rollback-production" \
  --project "$stable_project" --env-file "$env_file" \
  --image "$base_image_id" --http-port 8080 --confirm-image "$base_image_id" >/dev/null
stable_container="$(docker ps --filter label=com.docker.compose.project="$stable_project" --filter label=com.docker.compose.service=wordpress --format '{{.ID}}')"
[[ "$(docker inspect --format '{{.Config.Image}}' "$stable_container")" == "$base_image_id" ]]
docker exec "$stable_container" wp --allow-root --url=https://gama-software.com eval '
  $path = get_option("gama_production_runtime_upload");
  exit("persistent" === get_option("gama_production_runtime_identity") && is_file($path) ? 0 : 1);
'

echo 'Isolated production first deploy, candidate, encrypted SMTP, persistence and code rollback runtime passed.'
