#!/usr/bin/env bash
set -euo pipefail

# This test catches a broken local runtime contract: a clean checkout must be
# able to bootstrap WordPress, restart without losing content, and keep test
# mail inside the project's Mailpit service.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE=("$ROOT_DIR/bin/_compose")
clean_run=false

cleanup() {
  local test_status=$?

  if [[ "$clean_run" == true ]]; then
    set +e
    "$ROOT_DIR/bin/reset" --confirm
    cleanup_status=$?
    set -e
    if [[ "$cleanup_status" -ne 0 ]]; then
      echo "Clean-test cleanup failed with status $cleanup_status." >&2
      if [[ "$test_status" -eq 0 ]]; then
        test_status=$cleanup_status
      fi
    fi
  fi

  trap - EXIT
  exit "$test_status"
}

if [[ ! -f "$ROOT_DIR/.env" ]]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
fi

wp_port="$(sed -n 's/^WP_HTTP_PORT=//p' "$ROOT_DIR/.env" | tail -n 1)"
wp_port="${wp_port:-8090}"

if [[ "${1:-}" == "--clean" ]]; then
  clean_run=true
  trap cleanup EXIT
  "$ROOT_DIR/bin/reset" --confirm
elif [[ "$#" -ne 0 ]]; then
  echo "Usage: $0 [--clean]" >&2
  exit 64
fi

bootstrap_output="$("$ROOT_DIR/bin/start" 2>&1)"
if grep -Eq 'PHP Warning: Undefined array key "HTTP_HOST"|Unable to create directory wp-content/uploads' <<<"$bootstrap_output"; then
  printf '%s\n' "$bootstrap_output" >&2
  exit 1
fi

for service in db wordpress mailpit; do
  status="$("${COMPOSE[@]}" ps --format json "$service")"
  grep -q 'healthy' <<<"$status"
done

"$ROOT_DIR/bin/wp" core is-installed
"$ROOT_DIR/bin/wp" core version | grep -Fx '7.1'
"$ROOT_DIR/bin/wp" theme list --status=active --field=name | grep -Fx 'gama-software'
"$ROOT_DIR/bin/wp" plugin list --status=active --field=name | grep -Fx 'gama-local-mailpit'

upload_permission_token="gsweb10-permission-$(date +%s)-$$"
"$ROOT_DIR/bin/wp" eval "\$uploads = wp_upload_dir(); \$path = \$uploads['basedir'] . '/${upload_permission_token}-cli.txt'; if (file_put_contents(\$path, 'writable') === false) { exit(1); } unlink(\$path);"
"${COMPOSE[@]}" exec -T --user www-data wordpress php -r "\$path = '/var/www/html/wp-content/uploads/${upload_permission_token}.txt'; if (file_put_contents(\$path, 'writable') === false) { exit(1); } unlink(\$path);"

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
