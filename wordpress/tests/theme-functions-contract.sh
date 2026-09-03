#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
file="$ROOT_DIR/theme/gama-software/functions.php"

for token in "load_theme_textdomain" "custom-logo" "post-thumbnails" "wp-block-styles" "responsive-embeds" "editor-styles" "add_editor_style" "wp_enqueue_style" "block_editor_settings_all" "allowed_block_types_all" "activate_plugins" "WP_Block_Editor_Context" "codeEditingEnabled" "core/html"; do
  grep -Fq "$token" "$file"
done

for token in "gama_software_add_navigation_toggle_state" "render_block_core/navigation" "WP_HTML_Tag_Processor" "wp-block-navigation__responsive-container" "wp-block-navigation__responsive-container-open" "aria-controls" "data-wp-bind--aria-expanded" "context.overlayOpenedBy.click"; do
  grep -Fq "$token" "$file"
done

[[ "$(grep -Fc "add_filter( 'render_block_core/navigation', 'gama_software_add_navigation_toggle_state', 10, 3 );" "$file")" -eq 1 ]]

if grep -Eqi 'register_(activation|deactivation)_hook|update_option|add_option|delete_option|wp_insert_post|wp_delete_post|add_cap|remove_cap|get_role|register_nav_menus?|wp_nav_menu' "$file"; then
  echo 'Theme functions must not persist state, mutate roles, seed menus, or own lifecycle hooks.' >&2
  exit 1
fi

if [[ "$(grep -Ec "add_filter\( 'render_block(_core/navigation)?'" "$file")" -ne 1 ]]; then
  echo 'GSWEB-14 permits exactly one narrow Navigation render filter.' >&2
  exit 1
fi

if grep -Eqi 'wp_enqueue_script[[:space:]]*\(|<script|MutationObserver|addEventListener' "$file"; then
  echo 'Core Navigation must remain the only JavaScript and overlay owner.' >&2
  exit 1
fi

echo 'Theme functions contract passed.'
