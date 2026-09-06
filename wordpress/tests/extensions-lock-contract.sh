#!/usr/bin/env bash
set -euo pipefail

# This test catches an extension inventory whose validator accepts fields that
# the versioned schema does not declare, or silently accepts wrong field types.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fixture_dir="$(mktemp -d "${TMPDIR:-/tmp}/gama-extensions-lock.XXXXXX")"
valid_fixture="$ROOT_DIR/tests/fixtures/extensions-lock.valid.json"

cleanup() {
  find "$fixture_dir" -type f -delete
  rmdir "$fixture_dir"
}
trap cleanup EXIT

"$ROOT_DIR/bin/validate-extensions-lock"
"$ROOT_DIR/bin/validate-extensions-lock" "$valid_fixture"

assert_rejected() {
  local name="$1"
  local document="$2"
  local path="$fixture_dir/$name.json"
  local output

  printf '%s\n' "$document" >"$path"
  if output="$("$ROOT_DIR/bin/validate-extensions-lock" "$path" 2>&1)"; then
    echo "Validator accepted invalid fixture: $name" >&2
    exit 1
  fi
  if grep -Fq 'Extension lock validation failed: /input/extensions.lock.json:' <<<"$output"; then
    printf 'Invalid fixture is malformed JSON instead of a focused schema mutation: %s\n%s\n' "$name" "$output" >&2
    exit 1
  fi
}

valid_extension='{"type":"plugin","slug":"example-extension","version":"1.2.3","source":"https://downloads.example.test/example.zip","sha256":"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef","license":"GPL-2.0-or-later","requires":{"wordpress":"7.1","php":"8.4"},"purpose":"Fixture","decision":"GSWEB-23"}'

assert_rejected missing-version '{"extensions":[]}'
assert_rejected missing-extensions '{"version":1}'
assert_rejected unknown-top-level '{"version":1,"extensions":[],"unexpected":true}'
assert_rejected wrong-version-const '{"version":2,"extensions":[]}'
assert_rejected wrong-version-type '{"version":"1","extensions":[]}'
assert_rejected wrong-extensions-type '{"version":1,"extensions":"none"}'
assert_rejected wrong-item-type '{"version":1,"extensions":[false]}'

assert_rejected missing-type '{"version":1,"extensions":[{"slug":"example-extension","version":"1.2.3","source":"https://downloads.example.test/example.zip","sha256":"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef","license":"GPL-2.0-or-later","requires":{"wordpress":"7.1","php":"8.4"},"purpose":"Fixture","decision":"GSWEB-23"}]}'
assert_rejected missing-slug '{"version":1,"extensions":[{"type":"plugin","version":"1.2.3","source":"https://downloads.example.test/example.zip","sha256":"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef","license":"GPL-2.0-or-later","requires":{"wordpress":"7.1","php":"8.4"},"purpose":"Fixture","decision":"GSWEB-23"}]}'
assert_rejected missing-extension-version '{"version":1,"extensions":[{"type":"plugin","slug":"example-extension","source":"https://downloads.example.test/example.zip","sha256":"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef","license":"GPL-2.0-or-later","requires":{"wordpress":"7.1","php":"8.4"},"purpose":"Fixture","decision":"GSWEB-23"}]}'
assert_rejected missing-source '{"version":1,"extensions":[{"type":"plugin","slug":"example-extension","version":"1.2.3","sha256":"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef","license":"GPL-2.0-or-later","requires":{"wordpress":"7.1","php":"8.4"},"purpose":"Fixture","decision":"GSWEB-23"}]}'
assert_rejected missing-sha256 '{"version":1,"extensions":[{"type":"plugin","slug":"example-extension","version":"1.2.3","source":"https://downloads.example.test/example.zip","license":"GPL-2.0-or-later","requires":{"wordpress":"7.1","php":"8.4"},"purpose":"Fixture","decision":"GSWEB-23"}]}'
assert_rejected missing-license '{"version":1,"extensions":[{"type":"plugin","slug":"example-extension","version":"1.2.3","source":"https://downloads.example.test/example.zip","sha256":"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef","requires":{"wordpress":"7.1","php":"8.4"},"purpose":"Fixture","decision":"GSWEB-23"}]}'
assert_rejected missing-requires '{"version":1,"extensions":[{"type":"plugin","slug":"example-extension","version":"1.2.3","source":"https://downloads.example.test/example.zip","sha256":"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef","license":"GPL-2.0-or-later","purpose":"Fixture","decision":"GSWEB-23"}]}'
assert_rejected missing-purpose '{"version":1,"extensions":[{"type":"plugin","slug":"example-extension","version":"1.2.3","source":"https://downloads.example.test/example.zip","sha256":"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef","license":"GPL-2.0-or-later","requires":{"wordpress":"7.1","php":"8.4"},"decision":"GSWEB-23"}]}'
assert_rejected missing-decision '{"version":1,"extensions":[{"type":"plugin","slug":"example-extension","version":"1.2.3","source":"https://downloads.example.test/example.zip","sha256":"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef","license":"GPL-2.0-or-later","requires":{"wordpress":"7.1","php":"8.4"},"purpose":"Fixture"}]}'

