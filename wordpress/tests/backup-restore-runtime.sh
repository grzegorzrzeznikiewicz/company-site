#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"
COMPOSE_FILE="$ROOT_DIR/compose.yaml"
project="gama-restore-$RANDOM-$$"
backup_parent="$(mktemp -d "${TMPDIR:-/tmp}/gama-backup-contract.XXXXXX")"
backup="$backup_parent/backup"
marker="GSWEB24-restore-$(date +%s)-$$"
upload_name="$marker.txt"
source_post_id=''

RESTORE_COMPOSE=(docker compose --project-name "$project" --env-file "$ENV_FILE" --file "$COMPOSE_FILE" --file "$ROOT_DIR/restore-compose.override.yaml")
cleanup() {
  local status=$?
  set +e
  "${RESTORE_COMPOSE[@]}" down --volumes --remove-orphans >/dev/null 2>&1
  if [[ -n "$source_post_id" ]]; then
    "$ROOT_DIR/bin/wp" post delete "$source_post_id" --force >/dev/null 2>&1
  fi
  "$ROOT_DIR/bin/wp" eval "\$uploads=wp_upload_dir(); \$path=\$uploads['basedir'].'/$upload_name'; if (is_file(\$path)) { unlink(\$path); }" >/dev/null 2>&1
  if [[ -d "$backup_parent" && ! -L "$backup_parent" ]]; then
    find "$backup_parent" -type f -delete 2>/dev/null
    find "$backup_parent" -depth -type d -exec rmdir {} \; 2>/dev/null
  fi
  set -e
  trap - EXIT
  exit "$status"
}
trap cleanup EXIT

source_post_id="$("$ROOT_DIR/bin/wp" post create --post_type=page --post_status=publish --post_title="$marker" --post_content="$marker" --porcelain | tail -n 1)"
[[ "$source_post_id" =~ ^[1-9][0-9]*$ ]]
source_upload_sha="$("$ROOT_DIR/bin/wp" eval "\$uploads=wp_upload_dir(); \$path=\$uploads['basedir'].'/$upload_name'; file_put_contents(\$path,'$marker'); echo hash_file('sha256',\$path);" | tail -n 1)"
[[ "$source_upload_sha" =~ ^[a-f0-9]{64}$ ]]

backup_output="$("$ROOT_DIR/bin/backup" "$backup")"
grep -Fq "Backup created: $backup" <<<"$backup_output"
[[ "$(stat -f '%Lp' "$backup" 2>/dev/null || stat -c '%a' "$backup")" == 700 ]]

restore_output="$("$ROOT_DIR/bin/restore" --project "$project" --confirm "$backup")"
grep -Fq "Restore completed: $project" <<<"$restore_output"
elapsed="$(sed -n 's/^Elapsed seconds: //p' <<<"$restore_output")"
[[ "$elapsed" =~ ^[0-9]+$ && "$elapsed" -le 180 ]]

restored_post_id="$("${RESTORE_COMPOSE[@]}" run --rm --no-deps --entrypoint wp wp post list --post_type=page --search="$marker" --field=ID --allow-root | tail -n 1)"
[[ "$restored_post_id" == "$source_post_id" ]]
restored_upload_sha="$("${RESTORE_COMPOSE[@]}" run --rm --no-deps --entrypoint wp wp eval "\$uploads=wp_upload_dir(); echo hash_file('sha256',\$uploads['basedir'].'/$upload_name');" --allow-root | tail -n 1)"
[[ "$restored_upload_sha" == "$source_upload_sha" ]]

echo "Full isolated database/uploads restore passed in ${elapsed}s for artifact commit $(sed -n 's/^git_commit=//p' "$backup/manifest.txt")."
