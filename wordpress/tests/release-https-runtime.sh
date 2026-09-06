#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
project="${GAMA_STAGING_PROJECT:-}"
browser_image="${GAMA_RELEASE_BROWSER_IMAGE:-}"
artifact_volume="${GAMA_RELEASE_BROWSER_ARTIFACT_VOLUME:-}"
sidecar_image='wordpress:7.1.0-php8.4-apache@sha256:b8f37de278183840a09f5a4b5bf5ec9f09177a9984d2fe5cc072b4388128bd9d'

if [[ ! "$project" =~ ^gama-wp-staging-[a-z0-9][a-z0-9-]{2,40}$ ]]; then
  echo 'GAMA_STAGING_PROJECT must name the active isolated staging namespace.' >&2
  exit 64
fi
if [[ -z "$browser_image" || -z "$artifact_volume" ]]; then
  echo 'HTTPS runtime requires the built browser image and artifact volume.' >&2
  exit 64
fi
network="${project}_default"
docker network inspect "$network" >/dev/null
docker image inspect "$browser_image" >/dev/null
docker volume inspect "$artifact_volume" >/dev/null

wordpress_container_ids="$(
  docker ps \
    --filter "label=com.docker.compose.project=$project" \
    --filter 'label=com.docker.compose.service=wordpress' \
    --format '{{.ID}}'
)"
wordpress_container_count="$(printf '%s\n' "$wordpress_container_ids" | awk 'NF { count += 1 } END { print count + 0 }')"
if [[ "$wordpress_container_count" -ne 1 ]]; then
  echo 'HTTPS runtime requires exactly one running WordPress service container.' >&2
  exit 1
fi
wordpress_container="$wordpress_container_ids"
candidate_image="$(docker inspect --format '{{.Image}}' "$wordpress_container")"
candidate_revision="$(docker image inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$candidate_image")"
browser_image_id="$(docker image inspect --format '{{.Id}}' "$browser_image")"

fixture="$(mktemp -d "${TMPDIR:-/tmp}/gama-release-https.XXXXXX")"
chmod 0700 "$fixture"
trust_volume="gama-release-browser-trust-$$"
original_home=''
original_siteurl=''
originals_captured=0
cleanup_complete=0
TLS_COMPOSE=(
  docker compose
  --project-name "$project"
  --file "$ROOT_DIR/tests/release-https-compose.yaml"
)

wp_option() {
  docker exec --user 33:33 "$wordpress_container" \
    wp --path=/var/www/html "$@"
}

store_probe_evidence() {
  local mode="$1"
  local json="$2"
  local evidence_file="$fixture/$mode.json"
  printf '%s\n' "$json" >"$evidence_file"
  chmod 0644 "$evidence_file"
  docker run --rm --network none \
    --volume "$evidence_file:/source/probe.json:ro" \
    --volume "$artifact_volume:/artifacts" \
    --entrypoint sh "$browser_image" -ec \
    'node -e '\''JSON.parse(require("node:fs").readFileSync("/source/probe.json", "utf8"))'\''; mkdir -p /artifacts/tls-probes; install -m 0644 /source/probe.json "/artifacts/tls-probes/'"$mode"'.json"'
  echo "$mode TLS probe passed."
}

cleanup() {
  local status=$?
  local cleanup_status=0
  trap - EXIT INT TERM
  set +e
  if [[ "$originals_captured" -eq 1 ]] && docker inspect "$wordpress_container" >/dev/null 2>&1; then
    wp_option option update home "$original_home" >/dev/null || cleanup_status=1
    wp_option option update siteurl "$original_siteurl" >/dev/null || cleanup_status=1
    [[ "$(wp_option option get home 2>/dev/null)" == "$original_home" ]] || cleanup_status=1
    [[ "$(wp_option option get siteurl 2>/dev/null)" == "$original_siteurl" ]] || cleanup_status=1
  fi
  GAMA_RELEASE_HTTPS_FIXTURE="$fixture" "${TLS_COMPOSE[@]}" rm --stop --force wordpress-tls >/dev/null 2>&1 || cleanup_status=1
  if docker ps -a --quiet \
    --filter "label=com.docker.compose.project=$project" \
    --filter 'label=com.docker.compose.service=wordpress-tls' | grep -q .; then
    cleanup_status=1
  fi
  if docker volume inspect "$trust_volume" >/dev/null 2>&1; then
    docker volume rm "$trust_volume" >/dev/null 2>&1 || cleanup_status=1
  fi
  docker volume inspect "$trust_volume" >/dev/null 2>&1 && cleanup_status=1
  find "$fixture" -type f -delete 2>/dev/null
  find "$fixture" -depth -type d -exec rmdir {} \; 2>/dev/null
  [[ ! -e "$fixture" ]] || cleanup_status=1
  set -e
  cleanup_complete=1
  if [[ "$status" -eq 0 && "$cleanup_status" -ne 0 ]]; then
    status="$cleanup_status"
  fi
  exit "$status"
}
trap cleanup EXIT INT TERM

