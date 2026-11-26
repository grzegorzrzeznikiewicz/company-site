#!/usr/bin/env bash
set -euo pipefail

# This test catches drift between wordpress/config/extensions.lock.json and the
# places that ship each locked external plugin (GSWEB-31): the production image
# (checksum-verified ADD, version assertion, extracted directory only), the
# local fetch script and read-only mounts, the bootstrap activation, the release
# package inventory and the runtime smoke test. Plugin code is never committed.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOSITORY_ROOT="$(cd "$ROOT_DIR/.." && pwd)"

lock="$ROOT_DIR/config/extensions.lock.json"
dockerfile="$ROOT_DIR/runtime/Dockerfile"
fetch="$ROOT_DIR/bin/fetch-extensions"
bootstrap="$ROOT_DIR/bin/bootstrap"
compose="$ROOT_DIR/compose.yaml"
smoke="$ROOT_DIR/tests/runtime-smoke.sh"
manifest="$ROOT_DIR/release/manifest.py"
candidate="$ROOT_DIR/release/candidate.py"

fail() {
  echo "External extensions contract failed: $*" >&2
  exit 1
}

for file in "$lock" "$dockerfile" "$fetch" "$bootstrap" "$compose" "$smoke" "$manifest" "$candidate"; do
  [[ -f "$file" ]] || fail "missing $file"
done
[[ -x "$fetch" ]] || fail 'wordpress/bin/fetch-extensions is not executable'
grep -Fq 'config/extensions.lock.json' "$fetch" || fail 'fetch-extensions is not driven by the extension lock'
grep -Fq 'checksum mismatch' "$fetch" || fail 'fetch-extensions does not refuse a checksum mismatch'
for script in start restart; do
  grep -Fxq '"$SCRIPT_DIR/fetch-extensions"' "$ROOT_DIR/bin/$script" || fail "bin/$script does not fetch extensions first"
done

# The exact set of shipped external plugins and their main files. Complianz's
# upstream main file is really named complianz-gpdr.php.
expected='complianz-gdpr 7.5.9 complianz-gpdr.php
google-site-kit 1.192.0 google-site-kit.php
wp-consent-api 2.1.0 wp-consent-api.php'
locked="$(python3 -I - "$lock" <<'PY'
import json
import sys

with open(sys.argv[1], encoding='utf-8') as handle:
    lock = json.load(handle)
main_files = {'complianz-gdpr': 'complianz-gpdr.php'}
rows = []
for entry in lock['extensions']:
    assert entry['type'] == 'plugin', entry
    assert entry['decision'] == 'GSWEB-31', entry
    expected_source = 'https://downloads.wordpress.org/plugin/{0}.{1}.zip'.format(entry['slug'], entry['version'])
    assert entry['source'] == expected_source, entry
    rows.append('{0} {1} {2} {3}'.format(
        entry['slug'], entry['version'], main_files.get(entry['slug'], entry['slug'] + '.php'), entry['sha256']))
print('\n'.join(sorted(rows)))
PY
)" || fail 'extensions.lock.json entries are malformed'
[[ "$(cut -d' ' -f1-3 <<<"$locked")" == "$expected" ]] ||
  fail "locked extensions differ from the reviewed set:"$'\n'"$locked"

final_stage="$(awk '/^FROM wordpress:[0-9]/ { found = 1 } found' "$dockerfile")"
[[ -n "$final_stage" ]] || fail 'Dockerfile final WordPress stage not found'
if grep -Eq '\.zip|^ADD ' <<<"$final_stage"; then
  fail 'external archives must not be fetched or kept in the final image stage'
fi

while read -r slug version main_file sha256; do
  url="https://downloads.wordpress.org/plugin/${slug}.${version}.zip"
  escaped_version="${version//./\\.}"

  # Production image.
  # The checksum must sit on the ADD instruction that fetches this exact URL.
  add_pair="$(grep -Fx -A1 "ADD --checksum=sha256:${sha256} \\" "$dockerfile" || true)"
  [[ -n "$add_pair" ]] || fail "Dockerfile does not verify the $slug checksum"
  [[ "$add_pair" == "ADD --checksum=sha256:${sha256} \\"$'\n'"    ${url} /tmp/external-extensions/${slug}.zip" ]] ||
    fail "Dockerfile does not bind the $slug checksum to the pinned $slug archive"
  grep -Fq "Version: +${escaped_version}\$' /tmp/external-plugins/${slug}/${main_file}" "$dockerfile" ||
    fail "Dockerfile does not assert the $slug header version"
  grep -Fxq "COPY --from=external_extensions /tmp/external-plugins/${slug} /usr/src/wordpress/wp-content/plugins/${slug}" "$dockerfile" ||
    fail "Dockerfile does not copy only the extracted $slug directory"

  # Local development.
  mount_count="$(grep -Fxc "      - ./.cache/extensions/${slug}:/var/www/html/wp-content/plugins/${slug}:ro" "$compose" || true)"
  [[ "$mount_count" -eq 2 ]] || fail "expected two read-only $slug mounts in compose.yaml, found $mount_count"
  (cd "$REPOSITORY_ROOT" && git check-ignore -q "wordpress/.cache/extensions/${slug}/${main_file}") ||
    fail "the fetched $slug directory is not ignored by Git"

  # Activation, smoke and release inventory.
  grep -Eq "^wp_cli plugin activate( [a-z0-9-]+)* ${slug}( |\$)" "$bootstrap" || fail "bootstrap does not activate $slug"
  grep -Fq "grep -Fx '${slug}'" "$smoke" || fail "runtime smoke does not check that $slug is active"
  grep -Fq "plugin get ${slug} --field=version | grep -Fx '${version}'" "$smoke" || fail "runtime smoke does not check the $slug version"
  grep -Fq "'plugin/${slug}'," "$manifest" || fail "release manifest does not require plugin/$slug"
  grep -Fq "'plugin/${slug}'" "$candidate" || fail "candidate validation does not list plugin/$slug"
  if [[ "$main_file" == "${slug}.php" ]]; then
    grep -Eq "^foreach \(array\(([^)]*, )?'${slug}'(, [^)]*)?\) as \\\$plugin\) \{\$" "$candidate" ||
      fail "candidate package inventory does not read $slug"
  else
    grep -Fq "/usr/src/wordpress/wp-content/plugins/${slug}/${main_file}" "$candidate" ||
      fail "candidate package inventory does not read $slug from ${main_file}"
  fi
done < <(cut -d' ' -f1-4 <<<"$locked")

if (cd "$REPOSITORY_ROOT" && git ls-files --error-unmatch wordpress/.cache >/dev/null 2>&1); then
  fail 'external plugin code must not be committed'
fi

echo 'External extensions pin and activation contract passed.'
