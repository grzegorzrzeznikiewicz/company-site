#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOSITORY_ROOT="$(cd "$ROOT_DIR/.." && pwd)"
COMPOSE=("$ROOT_DIR/bin/_compose")
IMAGE="gama-wordpress-browser:gsweb20"
VOLUME="gama-contact-browser-artifacts-$$"
original_home=''
original_siteurl=''

cleanup() {
  local test_status=$?
  set +e
  if [[ -n "$original_home" ]]; then
    "$ROOT_DIR/bin/wp" option update home "$original_home" >/dev/null
  fi
  if [[ -n "$original_siteurl" ]]; then
    "$ROOT_DIR/bin/wp" option update siteurl "$original_siteurl" >/dev/null
  fi
  docker volume rm "$VOLUME" >/dev/null 2>&1
  set -e
  trap - EXIT
  exit "$test_status"
}
trap cleanup EXIT

wordpress_container="$("${COMPOSE[@]}" ps -q wordpress)"
mailpit_container="$("${COMPOSE[@]}" ps -q mailpit)"
[[ -n "$wordpress_container" && -n "$mailpit_container" ]]
network="$(docker inspect --format '{{range $name, $_ := .NetworkSettings.Networks}}{{$name}}{{"\n"}}{{end}}' "$wordpress_container" | head -n 1)"
[[ -n "$network" ]]

docker build \
  --cache-from 'gama-wordpress-browser:ci-cache' \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  --file "$ROOT_DIR/qa/browser.Dockerfile" \
  --tag "$IMAGE" \
  "$REPOSITORY_ROOT"

original_home="$("$ROOT_DIR/bin/wp" option get home)"
original_siteurl="$("$ROOT_DIR/bin/wp" option get siteurl)"
"$ROOT_DIR/bin/wp" option update home http://wordpress >/dev/null
"$ROOT_DIR/bin/wp" option update siteurl http://wordpress >/dev/null
"$ROOT_DIR/bin/wp" eval 'global $wpdb; foreach (["_transient_gama_contact_rate_", "_transient_timeout_gama_contact_rate_"] as $prefix) { $wpdb->query($wpdb->prepare("DELETE FROM {$wpdb->options} WHERE option_name LIKE %s", $wpdb->esc_like($prefix) . "%")); }'

docker volume create --label gama.contract=contact-browser "$VOLUME" >/dev/null
docker run --rm \
  --network "$network" \
  --volume "$VOLUME:/artifacts" \
  --env WP_BASE_URL=http://wordpress \
  --env MAILPIT_API_URL=http://mailpit:8025 \
  --env GAMA_PLAYWRIGHT_RUN=contact-form \
  "$IMAGE" npm test -- --grep @contact-form

docker run --rm \
  --volume "$VOLUME:/artifacts:ro" \
  --entrypoint sh \
  "$IMAGE" \
  -ec 'test -f /artifacts/contact-form/report/index.html; test -f /artifacts/contact-form/test-results/.last-run.json'

echo 'Browser contact form journey and required Playwright artifacts passed.'
