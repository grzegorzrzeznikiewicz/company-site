#!/usr/bin/env bash
set -euo pipefail

# This test drives the real test-package script through a controlled Docker
# boundary and verifies exact-label preflight and cleanup failure semantics.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_PACKAGE="$ROOT_DIR/bin/test-package"
ARTIFACT="$ROOT_DIR/dist/gama-contact-0.1.0.zip"
fixture_dir="$(mktemp -d "${TMPDIR:-/tmp}/gama-test-package-isolation.XXXXXX")"
fake_bin="$fixture_dir/bin"
log_path="$fixture_dir/docker.log"
mkdir -p "$fake_bin"

cleanup() {
  find "$fixture_dir" -type f -delete
  find "$fixture_dir" -depth -type d -exec rmdir {} \;
}
trap cleanup EXIT

if [[ ! -f "$ARTIFACT" || -L "$ARTIFACT" ]]; then
  echo "Canonical regular test artifact is required: $ARTIFACT" >&2
  exit 1
fi

printf '%s\n' '#!/usr/bin/env bash' \
  'set -euo pipefail' \
  'printf "%s\\n" "$*" >>"$FAKE_DOCKER_LOG"' \
  'kind="${1:-}"' \
  'action="${2:-}"' \
  'if [[ "$kind" =~ ^(container|volume|network)$ && "$action" == "ls" ]]; then' \
  '  count_file="$FAKE_DOCKER_STATE/${kind}-queries"' \
  '  count=0' \
  '  [[ ! -f "$count_file" ]] || count="$(<"$count_file")"' \
  '  count=$((count + 1))' \
  '  printf "%s\\n" "$count" >"$count_file"' \
  '  if [[ "$FAKE_DOCKER_MODE" == collision && "$kind" == container ]]; then printf "%s\\n" occupied; exit 0; fi' \
  '  if [[ "$FAKE_DOCKER_MODE" == preflight-query-failure && "$kind" == container ]]; then exit 73; fi' \
  '  if [[ "$FAKE_DOCKER_MODE" =~ ^cleanup-query-failure && "$count" -gt 1 ]]; then exit 74; fi' \
  '  exit 0' \
  'fi' \
  'if [[ "$kind" == compose ]]; then' \
  '  case " $* " in' \
  '    *" up --detach --wait db wordpress "*) [[ "$FAKE_DOCKER_MODE" == cleanup-query-failure-success ]] && exit 0; exit 88 ;;' \
  '    *" run --rm --no-deps wp core version "*) printf "%s\\n" 7.1; exit 0 ;;' \
  '    *" run --rm --no-deps wp eval "*"version_compare(PHP_VERSION"*) printf "%s\\n" 8.4.25; exit 0 ;;' \
  '    *" run --rm --no-deps wp eval "*) printf "%s\\n" lifecycle-and-side-effects-ok; exit 0 ;;' \
  '    *" run --rm --no-deps wp theme list --status=active --field=name "*) printf "%s\\n" twentytwentyfive; exit 0 ;;' \
  '    *" run --rm --no-deps wp theme list --status=inactive --field=name "*) printf "%s\\n" twentytwentyfour; exit 0 ;;' \
  '    *" run --rm --no-deps wp plugin get gama-contact --field=version "*) printf "%s\\n" 0.1.0; exit 0 ;;' \
  '    *" run --rm --no-deps wp option get gama_contact_schema_version "*) printf "%s\\n" 1; exit 0 ;;' \
  '    *" run --rm --no-deps wp plugin uninstall gama-contact "*) : >"$FAKE_DOCKER_STATE/uninstalled"; exit 0 ;;' \
  '    *" run --rm --no-deps wp plugin is-installed gama-contact "*) [[ ! -f "$FAKE_DOCKER_STATE/uninstalled" ]]; exit $? ;;' \
  '    *) exit 0 ;;' \
  '  esac' \
  'fi' \
  'exit 99' >"$fake_bin/docker"
chmod +x "$fake_bin/docker"

run_case() {
  local mode="$1"
  local expected_status="$2"
  local state_dir="$fixture_dir/$mode"
  local output command_status

  mkdir "$state_dir"
  : >"$log_path"
  set +e
  output="$(FAKE_DOCKER_MODE="$mode" FAKE_DOCKER_LOG="$log_path" FAKE_DOCKER_STATE="$state_dir" PATH="$fake_bin:$PATH" "$TEST_PACKAGE" "$ARTIFACT" 2>&1)"
  command_status=$?
  set -e
  if [[ "$command_status" -ne "$expected_status" ]]; then
    printf 'Isolation case %s returned %s instead of %s:\n%s\n' "$mode" "$command_status" "$expected_status" "$output" >&2
    exit 1
  fi
  cp "$log_path" "$fixture_dir/$mode.log"
}

run_case collision 1
if grep -Fq ' up --detach --wait ' "$fixture_dir/collision.log"; then
  echo 'Collision preflight reached Compose startup.' >&2
  exit 1
fi

run_case preflight-query-failure 73
if grep -Fq ' up --detach --wait ' "$fixture_dir/preflight-query-failure.log"; then
  echo 'Failed preflight residue query reached Compose startup.' >&2
  exit 1
fi

run_case cleanup-query-failure 88
for kind in container volume network; do
  if [[ "$(<"$fixture_dir/cleanup-query-failure/$kind-queries")" -ne 2 ]]; then
    echo "Cleanup did not execute and propagate the $kind residue query." >&2
    exit 1
  fi
done

run_case cleanup-query-failure-success 74
for kind in container volume network; do
  if [[ "$(<"$fixture_dir/cleanup-query-failure-success/$kind-queries")" -ne 2 ]]; then
    echo "Successful lifecycle did not propagate the failed $kind cleanup query." >&2
    exit 1
  fi
done

project_labels="$(grep -Eo 'label=com\.docker\.compose\.project=gama-package-[0-9]+-[0-9]+-[0-9]+' "$fixture_dir/cleanup-query-failure.log" | LC_ALL=C sort -u)"
if [[ "$(wc -l <<<"$project_labels" | tr -d ' ')" -ne 1 ]]; then
  echo 'Isolation queries did not consistently use one exact generated project label.' >&2
  exit 1
fi

echo 'test-package isolation contract passed.'
