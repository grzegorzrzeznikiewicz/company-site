#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOSITORY_ROOT="$ROOT_DIR/.."
STAGING_WORKFLOW="$REPOSITORY_ROOT/.github/workflows/wordpress-staging.yml"
PRODUCTION_WORKFLOW="$REPOSITORY_ROOT/.github/workflows/wordpress-production.yml"
ROLLBACK_WORKFLOW="$REPOSITORY_ROOT/.github/workflows/wordpress-production-rollback.yml"
FIXTURE_IMAGE='mcr.microsoft.com/playwright:v1.62.1-noble@sha256:dcc5531e97840b9b5e794f2814476b21571c5124a3fca2267d73041f56e7580e'

extract_step_scalar() {
  local workflow="$1"
  local step_name="$2"
  local key="$3"
  local output="$4"

  awk -v step_name="$step_name" -v scalar_key="$key" '
    function indentation(value) {
      match(value, /[^ ]/)
      return RSTART - 1
    }
    {
      trimmed = $0
      sub(/^ +/, "", trimmed)
    }
    trimmed == "- name: " step_name {
      in_step = 1
      next
    }
    in_step && trimmed ~ /^- name: / {
      exit
    }
    in_step && index(trimmed, scalar_key ": ") == 1 {
      value = substr(trimmed, length(scalar_key) + 3)
      if (value != "|") {
        print value
        exit
      }
      capture = 1
      content_indent = indentation($0) + 2
      next
    }
    capture {
      if ($0 == "") {
        print ""
        next
      }
      if (indentation($0) < content_indent) {
        exit
      }
      print substr($0, content_indent + 1)
    }
  ' "$workflow" > "$output"
  [[ -s "$output" ]]
}

run_release_validator() {
  local script="$1"
  local fixture="$2"
  local git_sha="$3"
  local run_id="$4"
  local case_fixture
  local expected_image

  [[ -f "$fixture/staging-evidence/staging-release.json" ]]
  case_fixture="$(mktemp -d "$fixture/validator-case.XXXXXX")"
  mkdir -p "$case_fixture/bin" "$case_fixture/staging-evidence"
  cp "$fixture/bin/jq" "$case_fixture/bin/jq"
  cp "$script" "$case_fixture/validator.sh"
  cp -P "$fixture/staging-evidence/staging-release.json" \
    "$case_fixture/staging-evidence/staging-release.json"
  if ! docker run --rm --name "${container_name}-validator" --network none \
      --volume "$case_fixture:/fixture" \
      --env PATH=/fixture/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
      --env GITHUB_OUTPUT=/fixture/production.output \
      --env INPUT_GIT_SHA="$git_sha" \
      --env INPUT_STAGING_RUN_ID="$run_id" \
      --workdir /fixture --entrypoint bash "$FIXTURE_IMAGE" \
      -euo pipefail /fixture/validator.sh; then
    return 1
  fi
  expected_image="$(jq -r '.image' "$fixture/staging-evidence/staging-release.json")"
  grep -Fxq "image=$expected_image" "$case_fixture/production.output"
}

