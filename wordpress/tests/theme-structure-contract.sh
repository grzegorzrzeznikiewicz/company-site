#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
THEME_DIR="$ROOT_DIR/theme/gama-software"

for slug in index front-page page single home archive search 404; do
  file="$THEME_DIR/templates/$slug.html"
  grep -Fq '<!-- wp:template-part {"slug":"header","theme":"gama-software"} /-->' "$file"
  grep -Fq "gama-template--$slug" "$file"
  [[ "$(grep -Fc '"tagName":"main"' "$file")" -eq 1 ]]
  grep -Fq '<!-- wp:template-part {"slug":"footer","theme":"gama-software"} /-->' "$file"
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
grep -Fq '<!-- wp:search ' "$THEME_DIR/templates/search.html"
grep -Fq '<!-- wp:pattern {"slug":"gama-software/not-found"} /-->' "$THEME_DIR/templates/404.html"

grep -Fq '"className":"gama-site-header"' "$THEME_DIR/parts/header.html"
grep -Fq '<!-- wp:site-logo /-->' "$THEME_DIR/parts/header.html"
grep -Fq '<!-- wp:site-title' "$THEME_DIR/parts/header.html"
grep -Fq '"className":"gama-site-footer"' "$THEME_DIR/parts/footer.html"
if grep -Rq '<!-- wp:navigation' "$THEME_DIR"; then
  echo 'Final navigation belongs to GSWEB-14.' >&2
  exit 1
fi

echo 'Theme structural contract passed.'