printf '%s\n' \
  '<VirtualHost *:443>' \
  '  ServerName wordpress-tls' \
  '  SSLEngine on' \
  '  SSLCertificateFile /run/gama-release-https/leaf.crt' \
  '  SSLCertificateKeyFile /run/gama-release-https/leaf.key' \
  '  SSLProtocol -all +TLSv1.2 +TLSv1.3' \
  '  ProxyRequests Off' \
  '  ProxyPreserveHost On' \
  '  RequestHeader set X-Forwarded-Proto "https"' \
  '  ProxyPass "/" "http://wordpress/"' \
  '  ProxyPassReverse "/" "http://wordpress/"' \
  '</VirtualHost>' \
  >"$fixture/apache.conf"
chmod 0644 "$fixture/apache.conf"

docker run --rm --network none \
  --volume "$fixture:/tls" \
  --entrypoint sh "$sidecar_image" -ec '
    umask 077
    openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out /tls/ca.key >/dev/null 2>&1
    openssl req -x509 -new -sha256 -days 1 -key /tls/ca.key \
      -subj "/CN=Gama Software ephemeral release test CA" -out /tls/ca.crt
    openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out /tls/leaf.key >/dev/null 2>&1
    openssl req -new -sha256 -key /tls/leaf.key \
      -subj "/CN=wordpress-tls" -out /tls/leaf.csr
    printf "%s\n" \
      "subjectAltName=DNS:wordpress-tls" \
      "basicConstraints=critical,CA:FALSE" \
      "keyUsage=critical,digitalSignature,keyEncipherment" \
      "extendedKeyUsage=serverAuth" > /tls/leaf.ext
    openssl x509 -req -sha256 -days 1 -in /tls/leaf.csr \
      -CA /tls/ca.crt -CAkey /tls/ca.key -CAcreateserial \
      -extfile /tls/leaf.ext -out /tls/leaf.crt >/dev/null 2>&1
    rm /tls/leaf.csr /tls/leaf.ext /tls/ca.srl
    chmod 0600 /tls/ca.key /tls/leaf.key
    chmod 0644 /tls/ca.crt /tls/leaf.crt
  '

for private_key in "$fixture/ca.key" "$fixture/leaf.key"; do
  key_mode="$(stat -c '%a' "$private_key" 2>/dev/null || stat -f '%Lp' "$private_key")"
  [[ "$key_mode" == 600 ]]
done
ca_fingerprint="$(openssl x509 -in "$fixture/ca.crt" -noout -fingerprint -sha256 | cut -d= -f2 | tr -d :)"
leaf_fingerprint="$(openssl x509 -in "$fixture/leaf.crt" -noout -fingerprint -sha256 | cut -d= -f2 | tr -d :)"

docker volume create --label gama.contract=release-browser-trust "$trust_volume" >/dev/null
docker run --rm --network none \
  --volume "$fixture/ca.crt:/source/ca.crt:ro" \
  --volume "$trust_volume:/trust" \
  --entrypoint sh "$sidecar_image" -ec \
  'find /trust -mindepth 1 -delete; install -m 0444 /source/ca.crt /trust/ca.crt; test "$(find /trust -mindepth 1 -maxdepth 1 -type f -printf "%f\n")" = ca.crt'

