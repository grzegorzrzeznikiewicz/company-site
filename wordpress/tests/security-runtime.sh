#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
runtime_url="${GAMA_SECURITY_RUNTIME_URL:-http://localhost:8090}"
editor_login="gsweb23-editor-$$"
editor_id=''

cleanup() {
  if [[ -n "$editor_id" ]]; then
    "$ROOT_DIR/bin/wp" user delete "$editor_id" --yes >/dev/null 2>&1 || true
  fi
  "$ROOT_DIR/bin/wp" eval 'global $wpdb; foreach (["_transient_gama_security_login_rate_", "_transient_timeout_gama_security_login_rate_"] as $prefix) { $wpdb->query($wpdb->prepare("DELETE FROM {$wpdb->options} WHERE option_name LIKE %s", $wpdb->esc_like($prefix) . "%")); } delete_option("gama_security_lock_contract_ready");' >/dev/null 2>&1 || true
}
trap cleanup EXIT

editor_id="$("$ROOT_DIR/bin/wp" user create "$editor_login" "$editor_login@example.test" --role=editor --user_pass='GSWEB-23-test-only' --porcelain | tail -n 1)"
[[ "$editor_id" =~ ^[1-9][0-9]*$ ]]

"$ROOT_DIR/bin/wp" eval "
\$user = get_user_by('id', (int) '$editor_id');
wp_set_current_user(\$user->ID);
\$navigation_id = wp_insert_post(['post_type' => 'wp_navigation', 'post_status' => 'publish', 'post_title' => 'GSWEB-23 navigation capability', 'post_content' => '<!-- wp:navigation-link {"label":"Start","url":"/"} /-->'], true);
if (is_wp_error(\$navigation_id)) { fwrite(STDERR, 'Could not create navigation capability fixture.'); exit(1); }
\$required = ['edit_posts', 'publish_posts', 'edit_pages', 'upload_files', 'edit_theme_options'];
\$forbidden = ['activate_plugins', 'install_plugins', 'update_plugins', 'edit_plugins', 'edit_files', 'edit_users', 'promote_users', 'manage_options', 'switch_themes', 'install_themes', 'update_themes', 'update_core'];
foreach (\$required as \$capability) { if (!current_user_can(\$capability)) { fwrite(STDERR, 'Missing Editor capability: ' . \$capability); exit(1); } }
if (!current_user_can('edit_post', \$navigation_id)) { fwrite(STDERR, 'Editor cannot save a Core Navigation record.'); exit(1); }
foreach (\$forbidden as \$capability) { if (current_user_can(\$capability)) { fwrite(STDERR, 'Forbidden Editor capability: ' . \$capability); exit(1); } }
wp_set_current_user(1);
wp_delete_post(\$navigation_id, true);
echo 'editor-capability-matrix-ok';
" | grep -Fx 'editor-capability-matrix-ok'

headers="$(curl --silent --show-error --dump-header - --output /dev/null "$runtime_url/")"
grep -Eiq '^X-Content-Type-Options: nosniff\r?$' <<<"$headers"
grep -Eiq '^X-Frame-Options: SAMEORIGIN\r?$' <<<"$headers"
grep -Eiq '^Referrer-Policy: strict-origin-when-cross-origin\r?$' <<<"$headers"
grep -Eiq '^Permissions-Policy: camera=\(\), geolocation=\(\), microphone=\(\)\r?$' <<<"$headers"
if grep -Eiq '^Strict-Transport-Security:' <<<"$headers"; then
  echo 'Local HTTP must not emit HSTS.' >&2
  exit 1
fi

"$ROOT_DIR/bin/wp" eval "
\$_SERVER['REMOTE_ADDR'] = '198.51.100.23';
\$username = 'gsweb23-rate-fixture';
\$error = new WP_Error('incorrect_password', 'fixture');
for (\$attempt = 0; \$attempt < 10; ++\$attempt) { do_action('wp_login_failed', \$username, \$error); }
\$blocked = apply_filters('authenticate', null, \$username, 'correct-but-not-evaluated');
if (!\$blocked instanceof WP_Error || \$blocked->get_error_code() !== 'gama_security_login_rate_limited' || (\$blocked->get_error_data()['status'] ?? null) !== 429) { exit(1); }
\$user = get_user_by('id', (int) '$editor_id');
do_action('wp_login', \$username, \$user);
\$after_clear = apply_filters('authenticate', null, \$username, 'fixture');
if (\$after_clear instanceof WP_Error && \$after_clear->get_error_code() === 'gama_security_login_rate_limited') { exit(1); }
echo 'login-rate-limit-ok';
" | grep -Fx 'login-rate-limit-ok'

echo 'GSWEB-23 Editor capability, headers and login protection checks passed.'