test_release_handoff() {
  local fixture="$1"
  local git_sha='1234567890abcdef1234567890abcdef12345678'
  local wrong_sha='abcdef1234567890abcdef1234567890abcdef12'
  local digest="sha256:$(printf 'a%.0s' {1..64})"
  local run_id='987654321'
  local tag image
  local metadata_script="$fixture/metadata.sh"
  local reference_script="$fixture/reference.sh"
  local record_script="$fixture/record.sh"
  local validator_script="$fixture/validator.sh"

  mkdir -p "$fixture/staging-evidence" "$fixture/bin"
  cat > "$fixture/bin/jq" <<'EOF'
#!/usr/bin/env python3
import json
import sys

expression = sys.argv[-2]
with open(sys.argv[-1], encoding="utf-8") as source:
    evidence = json.load(source)
if expression == ".git_sha":
    print(evidence.get("git_sha"))
elif expression == ".staging_run_id | tostring":
    print(evidence.get("staging_run_id"))
elif expression == ".image":
    print(evidence.get("image"))
else:
    raise SystemExit(f"unsupported fixture jq expression: {expression}")
EOF
  chmod 0755 "$fixture/bin/jq"
  extract_step_scalar "$STAGING_WORKFLOW" 'Prepare image tag' run "$metadata_script"
  extract_step_scalar "$STAGING_WORKFLOW" 'Publish immutable reference' run "$reference_script"
  extract_step_scalar "$STAGING_WORKFLOW" 'Record staging-tested immutable release' run "$record_script"
  extract_step_scalar "$PRODUCTION_WORKFLOW" 'Verify immutable staging evidence' run "$validator_script"

  docker run --rm --name "${container_name}-handoff" --network none \
    --volume "$fixture:/fixture" \
    --env GITHUB_REPOSITORY_OWNER=GamaSoftware \
    --env INPUT_GIT_SHA="$git_sha" \
    --env GITHUB_OUTPUT=/fixture/metadata.output \
    --entrypoint bash "$FIXTURE_IMAGE" -euo pipefail /fixture/metadata.sh
  tag="$(sed -n 's/^tag=//p' "$fixture/metadata.output")"
  [[ "$tag" == "ghcr.io/gamasoftware/gama-wordpress:sha-$git_sha" ]]

  sed \
    -e "s#\${{ steps.metadata.outputs.tag }}#$tag#g" \
    -e "s#\${{ steps.build.outputs.digest }}#$digest#g" \
    "$reference_script" > "$fixture/reference-resolved.sh"
  GITHUB_OUTPUT="$fixture/reference.output" bash -euo pipefail "$fixture/reference-resolved.sh"
  image="$(sed -n 's/^image=//p' "$fixture/reference.output")"
  [[ "$image" == "$tag@$digest" ]]

  sed "s#\${{ github.run_id }}#$run_id#g" "$record_script" > "$fixture/record-resolved.sh"
  (
    cd "$fixture"
    INPUT_GIT_SHA="$git_sha" WORDPRESS_IMAGE="$image" bash -euo pipefail "$fixture/record-resolved.sh"
  )
  mv "$fixture/staging-release.json" "$fixture/staging-evidence/staging-release.json"
  if ! run_release_validator "$validator_script" "$fixture" "$git_sha" "$run_id"; then
    echo 'Production rejected the exact tag-at-digest reference produced by staging.' >&2
    return 1
  fi

  jq --arg image "ghcr.io/gamasoftware/gama-wordpress@$digest" '.image = $image' \
    "$fixture/staging-evidence/staging-release.json" > "$fixture/staging-evidence/next.json"
  mv "$fixture/staging-evidence/next.json" "$fixture/staging-evidence/staging-release.json"
  run_release_validator "$validator_script" "$fixture" "$git_sha" "$run_id"

  local rejected_image
  for rejected_image in \
    'ghcr.io/gamasoftware/gama-wordpress:latest' \
    "ghcr.io/gamasoftware/gama-wordpress:sha-$wrong_sha@$digest" \
    "ghcr.io/gamasoftware/gama-wordpress:sha-$git_sha@sha256:abc"; do
    jq --arg image "$rejected_image" '.image = $image' \
      "$fixture/staging-evidence/staging-release.json" > "$fixture/staging-evidence/next.json"
    mv "$fixture/staging-evidence/next.json" "$fixture/staging-evidence/staging-release.json"
    if run_release_validator "$validator_script" "$fixture" "$git_sha" "$run_id" >/dev/null 2>&1; then
      echo "Production accepted rejected staging image: $rejected_image" >&2
      return 1
    fi
  done

  jq --arg git_sha "$wrong_sha" --arg image "$image" '.git_sha = $git_sha | .image = $image' \
    "$fixture/staging-evidence/staging-release.json" > "$fixture/staging-evidence/next.json"
  mv "$fixture/staging-evidence/next.json" "$fixture/staging-evidence/staging-release.json"
  if run_release_validator "$validator_script" "$fixture" "$git_sha" "$run_id" >/dev/null 2>&1; then
    echo 'Production accepted evidence for a different Git revision.' >&2
    return 1
  fi

  jq --arg git_sha "$git_sha" --arg image "$image" '.git_sha = $git_sha | .image = $image | .staging_run_id = 123' \
    "$fixture/staging-evidence/staging-release.json" > "$fixture/staging-evidence/next.json"
  mv "$fixture/staging-evidence/next.json" "$fixture/staging-evidence/staging-release.json"
  if run_release_validator "$validator_script" "$fixture" "$git_sha" "$run_id" >/dev/null 2>&1; then
    echo 'Production accepted evidence for a different staging run.' >&2
    return 1
  fi

  rm "$fixture/staging-evidence/staging-release.json"
  ln -s ../record-resolved.sh "$fixture/staging-evidence/staging-release.json"
  if run_release_validator "$validator_script" "$fixture" "$git_sha" "$run_id" >/dev/null 2>&1; then
    echo 'Production accepted symlinked staging evidence.' >&2
    return 1
  fi
}

