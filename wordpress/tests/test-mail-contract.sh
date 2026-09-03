#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -f "$ROOT_DIR/.env" ]]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
fi

"$ROOT_DIR/bin/start"
token="$("$ROOT_DIR/bin/test-mail")"
[[ "$token" =~ ^gsweb10-mail-[0-9]+-[0-9]+$ ]]
