#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
plugin="$ROOT_DIR/plugins/gama-mail-transport/gama-mail-transport.php"
assertion="$ROOT_DIR/tests/assert-mail-transport-plugin.php"
compose="$ROOT_DIR/deploy/compose.yaml"
dockerfile="$ROOT_DIR/runtime/Dockerfile"
bootstrap="$ROOT_DIR/bin/bootstrap"
production_deploy="$ROOT_DIR/bin/deploy-production"

for file in "$plugin" "$assertion" "$compose" "$dockerfile" "$bootstrap" "$production_deploy"; do
  [[ -f "$file" ]]
done

docker run --rm --network none \
  --volume "$ROOT_DIR/plugins/gama-mail-transport:/plugin:ro" \
  --volume "$assertion:/assert.php:ro" \
  wordpress:cli-2.12.0-php8.4@sha256:1e1d1485277d15e0331b598b6e19972243128ead978b7134d758097d82116b99 \
  sh -ec 'php -l /plugin/gama-mail-transport.php >/dev/null && php /assert.php'
grep -Fq 'Plugin Name: Gama Mail Transport' "$plugin"
grep -Fq "'production' !== wp_get_environment_type()" "$plugin"
grep -Fq "'phpmailer_init'" "$plugin"
grep -Fq "'pre_wp_mail'" "$plugin"
grep -Fq 'return false;' "$plugin"
grep -Fq 'GAMA_SMTP_HOST' "$plugin"
grep -Fq 'GAMA_SMTP_PORT' "$plugin"
grep -Fq 'GAMA_SMTP_USERNAME' "$plugin"
grep -Fq 'GAMA_SMTP_PASSWORD' "$plugin"
grep -Fq 'GAMA_SMTP_ENCRYPTION' "$plugin"
if grep -Eq 'error_log|trigger_error|var_dump|print_r' "$plugin"; then
  echo 'Mail transport must never log SMTP configuration or credentials.' >&2
  exit 1
fi

for key in GAMA_SMTP_HOST GAMA_SMTP_PORT GAMA_SMTP_USERNAME GAMA_SMTP_PASSWORD GAMA_SMTP_ENCRYPTION; do
  grep -Fq "$key" "$compose"
  grep -Fq "$key" "$production_deploy"
done
grep -Fq 'COPY wordpress/plugins/gama-mail-transport' "$dockerfile"
grep -Fq 'wp_cli plugin activate gama-mail-transport' "$bootstrap"
grep -Fq 'Production SMTP host must be external' "$production_deploy"
grep -Fq 'Production SMTP credentials are required' "$production_deploy"

echo 'Environment-only production SMTP transport contract passed.'
