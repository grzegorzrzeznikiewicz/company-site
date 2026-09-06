#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
THEME_DIR="$ROOT_DIR/theme/gama-software"
fixture_dir="$(mktemp -d "${TMPDIR:-/tmp}/gama-theme-i18n.XXXXXX")"
trap 'find "$fixture_dir" -type f -delete; find "$fixture_dir" -depth -type d -exec rmdir {} \;' EXIT
mkdir -p "$fixture_dir/first" "$fixture_dir/second"
chmod 0777 "$fixture_dir/first" "$fixture_dir/second"

generate_pot() {
  local output_dir="$1"
  docker run --rm --network none \
    --volume "$THEME_DIR:/theme:ro" \
    --volume "$ROOT_DIR/qa/schema:/schema:ro" \
    --volume "$output_dir:/output" \
    gama-theme-qa:gsweb12 php /qa/extract-theme-json-i18n.php \
      /theme/theme.json /schema/wp-7.1-theme-i18n.json /output/theme-json.pot
  docker run --rm --network none \
    --env TZ=UTC --env LC_ALL=C \
    --volume "$THEME_DIR:/theme:ro" \
    --volume "$output_dir:/output" \
    wordpress:cli-2.12.0-php8.4@sha256:1e1d1485277d15e0331b598b6e19972243128ead978b7134d758097d82116b99 \
    wp i18n make-pot /theme /output/gama-software.pot \
      --domain=gama-software \
      --exclude=languages \
      --merge=/output/theme-json.pot \
      --headers='{"POT-Creation-Date":"","Report-Msgid-Bugs-To":"https://gamasoftware.com/"}' \
      --file-comment='Copyright (C) 2026 Gama Software'
}

(cd "$ROOT_DIR/qa/schema" && shasum -a 256 -c wp-7.1-theme-i18n.json.sha256)
docker build \
  --tag gama-theme-qa:gsweb12 --file "$ROOT_DIR/qa/Dockerfile" "$ROOT_DIR/.." >/dev/null
generate_pot "$fixture_dir/first"
generate_pot "$fixture_dir/second"
cmp "$fixture_dir/first/gama-software.pot" "$fixture_dir/second/gama-software.pot"
generated_pot="$fixture_dir/first/gama-software.pot"
for context_message in \
  'Template part name|Header' \
  'Template part name|Footer' \
  'Color name|Base' \
  'Color name|Muted card text' \
  'Color name|Accent' \
  'Font family name|System sans' \
  'Font size name|Body' \
  'Font size name|Display large' \
  'Space size name|Medium' \
  'Space size name|Section' \
  'Shadow name|Elevation 1' \
  'Shadow name|Elevation 3'; do
  context="${context_message%%|*}"
  message="${context_message#*|}"
  grep -B1 -F "msgid \"$message\"" "$generated_pot" | grep -Fq "msgctxt \"$context\""
done
grep -Fq 'msgid "Page not found"' "$generated_pot"
grep -Fq 'msgid "Gama Software Hero"' "$generated_pot"
grep -Fq 'msgid "Poznaj nasze usługi"' "$generated_pot"
grep -Fq 'msgid "Gama Software Services"' "$generated_pot"
grep -Fq 'msgid "Nasze Usługi"' "$generated_pot"
grep -Fq 'msgid "Wdrożenia E-commerce"' "$generated_pot"
grep -Fq 'msgid "Konsultacje E-commerce"' "$generated_pot"
grep -Fq 'msgid "Agenci AI"' "$generated_pot"
grep -Fq 'msgid "Gama Software Modules"' "$generated_pot"
grep -Fq 'msgid "Moduły Magento 2"' "$generated_pot"
grep -Fq 'msgid "Zapisz się na listę oczekujących"' "$generated_pot"
grep -Fq 'msgid "Advanced SEO Suite"' "$generated_pot"
grep -Fq 'msgid "Monitoring wydajności"' "$generated_pot"
grep -Fq 'msgid "Gama Software Article Starter"' "$generated_pot"
grep -Fq 'msgid "Pierwsza część artykułu"' "$generated_pot"
grep -Fq 'msgid "Gama Software Contact"' "$generated_pot"
grep -Fq 'msgid "Formularz jest chwilowo niedostępny. Napisz do nas:"' "$generated_pot"
grep -Fq '"POT-Creation-Date: \n"' "$generated_pot"
cmp "$generated_pot" "$THEME_DIR/languages/gama-software.pot"

echo 'Deterministic WP-CLI POT contract passed.'
