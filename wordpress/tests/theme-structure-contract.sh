#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
THEME_DIR="$ROOT_DIR/theme/gama-software"

for slug in index front-page page single home archive search 404; do
  file="$THEME_DIR/templates/$slug.html"
  grep -Fq '<!-- wp:template-part {"slug":"header","theme":"gama-software","className":"gama-site-header"} /-->' "$file"
  grep -Fq "gama-template--$slug" "$file"
  [[ "$(grep -Fc '"tagName":"main"' "$file")" -eq 1 ]]
  grep -Fq '<!-- wp:template-part {"slug":"footer","theme":"gama-software","className":"gama-site-footer"} /-->' "$file"
done

for slug in index home archive search; do
  grep -Eq '<!-- wp:query .*"inherit":true' "$THEME_DIR/templates/$slug.html"
  grep -Fq '<!-- wp:query-pagination' "$THEME_DIR/templates/$slug.html"
done
grep -Fq '<!-- wp:post-title {"level":1' "$THEME_DIR/templates/page.html"
grep -Fq '<!-- wp:post-title {"level":1' "$THEME_DIR/templates/single.html"
grep -Fq '<!-- wp:post-featured-image' "$THEME_DIR/templates/single.html"
grep -Fq '<!-- wp:query-title {"type":"archive","level":1' "$THEME_DIR/templates/archive.html"
grep -Fq '<!-- wp:query-title {"type":"search","level":1' "$THEME_DIR/templates/search.html"
grep -Fq '<!-- wp:search {"showLabel":true} /-->' "$THEME_DIR/templates/search.html"
if grep -Eq '"(label|buttonText)"' "$THEME_DIR/templates/search.html"; then
  echo 'Search template hard-codes a label instead of using Core-localized defaults.' >&2
  exit 1
fi
grep -Fq '<!-- wp:pattern {"slug":"gama-software/not-found"} /-->' "$THEME_DIR/templates/404.html"

grep -Fq '"className":"gama-site-header__surface"' "$THEME_DIR/parts/header.html"
grep -Fq '<!-- wp:site-logo {"isLink":true} /-->' "$THEME_DIR/parts/header.html"
grep -Fq '<!-- wp:navigation ' "$THEME_DIR/parts/header.html"
grep -Fq '"className":"gama-site-footer__surface"' "$THEME_DIR/parts/footer.html"
grep -Fq '<!-- wp:site-logo {"isLink":true} /-->' "$THEME_DIR/parts/footer.html"
grep -Fq '<!-- wp:navigation ' "$THEME_DIR/parts/footer.html"

echo 'Theme structural contract passed.'
