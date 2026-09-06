#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fixture_dir="$(mktemp -d "${TMPDIR:-/tmp}/gama-release-evidence-contract.XXXXXX")"
expected_image='wordpress:7.1.0-php8.4-apache@sha256:b8f37de278183840a09f5a4b5bf5ec9f09177a9984d2fe5cc072b4388128bd9d'
failures=0

cleanup() {
  find "$fixture_dir" -type l -delete
  find "$fixture_dir" -type f -delete
  find "$fixture_dir" -depth -type d -exec rmdir {} \;
}
trap cleanup EXIT

fail() {
  echo "$1" >&2
  failures=$((failures + 1))
}

assert_status() {
  local name="$1"
  local expected="$2"
  local actual="$3"

  if [[ "$actual" -ne "$expected" ]]; then
    fail "$name returned $actual; expected $expected."
  fi
}

mkdir -p "$fixture_dir/bin" "$fixture_dir/source" "$fixture_dir/wordpress/tests/lib" "$fixture_dir/wordpress/qa"
printf '%s\n' 'known non-secret release evidence' >"$fixture_dir/source/evidence.txt"
cp "$ROOT_DIR/tests/release-regression-runtime.sh" "$fixture_dir/wordpress/tests/"
cp "$ROOT_DIR/tests/release-acceptance-runtime.sh" "$fixture_dir/wordpress/tests/"
if [[ -f "$ROOT_DIR/tests/lib/release-evidence.sh" ]]; then
  cp "$ROOT_DIR/tests/lib/release-evidence.sh" "$fixture_dir/wordpress/tests/lib/"
fi
printf '%s\n' \
  '#!/usr/bin/env bash' \
  'exit "${GAMA_FAKE_PRIMARY_STATUS:-0}"' \
  >"$fixture_dir/wordpress/tests/release-https-runtime.sh"
chmod +x "$fixture_dir/wordpress/tests/"*.sh

cat >"$fixture_dir/bin/docker" <<'EOF'
#!/usr/bin/env bash
set -u

printf '%s\n' "$*" >>"$GAMA_FAKE_DOCKER_LOG"

if [[ "$1 ${2:-}" == 'network inspect' && "${GAMA_FAKE_SETUP_STATUS:-0}" -ne 0 ]]; then
  exit "$GAMA_FAKE_SETUP_STATUS"
fi
if [[ "$1 ${2:-}" == 'volume inspect' ]]; then
  [[ -f "$GAMA_FAKE_DOCKER_STATE" ]]
  exit
fi
if [[ "$1 ${2:-}" == 'volume create' ]]; then
  : >"$GAMA_FAKE_DOCKER_STATE"
  exit 0
fi
if [[ "$1 ${2:-}" == 'volume rm' ]]; then
  if [[ "${GAMA_FAKE_REMOVE_STATUS:-0}" -ne 0 ]]; then
    exit "$GAMA_FAKE_REMOVE_STATUS"
  fi
  unlink "$GAMA_FAKE_DOCKER_STATE"
  exit 0
fi
if [[ "$1" == run && " $* " == *' --entrypoint tar '* ]]; then
  if [[ "${GAMA_FAKE_EXPORT_STATUS:-0}" -ne 0 ]]; then
    printf '%s' 'incomplete'
    exit "$GAMA_FAKE_EXPORT_STATUS"
  fi
  if [[ -n "${GAMA_FAKE_FINAL_DESTINATION:-}" ]]; then
    mkdir "$GAMA_FAKE_FINAL_DESTINATION"
    printf '%s' 'keep-directory-content' >"$GAMA_FAKE_FINAL_DESTINATION/content"
  fi
  tar -C "$GAMA_FAKE_EXPORT_SOURCE" -cf - .
  exit
fi
if [[ "$1" == run && " $* " == *' --entrypoint sh '* ]]; then
  if [[ "${GAMA_FAKE_DROP_VOLUME_BEFORE_CLEANUP:-0}" -eq 1 ]]; then
    unlink "$GAMA_FAKE_DOCKER_STATE"
  fi
  exit 0
fi
if [[ "$1" == run && " $* " == *' npm test '* ]]; then
  exit "${GAMA_FAKE_PRIMARY_STATUS:-0}"
fi
exit 0
EOF
chmod +x "$fixture_dir/bin/docker"

cat >"$fixture_dir/bin/ln" <<'EOF'
#!/usr/bin/env bash
if [[ "${GAMA_FAKE_PROMOTION_STATUS:-0}" -ne 0 ]]; then
  exit "$GAMA_FAKE_PROMOTION_STATUS"
fi
exec /bin/ln "$@"
EOF
cat >"$fixture_dir/bin/mv" <<'EOF'
#!/usr/bin/env bash
if [[ "${GAMA_FAKE_PROMOTION_STATUS:-0}" -ne 0 ]]; then
  exit "$GAMA_FAKE_PROMOTION_STATUS"
fi
exec /bin/mv "$@"
EOF
chmod +x "$fixture_dir/bin/ln" "$fixture_dir/bin/mv"

