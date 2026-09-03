#!/usr/bin/env bash
set -euo pipefail

# This test catches drift between the development and disposable package-test
# images, plus accidental ports, fixed volumes, or checkout source mounts.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGE_ZIP="$ROOT_DIR/dist/gama-contact-0.1.0.zip"

resolved="$({ PACKAGE_ZIP="$PACKAGE_ZIP" docker compose \
  --project-name gama-package-contract \
  --file "$ROOT_DIR/tests/package-compose.yaml" \
  config --format json; })"

for image in \
  'mariadb:10.11.18-jammy' \
  'wordpress:7.1.0-php8.4-apache' \
  'wordpress:cli-2.12.0-php8.4'; do
  grep -Fq "\"image\": \"$image\"" <<<"$resolved"
done

if grep -Fq '"ports"' <<<"$resolved"; then
  echo "Disposable package Compose must not publish ports." >&2
  exit 1
fi

if grep -Eq '"source": ".*(theme|plugins)/' <<<"$resolved"; then
  echo "Disposable package Compose must not mount checkout sources." >&2
  exit 1
fi

grep -Fq '"target": "/package/gama-contact.zip"' <<<"$resolved"

if grep -Eq '"external": true|"name": "gama-wordpress' <<<"$resolved"; then
  echo "Disposable package Compose must use only project-scoped volumes." >&2
  exit 1
fi
