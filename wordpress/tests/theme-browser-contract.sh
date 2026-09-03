#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
manifest="$ROOT_DIR/qa/e2e/package.json"
lock="$ROOT_DIR/qa/e2e/package-lock.json"
dockerfile="$ROOT_DIR/qa/browser.Dockerfile"
global_styles_spec="$ROOT_DIR/qa/e2e/specs/global-styles.spec.ts"
navigation_spec="$ROOT_DIR/qa/e2e/specs/header-footer-navigation.spec.ts"
shared_helpers="$ROOT_DIR/qa/e2e/specs/support/wordpress.ts"
snapshot_dir="$ROOT_DIR/qa/e2e/specs/global-styles.spec.ts-snapshots"
config="$ROOT_DIR/qa/e2e/playwright.config.ts"
test_package="$ROOT_DIR/bin/test-package"

grep -Fq '"node": "22.*"' "$manifest"
grep -Fq '"@playwright/test": "1.54.2"' "$manifest"
grep -Fq '"node_modules/@playwright/test"' "$lock"
grep -Fq '"version": "1.54.2"' "$lock"
grep -Fq 'mcr.microsoft.com/playwright:v1.54.2-noble@sha256:18b4bcff4f8ba0ac8c44b09f09def6a4f6cb8579e5f26381c21f38b50935d5d8' "$dockerfile"
grep -Fq 'npm ci --ignore-scripts' "$dockerfile"
[[ -f "$global_styles_spec" ]]
[[ -f "$navigation_spec" ]]
[[ -f "$shared_helpers" ]]
grep -Fq "reducedMotion: 'reduce'" "$config"
grep -Fq 'threshold: 0.2' "$config"
grep -Fq 'maxDiffPixelRatio: 0.003' "$config"
grep -Fq '@global-styles' "$global_styles_spec"
for tag in \
  '@global-styles-editor-choices' \
  '@global-styles-front-snapshots' \
  '@global-styles-editor-snapshots' \
  '@global-styles-focus' \
  '@global-styles-admin-persistence' \
  '@global-styles-dpr2'; do
  grep -Fq "$tag" "$global_styles_spec"
  grep -Fq "GAMA_PLAYWRIGHT_RUN=${tag#@}" "$test_package"
  grep -Fq -- "--grep $tag" "$test_package"
done
for tag in '@navigation-initial' '@navigation-save' '@navigation-persisted'; do
  grep -Fq "$tag" "$navigation_spec"
done
grep -Fq 'waitForEditorCanvas' "$shared_helpers"
grep -Fq "waitUntil: 'domcontentloaded'" "$shared_helpers"
grep -Fq 'timeout: 45_000' "$shared_helpers"
grep -Fq "waitForLoadState('domcontentloaded'" "$shared_helpers"
grep -Fq 'waitForExactEditorParagraph' "$global_styles_spec"
for tag in \
  '@global-styles-editor-snapshots' \
  '@global-styles-admin-persistence'; do
  scoped_timeout_test="$(grep -F -A4 "$tag" "$global_styles_spec")"
  grep -Fq 'test.setTimeout(90_000);' <<<"$scoped_timeout_test"
done
[[ "$(grep -Fc 'test.setTimeout(90_000);' "$global_styles_spec")" -eq 2 ]]
grep -Fq 'watchWordPressDiagnostics' "$shared_helpers"
grep -Fq 'deviceScaleFactor' "$global_styles_spec"
grep -Fq 'does not satisfy the native 200% zoom checkpoint' "$global_styles_spec"
expected_snapshots="$(
  printf '%s\n' \
    global-styles-editor-1440-linux.png \
    global-styles-editor-390-linux.png \
    global-styles-editor-768-linux.png \
    global-styles-front-1440-linux.png \
    global-styles-front-390-linux.png \
    global-styles-front-768-linux.png
)"
actual_snapshots="$(find "$snapshot_dir" -mindepth 1 -maxdepth 1 -type f -name '*.png' -exec basename {} \; | sort)"
[[ "$actual_snapshots" == "$expected_snapshots" ]]
while IFS= read -r snapshot; do
  [[ -s "$snapshot_dir/$snapshot" ]]
done <<<"$expected_snapshots"
if grep -Eq 'COPY[[:space:]]+(\. |wordpress/ |src/|backend/)' "$dockerfile"; then
  echo 'Browser image copies outside its dedicated E2E package.' >&2
  exit 1
fi

echo 'Pinned browser image contract passed.'
