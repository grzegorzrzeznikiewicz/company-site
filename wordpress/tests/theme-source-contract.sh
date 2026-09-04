#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
THEME_DIR="$ROOT_DIR/theme/gama-software"
fixture_dir="$(mktemp -d "${TMPDIR:-/tmp}/gama-theme-source.XXXXXX")"
trap 'find "$fixture_dir" -type f -delete; find "$fixture_dir" -depth -type d -exec rmdir {} \;' EXIT

cat >"$fixture_dir/expected.txt" <<'EOF'
CHANGELOG.md
LICENSE
README.md
assets/icons/module-package.svg
assets/icons/service-ai.svg
assets/icons/service-consulting.svg
assets/icons/service-ecommerce.svg
assets/images/gama-software-logo.png
functions.php
languages/gama-software.pot
parts/footer.html
parts/header.html
patterns/article.php
patterns/contact.php
patterns/hero.php
patterns/modules.php
patterns/not-found.php
patterns/services.php
style.css
templates/404.html
templates/archive.html
templates/front-page.html
templates/home.html
templates/index.html
templates/page.html
templates/search.html
templates/single.html
theme.json
EOF
(cd "$THEME_DIR" && find . -type f -print | sed 's#^\./##' | LC_ALL=C sort) >"$fixture_dir/actual.txt"
diff -u "$fixture_dir/expected.txt" "$fixture_dir/actual.txt"

while IFS= read -r metadata; do
  grep -Fq "$metadata" "$THEME_DIR/style.css"
done <<'EOF'
Theme Name: Gama Software
Author: Gama Software
Version: 0.4.0
Requires at least: 7.1
Requires PHP: 8.4
License: GPL v2 or later
License URI: https://www.gnu.org/licenses/gpl-2.0.html
Text Domain: gama-software
Domain Path: /languages
EOF

grep -Fq '## 0.4.0 ' "$THEME_DIR/CHANGELOG.md"
grep -Fq 'gama-software' "$THEME_DIR/README.md"
[[ "$(wc -c <"$THEME_DIR/LICENSE" | tr -d ' ')" -ge 15000 ]]
grep -Fq 'GNU GENERAL PUBLIC LICENSE' "$THEME_DIR/LICENSE"

if grep -ERni --include='*.php' --include='*.html' --include='*.json' \
  'wp_mail|register_rest_route|register_post_type|register_taxonomy|add_role|add_cap|remove_cap|get_role|wp_schedule|rel_canonical|wp_sitemaps?|sitemap_(index|url)|og:|application/ld\+json|noindex' "$THEME_DIR"; then
  echo 'Theme contains forbidden business, SEO, role, scheduling, or plugin behavior.' >&2
  exit 1
fi

echo 'Theme source boundary contract passed.'
