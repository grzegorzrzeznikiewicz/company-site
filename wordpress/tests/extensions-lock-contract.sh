#!/usr/bin/env bash
set -euo pipefail

# This test catches an extension inventory whose validator accepts fields that
# the versioned schema does not declare, or silently accepts wrong field types.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fixture_dir="$(mktemp -d "${TMPDIR:-/tmp}/gama-extensions-lock.XXXXXX")"

cleanup() {
  find "$fixture_dir" -type f -delete
  rmdir "$fixture_dir"
}
trap cleanup EXIT

"$ROOT_DIR/bin/validate-extensions-lock"

printf '%s\n' '{"version":1,"extensions":[],"unexpected":true}' >"$fixture_dir/unknown.json"
if "$ROOT_DIR/bin/validate-extensions-lock" "$fixture_dir/unknown.json"; then
  echo "Validator accepted an unknown top-level field." >&2
  exit 1
fi

printf '%s\n' '{"version":"1","extensions":[]}' >"$fixture_dir/wrong-version-type.json"
if "$ROOT_DIR/bin/validate-extensions-lock" "$fixture_dir/wrong-version-type.json"; then
  echo "Validator accepted a mistyped version field." >&2
  exit 1
fi

printf '%s\n' '{"version":1,"extensions":"none"}' >"$fixture_dir/wrong-extensions-type.json"
if "$ROOT_DIR/bin/validate-extensions-lock" "$fixture_dir/wrong-extensions-type.json"; then
  echo "Validator accepted a mistyped extensions field." >&2
  exit 1
fi
