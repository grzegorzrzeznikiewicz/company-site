#!/usr/bin/env bash
set -euo pipefail

assert_no_published_ports() {
  local container="$1"
  local bindings
  bindings="$(docker inspect --format '{{json .HostConfig.PortBindings}}' "$container")" || return 1
  case "$bindings" in
    null|'{}') return 0 ;;
    *) return 1 ;;
  esac
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOSITORY_ROOT="$(cd "$ROOT_DIR/.." && pwd)"
baseline_revision='c26e19699c7a66a15e0854cf3bb4fce342bf2e2c'
baseline_build_image='node:24.14.0-alpine@sha256:7fddd9ddeae8196abf4a3ef2de34e11f7b1a722119f91f28ddf1e99dcafdf114'
candidate_revision="${GAMA_CWV_CANDIDATE_REF:-}"

if [[ ! "$candidate_revision" =~ ^[a-f0-9]{40}$ ]]; then
  echo 'GAMA_CWV_CANDIDATE_REF must be an exact 40-character candidate commit.' >&2
  exit 64
fi
git -C "$REPOSITORY_ROOT" cat-file -e "$candidate_revision^{commit}" 2>/dev/null || {
  echo 'GAMA_CWV_CANDIDATE_REF must resolve to a local commit.' >&2
  exit 64
}

