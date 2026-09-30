#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
project="gama-wp-staging-https-cleanup-$RANDOM-$$"
candidate_image="${GAMA_RELEASE_HTTPS_CLEANUP_CANDIDATE_IMAGE:-}"
browser_image="${GAMA_RELEASE_HTTPS_CLEANUP_BROWSER_IMAGE:-}"
evidence_root="${GAMA_RELEASE_HTTPS_CLEANUP_EVIDENCE_ROOT:-}"
fixture=''
env_file="$fixture/staging.env"
runtime="$ROOT_DIR/tests/release-https-runtime.sh"

if [[ ! "$candidate_image" =~ ^sha256:[a-f0-9]{64}$ ]]; then
  echo 'GAMA_RELEASE_HTTPS_CLEANUP_CANDIDATE_IMAGE must be an immutable local image ID.' >&2
  exit 64
fi
if [[ -z "$browser_image" ]]; then
  echo 'GAMA_RELEASE_HTTPS_CLEANUP_BROWSER_IMAGE must name the built browser image.' >&2
  exit 64
fi
docker image inspect "$candidate_image" "$browser_image" >/dev/null
if [[ -z "$evidence_root" ]]; then
  evidence_root="$(mktemp -d "${TMPDIR:-/tmp}/gama-release-https-cleanup-evidence.XXXXXX")"
