#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
runtime_url="${GAMA_CONTACT_RUNTIME_URL:-http://localhost:8090}"
mailpit_url="${GAMA_CONTACT_MAILPIT_URL:-http://localhost:8027}"

clear_contact_rate_limits() {
  "$ROOT_DIR/bin/wp" eval 'global $wpdb; foreach (["_transient_gama_contact_rate_", "_transient_timeout_gama_contact_rate_"] as $prefix) { $wpdb->query($wpdb->prepare("DELETE FROM {$wpdb->options} WHERE option_name LIKE %s", $wpdb->esc_like($prefix) . "%")); } delete_option("gama_contact_lock_contract_ready"); delete_option("gama_contact_lock_contract_release");'
}

assert_database_lock_exclusion() {
  "$ROOT_DIR/bin/wp" eval 'global $wpdb; $name="gama-contact-contract"; $release_option="gama_contact_lock_contract_release"; $acquired=$wpdb->get_var($wpdb->prepare("SELECT GET_LOCK(%s, %d)",$name,0)); if ((string)$acquired!=="1") { exit(1); } update_option("gama_contact_lock_contract_ready","1",false); $released=false; for ($attempt=0; $attempt<300; ++$attempt) { $released=(string)$wpdb->get_var($wpdb->prepare("SELECT option_value FROM {$wpdb->options} WHERE option_name=%s",$release_option))==="1"; if ($released) { break; } usleep(100000); } $wpdb->get_var($wpdb->prepare("SELECT RELEASE_LOCK(%s)",$name)); delete_option("gama_contact_lock_contract_ready"); delete_option($release_option); exit($released ? 0 : 2);' &
  local holder_pid=$!
  local ready=false
  for _ in $(seq 1 50); do
    if [[ "$("$ROOT_DIR/bin/wp" option get gama_contact_lock_contract_ready 2>/dev/null || true)" == 1 ]]; then
      ready=true
      break
    fi
    sleep 0.1
  done
  if [[ "$ready" != true ]]; then
    wait "$holder_pid" || true
    echo 'Database lock holder did not become ready.' >&2
    return 1
  fi
  if ! "$ROOT_DIR/bin/wp" eval 'global $wpdb; $result=$wpdb->get_var($wpdb->prepare("SELECT GET_LOCK(%s, %d)","gama-contact-contract",1)); exit((string)$result==="0" ? 0 : 1);'; then
    "$ROOT_DIR/bin/wp" option update gama_contact_lock_contract_release 1 >/dev/null || true
    wait "$holder_pid" || true
    return 1
  fi
  "$ROOT_DIR/bin/wp" option update gama_contact_lock_contract_release 1 >/dev/null
  wait "$holder_pid"
  "$ROOT_DIR/bin/wp" eval 'global $wpdb; $name="gama-contact-contract"; $result=$wpdb->get_var($wpdb->prepare("SELECT GET_LOCK(%s, %d)",$name,0)); if ((string)$result!=="1") { exit(1); } $wpdb->get_var($wpdb->prepare("SELECT RELEASE_LOCK(%s)",$name));'
}

submit_to() {
  local payload="$1"
  local output_file="$2"
  curl --silent --show-error --output "$output_file" --write-out '%{http_code}' \
    --request POST "$runtime_url/?rest_route=/gama-contact/v1/messages" \
    --header "Origin: $runtime_url" \
    --header "X-Gama-Contact-Nonce: $nonce" \
    --header 'Content-Type: application/json' \
    --data "$payload"
}

submit() {
  submit_to "$1" "$response_file"
}

response_file="$(mktemp "${TMPDIR:-/tmp}/gama-contact-response.XXXXXX")"
concurrency_dir=''
cleanup() {
  unlink "$response_file" 2>/dev/null || true
  if [[ -n "$concurrency_dir" && -d "$concurrency_dir" ]]; then
    find "$concurrency_dir" -type f -delete 2>/dev/null || true
    rmdir "$concurrency_dir" 2>/dev/null || true
  fi
  clear_contact_rate_limits >/dev/null 2>&1 || true
}
trap cleanup EXIT

clear_contact_rate_limits
assert_database_lock_exclusion
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
concurrency_dir="$(mktemp -d "${TMPDIR:-/tmp}/gama-contact-concurrency.XXXXXX")"
concurrency_pids=()
for attempt in $(seq 1 12); do
  (submit_to '{"name":"","email":"","phone":"","message":""}' "$concurrency_dir/response-$attempt.json" >"$concurrency_dir/status-$attempt") &
  concurrency_pids+=("$!")
done
for concurrency_pid in "${concurrency_pids[@]}"; do
  wait "$concurrency_pid"
done
[[ "$(grep -lFx 422 "$concurrency_dir"/status-* | wc -l | tr -d ' ')" -eq 5 ]]
[[ "$(grep -lFx 429 "$concurrency_dir"/status-* | wc -l | tr -d ' ')" -eq 7 ]]
grep -Flq 'gama_contact_rate_limited' "$concurrency_dir"/response-*.json
find "$concurrency_dir" -type f -delete
rmdir "$concurrency_dir"
concurrency_dir=''

echo 'Local contact form validation, honeypot, database-lock exclusion, atomic concurrent rate limit and Mailpit delivery passed.'
