#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
runtime_url="${GAMA_CONTACT_RUNTIME_URL:-http://localhost:8090}"
mailpit_url="${GAMA_CONTACT_MAILPIT_URL:-http://localhost:8027}"

clear_contact_rate_limits() {
  "$ROOT_DIR/bin/wp" eval 'global $wpdb; $wpdb->query($wpdb->prepare("DELETE FROM {$wpdb->options} WHERE option_name LIKE %s", $wpdb->esc_like("_transient_gama_contact_rate_") . "%")); $wpdb->query($wpdb->prepare("DELETE FROM {$wpdb->options} WHERE option_name LIKE %s", $wpdb->esc_like("_transient_timeout_gama_contact_rate_") . "%"));'
}

submit() {
  local payload="$1"
  curl --silent --show-error --output "$response_file" --write-out '%{http_code}' \
    --request POST "$runtime_url/?rest_route=/gama-contact/v1/messages" \
    --header "Origin: $runtime_url" \
    --header "X-Gama-Contact-Nonce: $nonce" \
    --header 'Content-Type: application/json' \
    --data "$payload"
}

response_file="$(mktemp "${TMPDIR:-/tmp}/gama-contact-response.XXXXXX")"
trap 'unlink "$response_file" 2>/dev/null || true; clear_contact_rate_limits >/dev/null 2>&1 || true' EXIT

clear_contact_rate_limits
nonce="$("$ROOT_DIR/bin/wp" eval 'echo wp_create_nonce("gama_contact_submit");' | tail -n 1)"
[[ "$nonce" =~ ^[A-Za-z0-9]+$ ]]

invalid_status="$(submit '{"name":"Jan","email":"bad","phone":"","message":""}')"
[[ "$invalid_status" == 422 ]]
grep -Fq 'field_errors' "$response_file"
grep -Fq 'email' "$response_file"
grep -Fq 'phone' "$response_file"
grep -Fq 'message' "$response_file"

honeypot_marker="GSWEB20-honeypot-$(date +%s)-$$"
honeypot_status="$(submit "{\"name\":\"Bot\",\"email\":\"bot@example.test\",\"phone\":\"123456789\",\"message\":\"$honeypot_marker\",\"company\":\"spam\"}")"
[[ "$honeypot_status" == 200 ]]
if curl --fail --silent --show-error "$mailpit_url/api/v1/messages" | grep -Fq "$honeypot_marker"; then
  echo 'Honeypot submission unexpectedly reached Mailpit.' >&2
  exit 1
fi

delivery_marker="GSWEB20-delivery-$(date +%s)-$$"
delivery_status="$(submit "{\"name\":\"Jan Kowalski\",\"email\":\"jan@example.test\",\"phone\":\"+48 500 600 700\",\"message\":\"$delivery_marker\"}")"
[[ "$delivery_status" == 200 ]]
grep -Fq 'Wiadomo' "$response_file"
curl --fail --silent --show-error "$mailpit_url/api/v1/messages" | grep -Fq "$delivery_marker"

clear_contact_rate_limits
for attempt in 1 2 3 4 5; do
  [[ "$(submit '{"name":"","email":"","phone":"","message":""}')" == 422 ]]
done
[[ "$(submit '{"name":"","email":"","phone":"","message":""}')" == 429 ]]
grep -Fq 'gama_contact_rate_limited' "$response_file"

echo 'Local contact form validation, honeypot, rate limit and Mailpit delivery passed.'