elif [[ "$evidence_root" != /* || -L "$evidence_root" ]]; then
  echo 'Cleanup evidence root must be an absolute directory, not a symlink.' >&2
  exit 64
else
  mkdir -p "$evidence_root"
fi
if [[ -n "$(find "$evidence_root" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
  echo "Refusing to overwrite cleanup evidence: $evidence_root" >&2
  exit 1
fi

fixture="$(mktemp -d "${TMPDIR:-/tmp}/gama-release-https-cleanup.XXXXXX")"
env_file="$fixture/staging.env"

printf '%s\n' \
  "WORDPRESS_IMAGE=$candidate_image" \
  'WORDPRESS_HTTP_PORT=' \
  'WP_DB_NAME=gama_staging' \
  'WP_DB_USER=gama_staging' \
  'WP_DB_PASSWORD=staging-database-test-only' \
  'WP_DB_ROOT_PASSWORD=staging-root-test-only' \
  'WP_HOME=http://wordpress' \
  'WP_SITE_TITLE=Gama Software HTTPS Cleanup Staging' \
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

COMPOSE=(
  docker compose
  --project-name "$project"
  --env-file "$env_file"
  --file "$ROOT_DIR/deploy/compose.yaml"
  --file "$ROOT_DIR/deploy/staging.override.yaml"
)
wordpress_container=''
case_volumes=''

cleanup() {
  local status=$?
  local cleanup_status=0
  local residual_containers residual_volumes fixture_present
  trap - EXIT
  set +e
  "${COMPOSE[@]}" down --volumes --remove-orphans >/dev/null 2>&1
  for volume in $case_volumes; do
    docker volume rm "$volume" >/dev/null 2>&1
  done
  find "$fixture" -type f -delete 2>/dev/null
  find "$fixture" -depth -type d -exec rmdir {} \; 2>/dev/null
  residual_containers="$(docker ps -a --quiet --filter "label=com.docker.compose.project=$project")"
  residual_volumes="$(docker volume ls --quiet --filter "label=com.docker.compose.project=$project")"
  fixture_present=0
  [[ -e "$fixture" ]] && fixture_present=1
  [[ -z "$residual_containers" ]] || cleanup_status=1
  [[ -z "$residual_volumes" ]] || cleanup_status=1
  [[ "$fixture_present" -eq 0 ]] || cleanup_status=1
  if [[ "$status" -eq 0 && "$cleanup_status" -ne 0 ]]; then
    status="$cleanup_status"
  fi
  printf '%s\n' \
    "exit_status=$status" \
    "project=$project" \
    "residual_containers=${residual_containers:-none}" \
    "residual_compose_volumes=${residual_volumes:-none}" \
    "staging_fixture_present=$fixture_present" \
    >"$evidence_root/overall-cleanup.audit"
  for evidence_file in "$evidence_root"/*; do
    [[ "$(basename "$evidence_file")" == SHA256SUMS ]] && continue
    shasum -a 256 "$evidence_file"
  done >"$evidence_root/SHA256SUMS"
  set -e
  exit "$status"
}
trap cleanup EXIT

wp_option() {
  docker exec --user 33:33 "$wordpress_container" \
    wp --path=/var/www/html "$@"
}

read_state_value() {
  local key="$1"
  local state_file="$2"
  sed -n "s/^${key}=//p" "$state_file"
}

audit_case() {
  local name="$1"
  local expected_status="$2"
  local actual_status="$3"
  local state_file="$4"
  local fixture_path trust_volume sidecar_container after_home after_siteurl
  local sidecar_present trust_present fixture_present private_key_present

  fixture_path="$(read_state_value fixture "$state_file")"
  trust_volume="$(read_state_value trust_volume "$state_file")"
  sidecar_container="$(read_state_value sidecar_container "$state_file")"
  [[ "$fixture_path" == "${TMPDIR:-/tmp}"/gama-release-https.* ]]
  [[ "$trust_volume" =~ ^gama-release-browser-trust-[0-9]+$ ]]
  [[ "$sidecar_container" =~ ^[a-f0-9]+$ ]]

  after_home="$(wp_option option get home)"
  after_siteurl="$(wp_option option get siteurl)"
  sidecar_present=0
  trust_present=0
  fixture_present=0
  private_key_present=0
  docker inspect "$sidecar_container" >/dev/null 2>&1 && sidecar_present=1
  docker volume inspect "$trust_volume" >/dev/null 2>&1 && trust_present=1
  [[ -e "$fixture_path" ]] && fixture_present=1
  if [[ -d "$fixture_path" ]] && find "$fixture_path" -type f \( -name 'ca.key' -o -name 'leaf.key' \) -print -quit | grep -q .; then
    private_key_present=1
  fi

  printf '%s\n' \
    "case=$name" \
    "expected_status=$expected_status" \
    "actual_status=$actual_status" \
    "original_home=$original_home" \
    "restored_home=$after_home" \
    "original_siteurl=$original_siteurl" \
    "restored_siteurl=$after_siteurl" \
    "sidecar_container=$sidecar_container" \
    "sidecar_present=$sidecar_present" \
    "trust_volume=$trust_volume" \
    "trust_volume_present=$trust_present" \
    "tls_fixture=$fixture_path" \
    "tls_fixture_present=$fixture_present" \
    "private_key_present=$private_key_present" \
    >"$evidence_root/$name.audit"

  if [[ "$actual_status" -ne "$expected_status" ||
        "$after_home" != "$original_home" ||
        "$after_siteurl" != "$original_siteurl" ||
        "$sidecar_present" -ne 0 ||
        "$trust_present" -ne 0 ||
        "$fixture_present" -ne 0 ||
        "$private_key_present" -ne 0 ]]; then
    echo "HTTPS cleanup invariant failed for $name; see $evidence_root/$name.audit" >&2
    return 1
  fi
}

run_signal_case() {
  local name="$1"
  local signal="$2"
  local expected_status="$3"
  local volume="gama-release-https-cleanup-$name-$$"
  local state_file="$evidence_root/$name.state"
  local log_file="$evidence_root/$name.log"
  local actual_status

  case_volumes="$case_volumes $volume"
  docker volume create --label gama.contract=release-browser-cleanup "$volume" >/dev/null
  set +e
  GAMA_STAGING_PROJECT="$project" \
    GAMA_RELEASE_BROWSER_IMAGE="$browser_image" \
    GAMA_RELEASE_BROWSER_ARTIFACT_VOLUME="$volume" \
    GAMA_RELEASE_HTTPS_TEST_STATE_FILE="$state_file" \
    GAMA_RELEASE_HTTPS_TEST_PAUSE_AFTER_START=1 \
    bash -c '
      target=$$
      state_file="$1"
      signal="$2"
      runtime="$3"
      (
        count=0
        while [[ ! -s "$state_file" && "$count" -lt 600 ]]; do
          sleep 0.1
          count=$((count + 1))
        done
        if [[ ! -s "$state_file" ]]; then
          printf "%s\n" "Timed out waiting for HTTPS runtime test state." >"$state_file.timeout"
          kill -TERM "$target"
          exit 1
        fi
        kill -s "$signal" "$target"
      ) &
      exec "$runtime"
    ' _ "$state_file" "$signal" "$runtime" >"$log_file" 2>&1
  actual_status=$?
  set -e
  [[ ! -e "$state_file.timeout" ]]
  [[ -s "$state_file" ]]
  audit_case "$name" "$expected_status" "$actual_status" "$state_file" || return 1
  docker volume rm "$volume" >/dev/null
}

run_exit_case() {
  local name='exit-97'
  local volume="gama-release-https-cleanup-exit-97-$$"
  local state_file="$evidence_root/$name.state"
  local log_file="$evidence_root/$name.log"
  local actual_status

  case_volumes="$case_volumes $volume"
  docker volume create --label gama.contract=release-browser-cleanup "$volume" >/dev/null
  set +e
  GAMA_STAGING_PROJECT="$project" \
    GAMA_RELEASE_BROWSER_IMAGE="$browser_image" \
    GAMA_RELEASE_BROWSER_ARTIFACT_VOLUME="$volume" \
    GAMA_RELEASE_HTTPS_TEST_STATE_FILE="$state_file" \
    GAMA_RELEASE_HTTPS_TEST_FAIL_AFTER_START=1 \
    "$runtime" >"$log_file" 2>&1
  actual_status=$?
  set -e
  [[ -s "$state_file" ]]
  audit_case "$name" 97 "$actual_status" "$state_file" || return 1
  docker volume rm "$volume" >/dev/null
}

"$ROOT_DIR/bin/deploy-staging" --project "$project" --env-file "$env_file" --confirm
wordpress_container="$("${COMPOSE[@]}" ps -q wordpress)"
[[ -n "$wordpress_container" ]]
[[ "$(docker inspect --format '{{.Image}}' "$wordpress_container")" == "$candidate_image" ]]
original_home="$(wp_option option get home)"
original_siteurl="$(wp_option option get siteurl)"

run_signal_case int INT 130
run_signal_case term TERM 143
run_exit_case

printf '%s\n' \
  "project=$project" \
  "candidate_image=$candidate_image" \
  "candidate_revision=$(docker image inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$candidate_image")" \
  "browser_image=$(docker image inspect --format '{{.Id}}' "$browser_image")" \
  "evidence_root=$evidence_root" \
  >"$evidence_root/summary.txt"

echo "HTTPS cleanup runtime passed INT=130, TERM=143 and injected exit=97 for $project."
echo "Cleanup evidence: $evidence_root"
