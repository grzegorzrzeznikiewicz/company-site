#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
manifest="$ROOT_DIR/qa/e2e/package.json"
lock="$ROOT_DIR/qa/e2e/package-lock.json"
dockerfile="$ROOT_DIR/qa/browser.Dockerfile"

grep -Fq '"node": "22.*"' "$manifest"
grep -Fq '"@playwright/test": "1.54.2"' "$manifest"
grep -Fq '"node_modules/@playwright/test"' "$lock"
grep -Fq '"version": "1.54.2"' "$lock"
grep -Fq 'mcr.microsoft.com/playwright:v1.54.2-noble@sha256:18b4bcff4f8ba0ac8c44b09f09def6a4f6cb8579e5f26381c21f38b50935d5d8' "$dockerfile"
grep -Fq 'npm ci --ignore-scripts' "$dockerfile"
if grep -Eq 'COPY[[:space:]]+(\. |wordpress/ |src/|backend/)' "$dockerfile"; then
  echo 'Browser image copies outside its dedicated E2E package.' >&2
  exit 1
fi

echo 'Pinned browser image contract passed.'