original_home="$(wp_option option get home)"
original_siteurl="$(wp_option option get siteurl)"
originals_captured=1
wp_option option update home https://wordpress-tls >/dev/null
wp_option option update siteurl https://wordpress-tls >/dev/null
[[ "$(wp_option option get home)" == https://wordpress-tls ]]
[[ "$(wp_option option get siteurl)" == https://wordpress-tls ]]

GAMA_RELEASE_HTTPS_FIXTURE="$fixture" \
  "${TLS_COMPOSE[@]}" up --detach --wait --wait-timeout 60 wordpress-tls
sidecar_container="$(
  docker ps \
    --filter "label=com.docker.compose.project=$project" \
    --filter 'label=com.docker.compose.service=wordpress-tls' \
    --format '{{.ID}}'
)"
[[ -n "$sidecar_container" ]]
[[ "$(docker inspect --format '{{json .HostConfig.PortBindings}}' "$sidecar_container")" == null ]]
sidecar_ip="$(docker inspect --format "{{(index .NetworkSettings.Networks \"$network\").IPAddress}}" "$sidecar_container")"
[[ "$sidecar_ip" =~ ^[0-9a-fA-F:.]+$ ]]

if [[ "${GAMA_RELEASE_HTTPS_TEST_FAIL_AFTER_START:-0}" == 1 ]]; then
  echo 'Injected HTTPS cleanup failure-path probe.' >&2
  exit 97
fi

probe_output="$(docker run --rm \
  --network "$network" \
  --env WP_BASE_URL=https://wordpress-tls \
  "$browser_image" node ./release-tls-probe.mjs reject-untrusted)"
store_probe_evidence reject-untrusted "$probe_output"

probe_output="$(docker run --rm \
  --network "$network" \
  --add-host "wordpress-tls-wrong:$sidecar_ip" \
  --volume "$trust_volume:/run/gama-release-trust:ro" \
  --env WP_BASE_URL=https://wordpress-tls-wrong \
  --entrypoint /usr/local/bin/gama-release-https-trust \
  "$browser_image" node ./release-tls-probe.mjs reject-wrong-hostname)"
store_probe_evidence reject-wrong-hostname "$probe_output"

probe_output="$(docker run --rm \
  --network "$network" \
  --volume "$trust_volume:/run/gama-release-trust:ro" \
  --env WP_BASE_URL=https://wordpress-tls \
  --entrypoint /usr/local/bin/gama-release-https-trust \
  "$browser_image" node ./release-tls-probe.mjs accept-valid)"
store_probe_evidence accept-valid "$probe_output"

docker run --rm \
  --network "$network" \
  --volume "$artifact_volume:/artifacts" \
  --volume "$trust_volume:/run/gama-release-trust:ro" \
  --env WP_BASE_URL=https://wordpress-tls \
  --env GAMA_PLAYWRIGHT_RUN=release-regression \
  --entrypoint /usr/local/bin/gama-release-https-trust \
  "$browser_image" npm test -- --grep @release-regression

[[ "$(docker inspect --format '{{.Image}}' "$wordpress_container")" == "$candidate_image" ]]
[[ "$(docker image inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$candidate_image")" == "$candidate_revision" ]]
printf '%s\n' \
  '{' \
  "  \"candidateImage\": \"$candidate_image\"," \
  "  \"candidateRevision\": \"$candidate_revision\"," \
  "  \"browserImage\": \"$browser_image_id\"," \
  "  \"caSha256Fingerprint\": \"$ca_fingerprint\"," \
  "  \"leafSha256Fingerprint\": \"$leaf_fingerprint\"" \
  '}' >"$fixture/metadata.json"
chmod 0644 "$fixture/metadata.json"
docker run --rm --network none \
  --volume "$fixture/metadata.json:/source/metadata.json:ro" \
  --volume "$artifact_volume:/artifacts" \
  --entrypoint sh "$sidecar_image" -ec \
  'mkdir -p /artifacts/tls-probes; install -m 0644 /source/metadata.json /artifacts/tls-probes/metadata.json'

echo "Trusted HTTPS release regression passed with CA fingerprint $ca_fingerprint."
