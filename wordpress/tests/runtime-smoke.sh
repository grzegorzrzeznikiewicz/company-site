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

upload_token="gsweb10-upload-$(date +%s)-$$"
"$ROOT_DIR/bin/wp" eval "\$upload = wp_upload_bits('${upload_token}.txt', null, 'persistent'); if (!empty(\$upload['error'])) { fwrite(STDERR, \$upload['error']); exit(1); } update_option('gsweb10_smoke_upload_path', \$upload['file']);"
assert_upload_persisted() {
  "$ROOT_DIR/bin/wp" eval '$path = get_option("gsweb10_smoke_upload_path"); if (!$path || !is_file($path)) { exit(1); }'
}
assert_upload_persisted

"$ROOT_DIR/bin/restart"
assert_upload_persisted
curl --fail --silent --show-error "http://127.0.0.1:${wp_port}/" >/dev/null
curl --fail --silent --show-error "http://127.0.0.1:${wp_port}/wp-admin/" >/dev/null

"$ROOT_DIR/bin/test-mail"

cleanup "${1:-}"