assert_rejected wrong-type-type '{"version":1,"extensions":[{"type":1,"slug":"example-extension","version":"1.2.3","source":"https://downloads.example.test/example.zip","sha256":"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef","license":"GPL-2.0-or-later","requires":{"wordpress":"7.1","php":"8.4"},"purpose":"Fixture","decision":"GSWEB-23"}]}'
assert_rejected wrong-type-enum "{\"version\":1,\"extensions\":[${valid_extension/\"type\":\"plugin\"/\"type\":\"module\"}]}"
assert_rejected wrong-slug-type "{\"version\":1,\"extensions\":[${valid_extension/\"slug\":\"example-extension\"/\"slug\":7}]}"
assert_rejected wrong-slug-pattern "{\"version\":1,\"extensions\":[${valid_extension/\"slug\":\"example-extension\"/\"slug\":\"Example_extension\"}]}"
assert_rejected wrong-extension-version-type "{\"version\":1,\"extensions\":[${valid_extension/\"version\":\"1.2.3\"/\"version\":123}]}"
assert_rejected empty-extension-version "{\"version\":1,\"extensions\":[${valid_extension/\"version\":\"1.2.3\"/\"version\":\"\"}]}"
assert_rejected wrong-source-type "{\"version\":1,\"extensions\":[${valid_extension/\"source\":\"https:\/\/downloads.example.test\/example.zip\"/\"source\":false}]}"
assert_rejected non-http-source "{\"version\":1,\"extensions\":[${valid_extension/https:\/\/downloads.example.test/ftp:\/\/downloads.example.test}]}"
assert_rejected wrong-sha256-type "{\"version\":1,\"extensions\":[${valid_extension/\"sha256\":\"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef\"/\"sha256\":64}]}"
assert_rejected wrong-sha256-pattern "{\"version\":1,\"extensions\":[${valid_extension/0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef/ABCDEF}]}"
assert_rejected wrong-license-type "{\"version\":1,\"extensions\":[${valid_extension/\"license\":\"GPL-2.0-or-later\"/\"license\":false}]}"
assert_rejected empty-license "{\"version\":1,\"extensions\":[${valid_extension/\"license\":\"GPL-2.0-or-later\"/\"license\":\"\"}]}"
assert_rejected wrong-requires-type '{"version":1,"extensions":[{"type":"plugin","slug":"example-extension","version":"1.2.3","source":"https://downloads.example.test/example.zip","sha256":"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef","license":"GPL-2.0-or-later","requires":[],"purpose":"Fixture","decision":"GSWEB-23"}]}'
assert_rejected missing-wordpress "{\"version\":1,\"extensions\":[${valid_extension/\"wordpress\":\"7.1\",/}]}"
assert_rejected missing-php "{\"version\":1,\"extensions\":[${valid_extension/,\"php\":\"8.4\"/}]}"
assert_rejected wrong-wordpress-type "{\"version\":1,\"extensions\":[${valid_extension/\"wordpress\":\"7.1\"/\"wordpress\":71}]}"
assert_rejected empty-wordpress "{\"version\":1,\"extensions\":[${valid_extension/\"wordpress\":\"7.1\"/\"wordpress\":\"\"}]}"
assert_rejected wrong-php-type "{\"version\":1,\"extensions\":[${valid_extension/\"php\":\"8.4\"/\"php\":84}]}"
assert_rejected empty-php "{\"version\":1,\"extensions\":[${valid_extension/\"php\":\"8.4\"/\"php\":\"\"}]}"
assert_rejected unknown-requires-field "{\"version\":1,\"extensions\":[${valid_extension/\"php\":\"8.4\"/\"php\":\"8.4\",\"cms\":\"wordpress\"}]}"
assert_rejected wrong-purpose-type "{\"version\":1,\"extensions\":[${valid_extension/\"purpose\":\"Fixture\"/\"purpose\":false}]}"
assert_rejected empty-purpose "{\"version\":1,\"extensions\":[${valid_extension/\"purpose\":\"Fixture\"/\"purpose\":\"\"}]}"
assert_rejected wrong-decision-type "{\"version\":1,\"extensions\":[${valid_extension/\"decision\":\"GSWEB-23\"/\"decision\":23}]}"
assert_rejected wrong-decision-pattern "{\"version\":1,\"extensions\":[${valid_extension/GSWEB-23/gsweb-23}]}"
assert_rejected unknown-extension-field "{\"version\":1,\"extensions\":[${valid_extension%?},\"unexpected\":true}]}"