artifact_root="${GAMA_CWV_ARTIFACT_ROOT:-}"
if [[ -n "$artifact_root" ]]; then
  if [[ "$artifact_root" != /* || -e "$artifact_root" || -L "$artifact_root" || ! -d "$(dirname "$artifact_root")" ]]; then
    echo 'GAMA_CWV_ARTIFACT_ROOT must be a new absolute path in an existing directory.' >&2
    exit 64
  fi
  mkdir "$artifact_root"
else
  artifact_root="$(mktemp -d "${TMPDIR:-/tmp}/gama-gsweb27-vitals-evidence.XXXXXX")"
fi
chmod 0700 "$artifact_root"

fixture="$(mktemp -d "${TMPDIR:-/tmp}/gama-gsweb27-vitals-fixture.XXXXXX")"
chmod 0700 "$fixture"
project="gama-wp-staging-cwv-$(printf '%x' "$$")"
candidate_tag="gama-wordpress:gsweb27-cwv-$candidate_revision-$$"
browser_tag="gama-wordpress-browser:gsweb27-cwv-$$"
candidate_image=''
browser_image=''
baseline_build_image_id=''
wordpress_container=''
original_home=''
original_siteurl=''
originals_captured=0
preview_before='000'
preview_after='000'
run_complete=0

status_log="$artifact_root/commands-statuses.txt"
record() {
  printf '%s status=%s\n' "$1" "$2" >>"$status_log"
}

preview_before="$(curl --silent --output /dev/null --write-out '%{http_code}' http://localhost:8090/ || true)"
if [[ "$preview_before" != 200 ]]; then
  echo 'Owner preview must return HTTP 200 before the diagnostic.' >&2
  rmdir "$fixture" "$artifact_root" 2>/dev/null || true
  exit 1
fi
record owner-preview-before 0

cat >"$fixture/no-ports.override.yaml" <<'YAML'
services:
  wordpress:
    ports: !reset []
YAML

env_file="$fixture/staging.env"
cat >"$env_file" <<EOF
WORDPRESS_IMAGE=sha256:$(printf '0%.0s' {1..64})
WP_DB_NAME=gama_cwv
WP_DB_USER=gama_cwv
WP_DB_PASSWORD=gama-cwv-db-only
WP_DB_ROOT_PASSWORD=gama-cwv-root-only
WP_HOME=http://wordpress
WP_ENVIRONMENT_TYPE=local
WP_SITE_TITLE=Gama Software CWV Fixture
WP_ADMIN_USER=gama_cwv_admin
WP_ADMIN_PASSWORD=gama-cwv-admin-only
WP_ADMIN_EMAIL=cwv@example.test
GAMA_CONTACT_RECIPIENT=recipient@example.test
GAMA_CONTACT_SENDER=sender@example.test
GAMA_MAIL_SINK_HOST=mailpit
GAMA_MAIL_SINK_PORT=1025
EOF
chmod 0600 "$env_file"

COMPOSE=(
  docker compose
  --project-name "$project"
  --env-file "$env_file"
  --file "$ROOT_DIR/deploy/compose.yaml"
  --file "$ROOT_DIR/deploy/staging.override.yaml"
  --file "$fixture/no-ports.override.yaml"
)

wp_option() {
  docker exec --user 33:33 "$wordpress_container" wp --path=/var/www/html --url=http://127.0.0.1 "$@"
}

finalize_artifacts() {
  local status="$1"
  PREVIEW_BEFORE="$preview_before" PREVIEW_AFTER="$preview_after" RUN_STATUS="$status" \
    CLEANUP_COMPLETE="$run_complete" node -e '
      const fs = require("node:fs");
      const result = {
        formatVersion: 1,
        ownerPreviewBefore: Number(process.env.PREVIEW_BEFORE),
        ownerPreviewAfter: Number(process.env.PREVIEW_AFTER),
        exitStatus: Number(process.env.RUN_STATUS),
        exactNamespaceAbsent: process.env.CLEANUP_COMPLETE === "1",
      };
      fs.writeFileSync(process.argv[1], `${JSON.stringify(result, null, 2)}\n`);
    ' "$artifact_root/cleanup.json"
  (
    cd "$artifact_root"
    find . -type f ! -name SHA256SUMS -print | LC_ALL=C sort | sed 's#^./##' | xargs shasum -a 256 >SHA256SUMS
  )
  chmod 0644 "$artifact_root"/*
}

cleanup() {
  local status="$1"
  local cleanup_status=0
  local restore_status=0
  local compose_status=0
  trap - EXIT INT TERM
  set +e
  if [[ "$originals_captured" -eq 1 ]] && docker inspect "$wordpress_container" >/dev/null 2>&1; then
    wp_option option update home "$original_home" >/dev/null || restore_status=1
    wp_option option update siteurl "$original_siteurl" >/dev/null || restore_status=1
    [[ "$(docker exec --user 33:33 "$wordpress_container" wp --path=/var/www/html option get home 2>/dev/null)" == "$original_home" ]] || restore_status=1
    [[ "$(docker exec --user 33:33 "$wordpress_container" wp --path=/var/www/html option get siteurl 2>/dev/null)" == "$original_siteurl" ]] || restore_status=1
  fi
  record wordpress-options-restore "$restore_status"
  [[ "$restore_status" -eq 0 ]] || cleanup_status=1
  "${COMPOSE[@]}" down --volumes --remove-orphans --timeout 10 >/dev/null 2>&1 || compose_status=1
  record compose-down "$compose_status"
  [[ "$compose_status" -eq 0 ]] || cleanup_status=1
  docker image rm "$candidate_tag" "$browser_tag" >/dev/null 2>&1 || true
  find "$fixture" -depth -delete 2>/dev/null
  [[ ! -e "$fixture" ]] || cleanup_status=1
  docker ps -a --quiet --filter "label=com.docker.compose.project=$project" | grep -q . && cleanup_status=1
  docker network ls --quiet --filter "label=com.docker.compose.project=$project" | grep -q . && cleanup_status=1
  docker volume ls --quiet --filter "label=com.docker.compose.project=$project" | grep -q . && cleanup_status=1
  preview_after="$(curl --silent --output /dev/null --write-out '%{http_code}' http://localhost:8090/ || true)"
  [[ "$preview_after" == 200 ]] || cleanup_status=1
  if [[ "$cleanup_status" -eq 0 ]]; then
    run_complete=1
    record exact-cleanup 0
    record owner-preview-after 0
  else
    record exact-cleanup 1
  fi
  if [[ "$status" -eq 0 && "$cleanup_status" -ne 0 ]]; then status="$cleanup_status"; fi
  finalize_artifacts "$status"
  set -e
  echo "CWV evidence retained at: $artifact_root"
  exit "$status"
}
trap 'cleanup "$?"' EXIT
trap 'cleanup 130' INT
trap 'cleanup 143' TERM

mkdir "$fixture/candidate-source" "$fixture/baseline-source"
git -C "$REPOSITORY_ROOT" archive "$candidate_revision" | tar -x -C "$fixture/candidate-source"
git -C "$REPOSITORY_ROOT" archive "$baseline_revision" | tar -x -C "$fixture/baseline-source"
record source-archives 0

docker build \
  --file "$fixture/candidate-source/wordpress/runtime/Dockerfile" \
  --build-arg "GAMA_GIT_SHA=$candidate_revision" \
  --build-arg GAMA_RELEASE_MARKER=gsweb27-cwv \
  --tag "$candidate_tag" \
  "$fixture/candidate-source"
candidate_image="$(docker image inspect --format '{{.Id}}' "$candidate_tag")"
[[ "$candidate_image" =~ ^sha256:[a-f0-9]{64}$ ]]
[[ "$(docker image inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$candidate_image")" == "$candidate_revision" ]]
sed -i.bak "s#^WORDPRESS_IMAGE=.*#WORDPRESS_IMAGE=$candidate_image#" "$env_file"
rm "$env_file.bak"
record candidate-image-build 0

docker pull "$baseline_build_image"
baseline_build_image_id="$(docker image inspect --format '{{.Id}}' "$baseline_build_image")"
[[ "$baseline_build_image_id" =~ ^sha256:[a-f0-9]{64}$ ]]
docker run --rm \
  --volume "$fixture/baseline-source:/app" \
  --workdir /app \
  "$baseline_build_image_id" sh -ec 'npm ci && npm run build'
[[ -f "$fixture/baseline-source/dist/index.html" ]]
record baseline-build 0

docker build --file "$ROOT_DIR/qa/browser.Dockerfile" --tag "$browser_tag" "$REPOSITORY_ROOT"
browser_image="$(docker image inspect --format '{{.Id}}' "$browser_tag")"
[[ "$browser_image" =~ ^sha256:[a-f0-9]{64}$ ]]
record browser-image-build 0

"${COMPOSE[@]}" config >/dev/null
"${COMPOSE[@]}" up --detach db mailpit uploads-init
"${COMPOSE[@]}" run --rm --no-deps install
"${COMPOSE[@]}" up --detach wordpress
wordpress_container="$("${COMPOSE[@]}" ps -q wordpress)"
for _ in $(seq 1 60); do
  [[ "$(docker inspect --format '{{.State.Health.Status}}' "$wordpress_container")" == healthy ]] && break
  sleep 1
done
[[ "$(docker inspect --format '{{.State.Health.Status}}' "$wordpress_container")" == healthy ]]
"${COMPOSE[@]}" run --rm bootstrap
assert_no_published_ports "$wordpress_container"
[[ "$(docker inspect --format '{{.Image}}' "$wordpress_container")" == "$candidate_image" ]]
record wordpress-deploy 0

original_home="$(wp_option option get home)"
original_siteurl="$(wp_option option get siteurl)"
originals_captured=1
wp_option option update home http://127.0.0.1 >/dev/null
wp_option option update siteurl http://127.0.0.1 >/dev/null
[[ "$(wp_option option get home)" == http://127.0.0.1 ]]
[[ "$(wp_option option get siteurl)" == http://127.0.0.1 ]]
  [[ "$(wp_option post list --post_type=post --post_status=publish --format=count)" == 0 ]]
record empty-blog-home-fixture 0

if [[ "${GAMA_CWV_TEST_EXIT_AFTER_DEPLOY:-0}" == 1 ]]; then
  record injected-exit-after-deploy 97
  exit 97
fi
if [[ "${GAMA_CWV_TEST_PAUSE_AFTER_DEPLOY:-0}" == 1 ]]; then
  record pause-after-deploy 0
  while :; do sleep 1; done
fi

wordpress_server_version="$(docker exec "$wordpress_container" apache2 -v | sed -n '1s#^Server version: ##p')"
CONFIG_PATH="$fixture/config.json" BASELINE_ROOT=/baseline \
  CANDIDATE_IMAGE="$candidate_image" BROWSER_IMAGE="$browser_image" \
  BUILD_IMAGE="$baseline_build_image_id" CANDIDATE_REVISION="$candidate_revision" \
  BASELINE_REVISION="$baseline_revision" SERVER_VERSION="$wordpress_server_version" node -e '
    const fs = require("node:fs");
    fs.writeFileSync(process.env.CONFIG_PATH, `${JSON.stringify({
      baselineRoot: process.env.BASELINE_ROOT,
      candidateImage: process.env.CANDIDATE_IMAGE,
      browserImage: process.env.BROWSER_IMAGE,
      baselineBuildImage: process.env.BUILD_IMAGE,
      candidateRevision: process.env.CANDIDATE_REVISION,
      baselineRevision: process.env.BASELINE_REVISION,
      wordpressBaseUrl: "http://127.0.0.1",
      wordpressServerVersion: process.env.SERVER_VERSION,
    }, null, 2)}\n`);
  '
chmod 0600 "$fixture/config.json"

docker run --rm --network none \
  --volume "$artifact_root:/evidence" \
  --env "GAMA_SOURCE_REVISION=$candidate_revision" \
  --env "GAMA_BROWSER_IMAGE_ID=$browser_image" \
  --env "GAMA_SERVER_IMAGE_ID=$browser_image" \
  "$browser_image" node ./vitals/runner.mjs controls /evidence/collector-controls.json
docker run --rm --network none \
  --volume "$artifact_root:/evidence" \
  --env "GAMA_SOURCE_REVISION=$candidate_revision" \
  --env "GAMA_BROWSER_IMAGE_ID=$browser_image" \
  --env "GAMA_SERVER_IMAGE_ID=$browser_image" \
  "$browser_image" node ./vitals/runner.mjs journey-controls /evidence/journey-controls.json
record actual-controls 0

docker run --rm --network "container:$wordpress_container" \
  --volume "$fixture/config.json:/config/config.json:ro" \
  --volume "$fixture/baseline-source/dist:/baseline:ro" \
  --volume "$artifact_root:/evidence" \
  "$browser_image" node ./vitals/runner.mjs measure /config/config.json /evidence/raw-home.json home
record paired-home-measurement 0

media_id="$(wp_option media import /var/www/html/wp-content/themes/gama-software/assets/images/gama-software-logo.png --title='GSWEB-27 synthetic article media' --porcelain)"
post_id="$(wp_option post create --post_type=post --post_status=publish \
  --post_name=gama-cwv-representative-article \
  --post_title='GSWEB-27 representative article' \
  --post_content='<!-- wp:heading --><h2 class="wp-block-heading">Reprezentatywny artykuł testowy</h2><!-- /wp:heading --><!-- wp:paragraph --><p>Wyłącznie syntetyczna treść diagnostyczna w jednorazowym środowisku lokalnym.</p><!-- /wp:paragraph -->' \
  --porcelain)"
wp_option post meta update "$post_id" _thumbnail_id "$media_id" >/dev/null
[[ "$(wp_option post list --post_type=post --post_status=publish --format=count)" == 1 ]]
record synthetic-blog-fixture 0

docker run --rm --network "container:$wordpress_container" \
  --volume "$fixture/config.json:/config/config.json:ro" \
  --volume "$fixture/baseline-source/dist:/baseline:ro" \
  --volume "$artifact_root:/evidence" \
  "$browser_image" node ./vitals/runner.mjs measure /config/config.json /evidence/raw-wordpress-only.json wordpress-only
record wordpress-only-measurement 0

docker run --rm --network none --volume "$artifact_root:/evidence" "$browser_image" \
  node ./vitals/runner.mjs merge /evidence/raw-home.json /evidence/raw-wordpress-only.json /evidence/raw.json
docker run --rm --network none --volume "$artifact_root:/evidence" "$browser_image" \
  node ./vitals/runner.mjs summarize /evidence/raw.json /evidence/summary.json
record validation-and-summary 0

CANDIDATE_IMAGE="$candidate_image" BROWSER_IMAGE="$browser_image" \
  BUILD_IMAGE="$baseline_build_image_id" CANDIDATE_REVISION="$candidate_revision" \
  BASELINE_REVISION="$baseline_revision" SERVER_VERSION="$wordpress_server_version" \
  PROJECT="$project" node -e '
    const fs = require("node:fs");
    fs.writeFileSync(process.argv[1], `${JSON.stringify({
      formatVersion: 1,
      date: "2026-09-06",
      project: process.env.PROJECT,
      candidateRevision: process.env.CANDIDATE_REVISION,
      candidateImage: process.env.CANDIDATE_IMAGE,
      baselineRevision: process.env.BASELINE_REVISION,
      baselineBuildImage: process.env.BUILD_IMAGE,
      baselineBuildImageReference: "node:24.14.0-alpine@sha256:7fddd9ddeae8196abf4a3ef2de34e11f7b1a722119f91f28ddf1e99dcafdf114",
      browserImage: process.env.BROWSER_IMAGE,
      browserRuntime: "Playwright 1.62.1 / Node 24.18.1 / bundled Chromium",
      wordpressServerVersion: process.env.SERVER_VERSION,
      baselineServer: { implementation: "node:http", compression: "none", cacheControl: "no-store" },
      network: "unthrottled local loopback; browser shares WordPress container network namespace",
      viewports: [{ name: "desktop", width: 1440, height: 900 }, { name: "phone", width: 390, height: 844 }],
      cache: "fresh browser context per sample",
      reducedMotion: "reduce",
      fieldData: false,
    }, null, 2)}\n`);
  ' "$artifact_root/environment.json"
record environment-evidence 0

exit 0
