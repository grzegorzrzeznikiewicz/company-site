#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
backup="$ROOT_DIR/bin/backup"
restore="$ROOT_DIR/bin/restore"

[[ -x "$backup" && -x "$restore" ]]
grep -Fq 'mariadb-dump' "$backup"
grep -Fq 'single-transaction' "$backup"
grep -Fq 'gama-wordpress-uploads' "$backup"
grep -Fq 'SHA256SUMS' "$backup"
grep -Fq 'format_version=1' "$backup"
grep -Fq 'gama-restore-' "$restore"
grep -Fq 'refusing overwrite' "$restore"
grep -Fq 'shasum -a 256 -c SHA256SUMS' "$restore"
grep -Fq 'Uploads archive contains an unsafe path.' "$restore"
grep -Fq 'restore-compose.override.yaml' "$restore"
grep -Fq 'Elapsed seconds:' "$restore"
grep -Fq 'ports: !reset []' "$ROOT_DIR/restore-compose.override.yaml"
if "$restore" --project gama-wordpress --confirm /tmp 2>/dev/null; then
  echo 'Restore accepted the live local project namespace.' >&2
  exit 1
fi

echo 'Backup and isolated full-restore safety contract passed.'
