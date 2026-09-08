#!/usr/bin/env bash
set -euo pipefail
REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
IMAGE='mcr.microsoft.com/playwright:v1.62.1-noble@sha256:dcc5531e97840b9b5e794f2814476b21571c5124a3fca2267d73041f56e7580e'
# All writes are disposable root-private fixtures. No Docker socket, application
# data, environment file or owner preview namespace enters this test runner.
docker run --rm --network none --read-only \
  --tmpfs /private-tests:rw,exec,nosuid,mode=0700,size=256m \
  --mount "type=bind,src=$REPOSITORY_ROOT/.git,dst=/repo/.git,readonly" \
  --mount "type=bind,src=$REPOSITORY_ROOT/.gitignore,dst=/repo/.gitignore,readonly" \
  --mount "type=bind,src=$REPOSITORY_ROOT/.github/workflows,dst=/repo/.github/workflows,readonly" \
  --mount "type=bind,src=$REPOSITORY_ROOT/wordpress/release,dst=/repo/wordpress/release,readonly" \
  --mount "type=bind,src=$REPOSITORY_ROOT/wordpress/tests,dst=/repo/wordpress/tests,readonly" \
  --mount "type=bind,src=$REPOSITORY_ROOT/wordpress/bin,dst=/repo/wordpress/bin,readonly" \
  --mount "type=bind,src=$REPOSITORY_ROOT/wordpress/runtime,dst=/repo/wordpress/runtime,readonly" \
  --mount "type=bind,src=$REPOSITORY_ROOT/wordpress/deploy,dst=/repo/wordpress/deploy,readonly" \
  --workdir /repo --env PYTHONDONTWRITEBYTECODE=1 --env GAMA_HOST_TEST_ROOT=/private-tests \
  --env TMPDIR=/private-tests --env GIT_CONFIG_COUNT=1 \
  --env GIT_CONFIG_KEY_0=safe.directory --env GIT_CONFIG_VALUE_0=/repo \
  --entrypoint python3 "$IMAGE" -W error -m unittest discover -s wordpress/tests/release -p 'test_*.py' -v
