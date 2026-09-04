#!/usr/bin/env bash
set -euo pipefail

# This test catches a broken local runtime contract: a clean checkout must be
# able to bootstrap WordPress, restart without losing content, and keep test
# mail inside the project's Mailpit service.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE=("$ROOT_DIR/bin/_compose")
clean_run=false
original_logo_id=''
editor_logo_id=''

cleanup() {
  local test_status=$?

  if [[ "$clean_run" == false && -n "$original_logo_id" && -n "$editor_logo_id" ]]; then
    set +e
    "$ROOT_DIR/bin/wp" eval "set_theme_mod('custom_logo', (int)'$original_logo_id');" >/dev/null
    "$ROOT_DIR/bin/wp" post delete "$editor_logo_id" --force >/dev/null
    set -e
  fi

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
  grep -Fq '"Health":"healthy"' <<<"$status"
done

"$ROOT_DIR/bin/wp" core is-installed
"$ROOT_DIR/bin/wp" core version | grep -Fx '7.1'
"$ROOT_DIR/bin/wp" theme list --status=active --field=name | grep -Fx 'gama-software'
"$ROOT_DIR/bin/wp" plugin list --status=active --field=name | grep -Fx 'gama-local-mailpit'
"$ROOT_DIR/bin/wp" plugin list --status=active --field=name | grep -Fx 'gama-contact'
"$ROOT_DIR/bin/wp" plugin list --status=active --field=name | grep -Fx 'gama-seo'
"$ROOT_DIR/bin/wp" option get show_on_front | grep -Fx page
"$ROOT_DIR/bin/wp" option get permalink_structure | grep -Fx '/%postname%/'
home_page_id="$("$ROOT_DIR/bin/wp" option get page_on_front)"
blog_page_id="$("$ROOT_DIR/bin/wp" option get page_for_posts)"
[[ "$home_page_id" =~ ^[1-9][0-9]*$ ]]
[[ "$blog_page_id" =~ ^[1-9][0-9]*$ ]]
"$ROOT_DIR/bin/wp" post get "$home_page_id" --field=post_status | grep -Fx publish
"$ROOT_DIR/bin/wp" post get "$blog_page_id" --field=post_status | grep -Fx publish
"$ROOT_DIR/bin/wp" post get "$blog_page_id" --field=post_name | grep -Fx blog
for legal_slug in polityka-prywatnosci regulamin; do
  legal_id="$("$ROOT_DIR/bin/wp" post list --post_type=page --name="$legal_slug" --post_status=draft --posts_per_page=1 --field=ID | tail -n 1)"
  [[ "$legal_id" =~ ^[1-9][0-9]*$ ]]
done
original_logo_id="$("$ROOT_DIR/bin/wp" eval '$id=(int)get_theme_mod("custom_logo"); if ($id < 1 || get_post_meta($id,"_gama_asset_key",true)!=="gama-software-logo" || get_post_meta($id,"_wp_attachment_image_alt",true)!=="Gama Software") { exit(1); } echo $id;' | tail -n 1)"
[[ "$original_logo_id" =~ ^[1-9][0-9]*$ ]]
if "$ROOT_DIR/bin/wp" post list --post_type=post --post_status=publish --format=csv --fields=post_title,post_content | grep -Fq 'Welcome to WordPress. This is your first post. Edit or delete it, then start writing!'; then
  echo 'Exact default WordPress demonstration post remains published.' >&2
  exit 1
fi

upload_permission_token="gsweb10-permission-$(date +%s)-$$"
"$ROOT_DIR/bin/wp" eval "\$uploads = wp_upload_dir(); \$path = \$uploads['basedir'] . '/${upload_permission_token}-cli.txt'; if (file_put_contents(\$path, 'writable') === false) { exit(1); } unlink(\$path);"
"${COMPOSE[@]}" exec -T --user www-data wordpress php -r "\$path = '/var/www/html/wp-content/uploads/${upload_permission_token}.txt'; if (file_put_contents(\$path, 'writable') === false) { exit(1); } unlink(\$path);"

upload_token="gsweb10-upload-$(date +%s)-$$"
"$ROOT_DIR/bin/wp" eval "\$upload = wp_upload_bits('${upload_token}.txt', null, 'persistent'); if (!empty(\$upload['error'])) { fwrite(STDERR, \$upload['error']); exit(1); } update_option('gsweb10_smoke_upload_path', \$upload['file']);"
assert_upload_persisted() {
  "$ROOT_DIR/bin/wp" eval '$path = get_option("gsweb10_smoke_upload_path"); if (!$path || !is_file($path)) { exit(1); }'
}
assert_upload_persisted

editor_logo_id="$("$ROOT_DIR/bin/wp" media import /var/www/html/wp-content/themes/gama-software/assets/images/gama-software-logo.png --title='GSWEB-21 Editor logo persistence fixture' --alt='Editor logo' --porcelain | tail -n 1)"
[[ "$editor_logo_id" =~ ^[1-9][0-9]*$ ]]
"$ROOT_DIR/bin/wp" eval "set_theme_mod('custom_logo', (int)'$editor_logo_id');" >/dev/null
"$ROOT_DIR/bin/restart"
assert_upload_persisted
"$ROOT_DIR/bin/wp" eval "exit((int)get_theme_mod('custom_logo') === (int)'$editor_logo_id' ? 0 : 1);"
"$ROOT_DIR/bin/wp" eval "set_theme_mod('custom_logo', (int)'$original_logo_id');" >/dev/null
"$ROOT_DIR/bin/wp" post delete "$editor_logo_id" --force >/dev/null
editor_logo_id=''
runtime_url="http://localhost:${wp_port}"
home_html="$(curl --fail --silent --show-error "$runtime_url/")"
blog_html="$(curl --fail --silent --show-error "$runtime_url/blog/")"
grep -Fq 'gama-contact-form' <<<"$home_html"
grep -Fq 'gama-template--home' <<<"$blog_html"
curl --fail --silent --show-error "$runtime_url/wp-admin/" >/dev/null

"$ROOT_DIR/bin/test-mail"
GAMA_CONTACT_RUNTIME_URL="$runtime_url" GAMA_CONTACT_MAILPIT_URL="http://localhost:${MAILPIT_HTTP_PORT:-8027}" "$ROOT_DIR/tests/contact-form-runtime.sh"
"$ROOT_DIR/tests/contact-form-browser-runtime.sh"
GAMA_SEO_RUNTIME_URL="$runtime_url" "$ROOT_DIR/tests/seo-runtime.sh"
