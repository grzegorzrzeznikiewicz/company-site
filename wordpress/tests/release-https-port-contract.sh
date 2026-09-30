#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
runtime="$ROOT_DIR/tests/release-https-runtime.sh"
image='wordpress:7.1.0-php8.4-apache@sha256:b8f37de278183840a09f5a4b5bf5ec9f09177a9984d2fe5cc072b4388128bd9d'
suffix="$RANDOM-$$"
unbound_container="gama-release-https-port-empty-$suffix"
bound_container="gama-release-https-port-bound-$suffix"
missing_container="gama-release-https-port-missing-$suffix"
fixture="$(mktemp -d "${TMPDIR:-/tmp}/gama-release-https-port-contract.XXXXXX")"

cleanup() {
  local status=$?
  trap - EXIT
  set +e
  docker rm --force "$unbound_container" "$bound_container" >/dev/null 2>&1
  find "$fixture" -type f -delete 2>/dev/null
  find "$fixture" -depth -type d -exec rmdir {} \; 2>/dev/null
  set -e
  exit "$status"
}
trap cleanup EXIT

docker create --name "$unbound_container" --network none "$image" >/dev/null
docker create --name "$bound_container" --publish '127.0.0.1::443' "$image" >/dev/null
docker start "$bound_container" >/dev/null

# The runtime is sourceable so this contract calls its real validation function.
# Sourcing must not start the HTTPS lifecycle.
source "$runtime"

empty_bindings="$(docker inspect --format '{{json .HostConfig.PortBindings}}' "$unbound_container")"
nonempty_bindings="$(docker inspect --format '{{json .HostConfig.PortBindings}}' "$bound_container")"
published_endpoint="$(docker port "$bound_container" 443/tcp)"
[[ "$published_endpoint" =~ ^127\.0\.0\.1:[0-9]+$ ]]
assert_no_published_ports "$unbound_container"

if assert_no_published_ports "$bound_container" >"$fixture/nonempty.stdout" 2>"$fixture/nonempty.stderr"; then
  echo 'HTTPS port validation accepted a real nonempty publication configuration.' >&2
  exit 1
fi
grep -Fq 'must not publish host ports' "$fixture/nonempty.stderr"

if assert_no_published_ports "$missing_container" >"$fixture/missing.stdout" 2>"$fixture/missing.stderr"; then
  echo 'HTTPS port validation treated a failed inspection as empty.' >&2
  exit 1
fi
grep -Fq 'could not inspect sidecar port bindings' "$fixture/missing.stderr"

# Older engines may serialize the same empty map as null. This supplements the
# real Docker cases above without replacing them with a copied equality test.
(
  docker() {
    printf '%s\n' null
  }
  assert_no_published_ports gama-release-https-port-null-fixture
)

printf 'GSWEB-27 HTTPS port contract passed: empty=%s nonempty=%s loopback=%s missing=fail-closed null=accepted.\n' \
  "$empty_bindings" "$nonempty_bindings" "$published_endpoint"
