#!/usr/bin/env bash
set -euo pipefail

# This test catches a broken local runtime contract: a clean checkout must be
# able to bootstrap WordPress, restart without losing content, and keep test
# mail inside the project's Mailpit service.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE=("$ROOT_DIR/bin/_compose")

cleanup() {
  if [[ "${1:-}" == "--clean" ]]; then
    "$ROOT_DIR/bin/reset" --confirm
  fi
}

if [[ ! -f "$ROOT_DIR/.env" ]]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
fi

wp_port="$(sed -n 's/^WP_HTTP_PORT=//p' "$ROOT_DIR/.env" | tail -n 1)"
wp_port="${wp_port:-8090}"
mailpit_port="$(sed -n 's/^MAILPIT_HTTP_PORT=//p' "$ROOT_DIR/.env" | tail -n 1)"
mailpit_port="${mailpit_port:-8027}"

if [[ "${1:-}" == "--clean" ]]; then
  "$ROOT_DIR/bin/reset" --confirm
elif [[ "$#" -ne 0 ]]; then
  echo "Usage: $0 [--clean]" >&2
  exit 64
fi

"$ROOT_DIR/bin/start"

for service in db wordpress mailpit; do
  status="$("${COMPOSE[@]}" ps --format json "$service")"
  grep -q 'healthy' <<<"$status"
done

"$ROOT_DIR/bin/wp" core is-installed
"$ROOT_DIR/bin/wp" core version | grep -Fx '7.1.0'
"$ROOT_DIR/bin/wp" theme list --status=active --field=name | grep -Fx 'gama-software'
"$ROOT_DIR/bin/wp" plugin list --status=active --field=name | grep -Fx 'gama-local-mailpit'

upload_path="$("$ROOT_DIR/bin/wp" eval '$upload = wp_upload_bits("gsweb10-smoke.txt", null, "persistent"); if (!empty($upload["error"])) { fwrite(STDERR, $upload["error"]); exit(1); } echo $upload["file"];')"
test -f "$upload_path"

"$ROOT_DIR/bin/restart"
test -f "$upload_path"
curl --fail --silent --show-error "http://127.0.0.1:${wp_port}/" >/dev/null
curl --fail --silent --show-error "http://127.0.0.1:${wp_port}/wp-admin/" >/dev/null

"$ROOT_DIR/bin/test-mail"
curl --fail --silent --show-error "http://127.0.0.1:${mailpit_port}/api/v1/messages" | grep -q 'gsweb10-smoke@invalid.test'

cleanup "${1:-}"