run_permission_fixture() {
  install -d -m 0755 /fixture
  extract_step_scalar /repo/.github/workflows/wordpress-production.yml \
    'Require off-host backup target and deploy exact image' script /fixture/prepare-stable.sh
  extract_step_scalar /repo/.github/workflows/wordpress-production.yml \
    'Switch through the infrastructure-owned hook' script /fixture/cutover-hook.sh
  extract_step_scalar /repo/.github/workflows/wordpress-production.yml \
    'Fail safe to the preserved legacy route' script /fixture/fail-safe-hook.sh
  extract_step_scalar /repo/.github/workflows/wordpress-production-rollback.yml \
    'Route to legacy independently of WordPress health' script /fixture/rollback-routing-hook.sh
  extract_step_scalar /repo/.github/workflows/wordpress-production-rollback.yml \
    'Back up and roll application code back' script /fixture/code-rollback.sh
  sed -i 's#${{ github.run_id }}#246813579#g' /fixture/fail-safe-hook.sh
  chmod 0755 /fixture/*.sh

  getent group operator >/dev/null
  useradd --create-home --uid 2000 --gid operator fixtureuser
  printf '%s\n' \
    'auth sufficient pam_permit.so' \
    'account sufficient pam_permit.so' \
    'session sufficient pam_permit.so' \
    > /etc/pam.d/su

  install -d -m 0755 /fixture/bin
  cat > /fixture/bin/sudo <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
exec /usr/bin/su -s /bin/bash -c '
  printf "uid=%s command=%s\n" "$(id -u)" "$1" >> /fixture/elevation.log
  exec "$@"
' root -- sudo-root "$@"
EOF
  cat > /fixture/bin/docker <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
case "$*" in
  *'ps --filter label=com.docker.compose.project=gama-wp-production --filter label=com.docker.compose.service=wordpress'*) printf '%s\n' fixture-container ;;
  *"inspect --format {{.State.Health.Status}}"*) printf '%s\n' healthy ;;
  *"inspect --format {{.Config.Image}}"*) printf '%s\n' 'ghcr.io/gamasoftware/gama-wordpress@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb' ;;
esac
EOF
  cat > /fixture/bin/mountpoint <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
  cat > /fixture/bin/findmnt <<'EOF'
#!/usr/bin/env bash
printf '%s\n' fixture-off-host-source
EOF
  cat > /fixture/bin/curl <<'EOF'
#!/usr/bin/env bash
printf '%s\n' '<h1>Gama Software</h1><form class="gama-contact-form"></form>'
EOF
  chmod 0755 /fixture/bin/*

  install -d -o fixtureuser -g operator -m 0750 \
    /srv/gama-wordpress-production \
    /srv/gama-wordpress-production/bin \
    /srv/gama-wordpress-production/deploy \
    /srv/gama-wordpress-production/deployments \
    /srv/gama-wordpress-production/deployments/135792468
  install -o fixtureuser -g operator -m 0600 /dev/null /srv/gama-wordpress-production/.env
  install -o fixtureuser -g operator -m 0640 /dev/null /srv/gama-wordpress-production/deploy/compose.yaml
  install -d -o root -g root -m 0750 /backup

  cat > /fixture/tool <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
  cat > /fixture/backup <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
destination="${@: -1}"
install -d -o root -g root -m 0700 "$destination"
printf 'private fixture payload\n' > "$destination/payload.sql"
(cd "$destination" && sha256sum payload.sql > SHA256SUMS)
chmod 0600 "$destination/payload.sql" "$destination/SHA256SUMS"
if [[ -f /fixture/corrupt-backup && "$(cat /fixture/corrupt-backup)" == "$(basename "$destination")" ]]; then
  printf 'corruption\n' >> "$destination/payload.sql"
fi
EOF
  chmod 0755 /fixture/tool /fixture/backup
  for tool in deploy-production rollback-production; do
    install -o root -g root -m 0750 /fixture/tool "/srv/gama-wordpress-production/bin/$tool"
  done
  install -o root -g root -m 0750 /fixture/backup /srv/gama-wordpress-production/bin/backup
  install -o root -g root -m 0750 /fixture/tool /usr/local/sbin/gama-wordpress-cutover
  install -o root -g root -m 0750 /fixture/tool /usr/local/sbin/gama-wordpress-rollback-routing
  printf '%s\n' \
    'status=passed' \
    'image=ghcr.io/gamasoftware/gama-wordpress:sha-1234567890abcdef1234567890abcdef12345678@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' \
    > /fixture/candidate.env
  install -o root -g root -m 0600 /fixture/candidate.env \
    /srv/gama-wordpress-production/deployments/135792468/candidate.env

  run_as_operator() {
    local script="$1"
    /usr/bin/su fixtureuser -s /bin/bash -c \
      "env PATH=/fixture/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
        WORDPRESS_IMAGE=ghcr.io/gamasoftware/gama-wordpress:sha-1234567890abcdef1234567890abcdef12345678@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
        GAMA_GIT_SHA=1234567890abcdef1234567890abcdef12345678 \
        DEPLOYMENT_RUN_ID=135792468 ROLLBACK_RUN_ID=246813579 \
        DEPLOYMENT_WINDOW_UTC=2026-09-06T12:00Z \
        PRODUCTION_BACKUP_ROOT=/backup PRODUCTION_BACKUP_EXPECTED_SOURCE=fixture-off-host-source \
        GHCR_USERNAME=fixture GHCR_TOKEN=fixture bash '$script'"
  }

  expect_failure() {
    local label="$1"
    shift
    if "$@" > "/fixture/$label.output" 2>&1; then
      echo "Expected workflow boundary failure: $label" >&2
      return 1
    fi
  }

  if ! run_as_operator /fixture/prepare-stable.sh; then
    echo 'The non-root production operator could not consume root-private workflow outputs.' >&2
    return 1
  fi
  run_as_operator /fixture/cutover-hook.sh
  run_as_operator /fixture/fail-safe-hook.sh
  run_as_operator /fixture/rollback-routing-hook.sh
  run_as_operator /fixture/code-rollback.sh

  [[ "$(stat -c '%u:%g:%a' /srv/gama-wordpress-production/deployments/135792468/deployment.env)" == '0:0:600' ]]
  [[ "$(stat -c '%u:%g:%a' /backup/wordpress-predeploy-135792468)" == '0:0:700' ]]
  [[ "$(stat -c '%u:%g:%a' /backup/wordpress-precutover-135792468)" == '0:0:700' ]]
  [[ "$(stat -c '%u:%g:%a' /backup/wordpress-prerollback-246813579)" == '0:0:700' ]]
  expect_failure private-candidate /usr/bin/su fixtureuser -s /bin/bash -c \
    'cat /srv/gama-wordpress-production/deployments/135792468/candidate.env'
  expect_failure private-deployment /usr/bin/su fixtureuser -s /bin/bash -c \
    'cat /srv/gama-wordpress-production/deployments/135792468/deployment.env'
  expect_failure private-backup /usr/bin/su fixtureuser -s /bin/bash -c \
    'cd /backup/wordpress-predeploy-135792468'
  expect_failure status-preserved /usr/bin/su fixtureuser -s /bin/bash -c \
    'PATH=/fixture/bin:$PATH sudo false'
  for elevated_command in test stat find grep bash sed; do
    grep -Fxq "uid=0 command=$elevated_command" /fixture/elevation.log
  done

  cp /srv/gama-wordpress-production/deployments/135792468/deployment.env /fixture/deployment.valid
  reset_backups() {
    find /backup -mindepth 1 -depth -delete
  }

  mv /srv/gama-wordpress-production/bin/deploy-production /fixture/deploy-production.real
  ln -s /fixture/deploy-production.real /srv/gama-wordpress-production/bin/deploy-production
  expect_failure symlinked-tool run_as_operator /fixture/prepare-stable.sh
  rm /srv/gama-wordpress-production/bin/deploy-production
  install -o fixtureuser -g operator -m 0750 /fixture/tool /srv/gama-wordpress-production/bin/deploy-production
  expect_failure non-root-tool run_as_operator /fixture/prepare-stable.sh
  install -o root -g root -m 0770 /fixture/tool /srv/gama-wordpress-production/bin/deploy-production
  expect_failure writable-tool run_as_operator /fixture/prepare-stable.sh
  install -o root -g root -m 0750 /fixture/tool /srv/gama-wordpress-production/bin/deploy-production

  unlink /srv/gama-wordpress-production/deployments/135792468/candidate.env
  ln -s /fixture/candidate.env /srv/gama-wordpress-production/deployments/135792468/candidate.env
  expect_failure symlinked-candidate run_as_operator /fixture/prepare-stable.sh
  unlink /srv/gama-wordpress-production/deployments/135792468/candidate.env
  install -o fixtureuser -g operator -m 0600 /fixture/candidate.env \
    /srv/gama-wordpress-production/deployments/135792468/candidate.env
  expect_failure non-root-candidate run_as_operator /fixture/prepare-stable.sh
  install -o root -g root -m 0660 /fixture/candidate.env \
    /srv/gama-wordpress-production/deployments/135792468/candidate.env
  expect_failure writable-candidate run_as_operator /fixture/prepare-stable.sh
  printf 'status=failed\n' > /fixture/candidate.env
  install -o root -g root -m 0600 /fixture/candidate.env \
    /srv/gama-wordpress-production/deployments/135792468/candidate.env
  expect_failure invalid-candidate run_as_operator /fixture/prepare-stable.sh

  printf '%s\n' \
    'status=passed' \
    'image=ghcr.io/gamasoftware/gama-wordpress:sha-1234567890abcdef1234567890abcdef12345678@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' \
    > /fixture/candidate.env
  install -o root -g root -m 0600 /fixture/candidate.env \
    /srv/gama-wordpress-production/deployments/135792468/candidate.env
  reset_backups
  printf '%s\n' wordpress-predeploy-135792468 > /fixture/corrupt-backup
  expect_failure corrupt-predeploy-manifest run_as_operator /fixture/prepare-stable.sh
  reset_backups
  printf '%s\n' wordpress-precutover-135792468 > /fixture/corrupt-backup
  expect_failure corrupt-precutover-manifest run_as_operator /fixture/prepare-stable.sh
  unlink /fixture/corrupt-backup
  reset_backups
  run_as_operator /fixture/prepare-stable.sh
  cp /srv/gama-wordpress-production/deployments/135792468/deployment.env /fixture/deployment.valid

  unlink /srv/gama-wordpress-production/deployments/135792468/deployment.env
  ln -s /fixture/deployment.valid /srv/gama-wordpress-production/deployments/135792468/deployment.env
  expect_failure symlinked-deployment run_as_operator /fixture/code-rollback.sh
  unlink /srv/gama-wordpress-production/deployments/135792468/deployment.env
  install -o fixtureuser -g operator -m 0600 /fixture/deployment.valid \
    /srv/gama-wordpress-production/deployments/135792468/deployment.env
  expect_failure non-root-deployment run_as_operator /fixture/code-rollback.sh
  install -o root -g root -m 0660 /fixture/deployment.valid \
    /srv/gama-wordpress-production/deployments/135792468/deployment.env
  expect_failure writable-deployment run_as_operator /fixture/code-rollback.sh
  sed 's#^previous_image=.*#previous_image=ghcr.io/gamasoftware/gama-wordpress:latest#' \
    /fixture/deployment.valid > /fixture/deployment.invalid
  install -o root -g root -m 0600 /fixture/deployment.invalid \
    /srv/gama-wordpress-production/deployments/135792468/deployment.env
  reset_backups
  expect_failure mutable-rollback-image run_as_operator /fixture/code-rollback.sh
}

if [[ "${1:-}" == '--permission-fixture' ]]; then
  run_permission_fixture
  echo 'Real non-root/root workflow permission boundary passed.'
  exit 0
fi

for required in "$STAGING_WORKFLOW" "$PRODUCTION_WORKFLOW" "$ROLLBACK_WORKFLOW"; do
  [[ -f "$required" ]]
done
command -v jq >/dev/null
command -v docker >/dev/null

fixture_dir="$(mktemp -d /tmp/gama-workflow-boundary.XXXXXX)"
container_name="gama-workflow-boundary-${UID}-$$-${RANDOM}"
cleanup() {
  local status=$?
  docker rm --force "$container_name" >/dev/null 2>&1 || true
  docker rm --force "${container_name}-handoff" >/dev/null 2>&1 || true
  docker rm --force "${container_name}-validator" >/dev/null 2>&1 || true
  find "$fixture_dir" -type l -delete
  find "$fixture_dir" -type f -delete
  find "$fixture_dir" -depth -type d -exec rmdir {} +
  exit "$status"
}
trap cleanup EXIT

test_release_handoff "$fixture_dir"
docker run --rm --name "$container_name" --network none \
  --volume "$REPOSITORY_ROOT:/repo:ro" \
  --entrypoint bash "$FIXTURE_IMAGE" \
  /repo/wordpress/tests/production-workflow-boundary-contract.sh --permission-fixture

echo 'Immutable release handoff and privileged workflow boundaries passed.'
