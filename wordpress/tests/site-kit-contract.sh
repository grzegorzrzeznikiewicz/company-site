#!/usr/bin/env bash
set -euo pipefail

# This test catches drift between the places that pin the external Site Kit by
# Google plugin (GSWEB-31): the extension lock, the production image, the local
# fetch script, the bootstrap, the local mounts, the release inventory and the
# runtime smoke test. The plugin code itself is never committed.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOSITORY_ROOT="$(cd "$ROOT_DIR/.." && pwd)"

version='1.192.0'
sha256='da9c8424b90fc700b09484c20a13aaa3e4ea75edd05a175bf100c6484daee064'
url="https://downloads.wordpress.org/plugin/google-site-kit.${version}.zip"

lock="$ROOT_DIR/config/extensions.lock.json"
dockerfile="$ROOT_DIR/runtime/Dockerfile"
fetch="$ROOT_DIR/bin/fetch-site-kit"
bootstrap="$ROOT_DIR/bin/bootstrap"
compose="$ROOT_DIR/compose.yaml"
smoke="$ROOT_DIR/tests/runtime-smoke.sh"
manifest="$ROOT_DIR/release/manifest.py"
candidate="$ROOT_DIR/release/candidate.py"

fail() {
  echo "Site Kit contract failed: $*" >&2
  exit 1
}

for file in "$lock" "$dockerfile" "$fetch" "$bootstrap" "$compose" "$smoke" "$manifest" "$candidate"; do
  [[ -f "$file" ]] || fail "missing $file"
done
[[ -x "$fetch" ]] || fail 'wordpress/bin/fetch-site-kit is not executable'

python3 -I - "$lock" "$version" "$sha256" "$url" <<'PY' || fail 'extensions.lock.json does not pin the expected Site Kit release'
import json
import sys

lock_path, version, sha256, url = sys.argv[1:]
with open(lock_path, encoding='utf-8') as handle:
    lock = json.load(handle)
entries = [entry for entry in lock['extensions'] if entry.get('slug') == 'google-site-kit']
assert len(entries) == 1, entries
entry = entries[0]
assert entry['type'] == 'plugin'
assert entry['version'] == version
assert entry['sha256'] == sha256
assert entry['source'] == url
assert entry['decision'] == 'GSWEB-31'
PY

# Production image: checksum-verified download, extracted plugin only.
grep -Fq "ADD --checksum=sha256:${sha256} \\" "$dockerfile" || fail 'Dockerfile does not verify the archive checksum'
grep -Fq "    ${url} /tmp/google-site-kit.zip" "$dockerfile" || fail 'Dockerfile does not fetch the pinned archive'
grep -Fq "Version: +${version//./\\.}\$" "$dockerfile" || fail 'Dockerfile does not assert the plugin header version'
grep -Fxq 'COPY --from=google_site_kit /tmp/google-site-kit-extract/google-site-kit /usr/src/wordpress/wp-content/plugins/google-site-kit' "$dockerfile" ||
  fail 'Dockerfile does not copy only the extracted plugin into the final image'
final_stage="$(awk '/^FROM wordpress:[0-9]/ { found = 1 } found' "$dockerfile")"
[[ -n "$final_stage" ]] || fail 'Dockerfile final WordPress stage not found'
if grep -Eq 'google-site-kit\.zip|^ADD ' <<<"$final_stage"; then
  fail 'the Site Kit archive must not be fetched or kept in the final image stage'
fi

# Local development: same pin, verified, mounted read-only in both services.
grep -Fxq "SITE_KIT_VERSION='${version}'" "$fetch" || fail 'fetch-site-kit pins a different version'
grep -Fxq "SITE_KIT_SHA256='${sha256}'" "$fetch" || fail 'fetch-site-kit pins a different checksum'
grep -Fq 'checksum mismatch' "$fetch" || fail 'fetch-site-kit does not refuse a checksum mismatch'
for script in start restart; do
  grep -Fxq '"$SCRIPT_DIR/fetch-site-kit"' "$ROOT_DIR/bin/$script" || fail "bin/$script does not fetch Site Kit first"
done
mount_count="$(grep -Fxc '      - ./.cache/extensions/google-site-kit:/var/www/html/wp-content/plugins/google-site-kit:ro' "$compose" || true)"
[[ "$mount_count" -eq 2 ]] || fail "expected two read-only Site Kit mounts in compose.yaml, found $mount_count"
(cd "$REPOSITORY_ROOT" && git check-ignore -q wordpress/.cache/extensions/google-site-kit/google-site-kit.php) ||
  fail 'the fetched plugin directory is not ignored by Git'
if (cd "$REPOSITORY_ROOT" && git ls-files --error-unmatch wordpress/.cache >/dev/null 2>&1); then
  fail 'plugin code must not be committed'
fi

# Activation and verification.
grep -Fxq 'wp_cli plugin activate google-site-kit' "$bootstrap" || fail 'bootstrap does not activate google-site-kit'
grep -Fq "grep -Fx 'google-site-kit'" "$smoke" || fail 'runtime smoke does not check that google-site-kit is active'
grep -Fq "plugin get google-site-kit --field=version | grep -Fx '${version}'" "$smoke" || fail 'runtime smoke does not check the Site Kit version'

# Release inventory.
grep -Fq "'plugin/google-site-kit'," "$manifest" || fail 'release manifest does not require plugin/google-site-kit'
grep -Fq "'plugin/google-site-kit'," "$candidate" || fail 'candidate validation does not list plugin/google-site-kit'
grep -Fq "'gama-mail-transport', 'google-site-kit') as \$plugin" "$candidate" || fail 'candidate package inventory does not read google-site-kit'

echo 'Site Kit by Google pin and activation contract passed.'