run_wrapper() {
  local wrapper="$1"
  local name="$2"
  local case_dir="$fixture_dir/$name"
  local status

  mkdir -p "$case_dir/artifacts"
  : >"$case_dir/docker.log"
  set +e
  PATH="$fixture_dir/bin:$PATH" \
    GAMA_FAKE_DOCKER_LOG="$case_dir/docker.log" \
    GAMA_FAKE_DOCKER_STATE="$case_dir/volume" \
    GAMA_FAKE_EXPORT_SOURCE="$fixture_dir/source" \
    GAMA_STAGING_PROJECT=gama-wp-staging-contract \
    GAMA_RELEASE_ARTIFACT_ROOT="$case_dir/artifacts" \
    "${@:3}" \
    "$fixture_dir/wordpress/tests/$wrapper.sh" \
    >"$case_dir/stdout" 2>"$case_dir/stderr"
  status=$?
  set -e
  printf '%s' "$status"
}

archive_path() {
  local wrapper="$1"
  local case_dir="$2"

  if [[ "$wrapper" == release-regression-runtime ]]; then
    printf '%s/artifacts/gama-wp-staging-contract-browser-artifacts.tar' "$case_dir"
  else
    printf '%s/artifacts/gama-wp-staging-contract-acceptance-artifacts.tar' "$case_dir"
  fi
}

for wrapper in release-regression-runtime release-acceptance-runtime; do
  case_name="$wrapper-success"
  status="$(run_wrapper "$wrapper" "$case_name" env)"
  case_dir="$fixture_dir/$case_name"
  archive="$(archive_path "$wrapper" "$case_dir")"
  assert_status "$case_name" 0 "$status"
  if [[ ! -s "$archive" ]] || ! tar -tf "$archive" | grep -Fxq './evidence.txt'; then
    fail "$case_name did not retain a readable, nonempty archive."
  fi
  if [[ "$(tar -xOf "$archive" ./evidence.txt)" != 'known non-secret release evidence' ]]; then
    fail "$case_name archive content changed."
  fi
  if ! grep -Fq "$expected_image -C /artifacts -cf - ." "$case_dir/docker.log"; then
    fail "$case_name did not use the pinned export image."
  fi
  if ! grep -Eq '^run --rm --name gama-(release|acceptance)-browser-artifacts-[0-9]+-export --network none ' "$case_dir/docker.log"; then
    fail "$case_name did not give its disposable export container an inspectable owned name."
  fi
  if [[ -e "$case_dir/volume" ]]; then
    fail "$case_name left its owned volume behind."
  fi
done

for wrapper in release-regression-runtime release-acceptance-runtime; do
  case_name="$wrapper-export-failure"
  status="$(run_wrapper "$wrapper" "$case_name" env GAMA_FAKE_EXPORT_STATUS=42)"
  [[ "$status" -ne 0 ]] || fail "$case_name masked export status 42."
  grep -Fq 'Evidence export failed with status 42' "$fixture_dir/$case_name/stderr" \
    || fail "$case_name did not report the export failure."
done

case_name=promotion-failure
status="$(run_wrapper release-acceptance-runtime "$case_name" env GAMA_FAKE_PROMOTION_STATUS=43)"
[[ "$status" -ne 0 ]] || fail "$case_name returned success."
grep -Fq 'Evidence archive promotion failed with status 43' "$fixture_dir/$case_name/stderr" \
  || fail "$case_name did not report the promotion failure."

case_name=destination-directory-during-export
case_dir="$fixture_dir/$case_name"
archive="$(archive_path release-acceptance-runtime "$case_dir")"
status="$(run_wrapper release-acceptance-runtime "$case_name" env GAMA_FAKE_FINAL_DESTINATION="$archive")"
[[ "$status" -ne 0 ]] || fail "$case_name returned success."
[[ -d "$archive" && "$(<"$archive/content")" == keep-directory-content ]] \
  || fail "$case_name modified the destination directory sentinel."
[[ "$(find "$archive" -mindepth 1 -maxdepth 1 -type f | wc -l | tr -d ' ')" -eq 1 ]] \
  || fail "$case_name added evidence inside the destination directory."

case_name=missing-volume
status="$(run_wrapper release-acceptance-runtime "$case_name" env GAMA_FAKE_DROP_VOLUME_BEFORE_CLEANUP=1)"
[[ "$status" -ne 0 ]] || fail "$case_name returned success."
grep -Fq 'Required evidence volume is missing:' "$fixture_dir/$case_name/stderr" \
  || fail "$case_name did not report the missing owned volume."

case_name=cleanup-failure
status="$(run_wrapper release-acceptance-runtime "$case_name" env GAMA_FAKE_REMOVE_STATUS=44)"
[[ "$status" -ne 0 ]] || fail "$case_name returned success."
grep -Fq 'Owned evidence volume cleanup failed with status 44:' "$fixture_dir/$case_name/stderr" \
  || fail "$case_name did not report the cleanup failure."
[[ -e "$fixture_dir/$case_name/volume" ]] || fail "$case_name did not retain the failed cleanup resource for recovery."

