#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
file="$ROOT_DIR/theme/gama-software/functions.php"

for token in "load_theme_textdomain" "custom-logo" "post-thumbnails" "wp-block-styles" "responsive-embeds" "editor-styles" "add_editor_style" "wp_enqueue_style" "block_editor_settings_all" "allowed_block_types_all" "activate_plugins" "WP_Block_Editor_Context" "codeEditingEnabled" "core/html"; do
  grep -Fq "$token" "$file"
done

if grep -Eqi 'register_(activation|deactivation)_hook|update_option|add_option|delete_option|wp_insert_post|wp_delete_post' "$file"; then
  echo 'Theme functions must not persist state or own lifecycle hooks.' >&2
  exit 1
fi

echo 'Theme functions contract passed.'
