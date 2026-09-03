#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
manifest="$ROOT_DIR/qa/e2e/package.json"
lock="$ROOT_DIR/qa/e2e/package-lock.json"
dockerfile="$ROOT_DIR/qa/browser.Dockerfile"
global_styles_spec="$ROOT_DIR/qa/e2e/specs/global-styles.spec.ts"
snapshot_dir="$ROOT_DIR/qa/e2e/specs/global-styles.spec.ts-snapshots"
config="$ROOT_DIR/qa/e2e/playwright.config.ts"

grep -Fq '"node": "22.*"' "$manifest"
grep -Fq '"@playwright/test": "1.54.2"' "$manifest"
grep -Fq '"node_modules/@playwright/test"' "$lock"
grep -Fq '"version": "1.54.2"' "$lock"
grep -Fq 'mcr.microsoft.com/playwright:v1.54.2-noble@sha256:18b4bcff4f8ba0ac8c44b09f09def6a4f6cb8579e5f26381c21f38b50935d5d8' "$dockerfile"
grep -Fq 'npm ci --ignore-scripts' "$dockerfile"
[[ -f "$global_styles_spec" ]]
grep -Fq "reducedMotion: 'reduce'" "$config"
grep -Fq 'threshold: 0.2' "$config"
grep -Fq 'maxDiffPixelRatio: 0.003' "$config"
grep -Fq '@global-styles' "$global_styles_spec"
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
