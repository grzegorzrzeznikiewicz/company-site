#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
runtime_url="${GAMA_SEO_RUNTIME_URL:-http://localhost:8090}"
fixture_dir="$(mktemp -d "${TMPDIR:-/tmp}/gama-seo-runtime.XXXXXX")"

cleanup() {
  find "$fixture_dir" -type f -delete 2>/dev/null || true
  find "$fixture_dir" -depth -type d -exec rmdir {} \; 2>/dev/null || true
}
trap cleanup EXIT

home_file="$fixture_dir/home.html"
home_status="$(curl --silent --show-error --output "$home_file" --write-out '%{http_code}' "$runtime_url/")"
[[ "$home_status" == 200 ]]
home_html="$(<"$home_file")"

[[ "$(grep -Foc '<link rel="canonical"' <<<"$home_html")" -eq 1 ]]
[[ "$(grep -Foc '<meta name="description"' <<<"$home_html")" -eq 1 ]]
[[ "$(grep -Foc '<meta property="og:title"' <<<"$home_html")" -eq 1 ]]
[[ "$(grep -Foc '<script type="application/ld+json">' <<<"$home_html")" -eq 1 ]]
grep -Fq '<html lang="pl-PL"' <<<"$home_html"
grep -Eq "<meta name=(\"|')robots\\1 content=(\"|')noindex" <<<"$home_html"
grep -Fq 'rel="icon"' <<<"$home_html"

robots_file="$fixture_dir/robots.txt"
robots_status="$(curl --silent --show-error --output "$robots_file" --write-out '%{http_code}' "$runtime_url/robots.txt")"
[[ "$robots_status" == 200 ]]
grep -Fxq 'Disallow: /' "$robots_file"

redirect_headers="$fixture_dir/sitemap-redirect.headers"
redirect_status="$(curl --silent --show-error --output /dev/null --dump-header "$redirect_headers" --write-out '%{http_code}' "$runtime_url/sitemap.xml")"
[[ "$redirect_status" == 301 ]]
grep -Eiq '^Location: .*/wp-sitemap\.xml\r?$' "$redirect_headers"

sitemap_file="$fixture_dir/sitemap.xml"
sitemap_status="$(curl --silent --show-error --output "$sitemap_file" --write-out '%{http_code}' "$runtime_url/wp-sitemap.xml")"
[[ "$sitemap_status" == 200 ]]
grep -Fq '<sitemapindex' "$sitemap_file"

missing_status="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' "$runtime_url/__gsweb22_missing_path__")"
[[ "$missing_status" == 404 ]]

production_robots="$("$ROOT_DIR/bin/_compose" run --rm --env WP_ENVIRONMENT_TYPE=production --entrypoint wp wp --path=/var/www/html --allow-root eval '$robots=apply_filters("wp_robots", []); ksort($robots); echo wp_json_encode($robots);' | tail -n 1)"
[[ "$production_robots" == '{"follow":true,"index":true,"max-image-preview:large":true}' ]]

echo 'GSWEB-22 SEO, robots, sitemap, canonical and 404 runtime checks passed.'