case_name=primary-failure
status="$(run_wrapper release-acceptance-runtime "$case_name" env GAMA_FAKE_PRIMARY_STATUS=37 GAMA_FAKE_EXPORT_STATUS=42 GAMA_FAKE_REMOVE_STATUS=44)"
assert_status "$case_name" 37 "$status"
grep -Fq 'Evidence export failed with status 42' "$fixture_dir/$case_name/stderr" \
  || fail "$case_name hid its export failure."
grep -Fq 'Owned evidence volume cleanup failed with status 44:' "$fixture_dir/$case_name/stderr" \
  || fail "$case_name hid its cleanup failure."

case_name=preexisting-volume
mkdir -p "$fixture_dir/$case_name/artifacts"
: >"$fixture_dir/$case_name/docker.log"
: >"$fixture_dir/$case_name/volume"
status="$(run_wrapper release-acceptance-runtime "$case_name" env)"
[[ "$status" -ne 0 ]] || fail "$case_name was adopted as an owned resource."
[[ -e "$fixture_dir/$case_name/volume" ]] || fail "$case_name was deleted by this invocation."
grep -Fq 'Refusing preexisting generated evidence volume:' "$fixture_dir/$case_name/stderr" \
  || fail "$case_name refusal was not reported."

case_name=preexisting-final
mkdir -p "$fixture_dir/$case_name/artifacts"
printf '%s' 'keep-final' >"$(archive_path release-acceptance-runtime "$fixture_dir/$case_name")"
status="$(run_wrapper release-acceptance-runtime "$case_name" env)"
[[ "$status" -ne 0 ]] || fail "$case_name returned success."
[[ "$(<"$(archive_path release-acceptance-runtime "$fixture_dir/$case_name")")" == keep-final ]] \
  || fail "$case_name modified the existing final archive."
[[ ! -e "$fixture_dir/$case_name/volume" ]] || fail "$case_name created or removed an unrelated volume."

case_name=preexisting-final-directory
mkdir -p "$fixture_dir/$case_name/artifacts"
archive="$(archive_path release-acceptance-runtime "$fixture_dir/$case_name")"
mkdir "$archive"
printf '%s' 'keep-directory-content' >"$archive/content"
status="$(run_wrapper release-acceptance-runtime "$case_name" env)"
[[ "$status" -ne 0 ]] || fail "$case_name returned success."
[[ "$(<"$archive/content")" == keep-directory-content ]] || fail "$case_name modified the existing destination directory."

case_name=preexisting-final-symlink
mkdir -p "$fixture_dir/$case_name/artifacts"
archive="$(archive_path release-acceptance-runtime "$fixture_dir/$case_name")"
printf '%s' 'keep-final-target' >"$fixture_dir/$case_name/target"
ln -s "$fixture_dir/$case_name/target" "$archive"
status="$(run_wrapper release-acceptance-runtime "$case_name" env)"
[[ "$status" -ne 0 ]] || fail "$case_name returned success."
[[ -L "$archive" && "$(<"$fixture_dir/$case_name/target")" == keep-final-target ]] \
  || fail "$case_name modified the existing destination symlink."

case_name=preexisting-partial
mkdir -p "$fixture_dir/$case_name/artifacts"
partial="$(archive_path release-acceptance-runtime "$fixture_dir/$case_name").partial"
printf '%s' 'keep-partial' >"$partial"
status="$(run_wrapper release-acceptance-runtime "$case_name" env)"
assert_status "$case_name" 0 "$status"
[[ "$(<"$partial")" == keep-partial ]] || fail "$case_name modified or removed the stale partial."

case_name=symlink-partial
mkdir -p "$fixture_dir/$case_name/artifacts"
victim="$fixture_dir/$case_name/victim"
printf '%s' 'keep-victim' >"$victim"
partial="$(archive_path release-acceptance-runtime "$fixture_dir/$case_name").partial"
ln -s "$victim" "$partial"
status="$(run_wrapper release-acceptance-runtime "$case_name" env)"
assert_status "$case_name" 0 "$status"
[[ -L "$partial" && "$(<"$victim")" == keep-victim ]] \
  || fail "$case_name followed or removed the stale partial symlink."

case_name=setup-failure-before-acquisition
mkdir -p "$fixture_dir/$case_name/artifacts"
: >"$fixture_dir/$case_name/volume"
status="$(run_wrapper release-acceptance-runtime "$case_name" env GAMA_FAKE_SETUP_STATUS=29)"
assert_status "$case_name" 29 "$status"
[[ -e "$fixture_dir/$case_name/volume" ]] || fail "$case_name removed a volume it did not acquire."
if grep -Fq 'Required evidence volume' "$fixture_dir/$case_name/stderr"; then
  fail "$case_name reported an unacquired volume as missing evidence."
fi
if grep -Eq '^volume (create|rm) ' "$fixture_dir/$case_name/docker.log"; then
  fail "$case_name created or removed a volume after setup failed."
fi

if [[ "$failures" -ne 0 ]]; then
  echo "$failures release evidence export contract assertion(s) failed." >&2
  exit 1
fi

echo 'Release evidence export ownership and fail-closed contract passed.'
