#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOSITORY_ROOT="$(cd "$ROOT_DIR/.." && pwd)"
dockerfile="$ROOT_DIR/qa/browser.Dockerfile"
probe="$ROOT_DIR/qa/e2e/specs/support/release-tls-probe.cjs"
runtime="$ROOT_DIR/tests/release-https-runtime.sh"
compose="$ROOT_DIR/tests/release-https-compose.yaml"
trust="$ROOT_DIR/tests/release-https-trust.sh"
regression_runtime="$ROOT_DIR/tests/release-regression-runtime.sh"

for file in "$dockerfile" "$probe" "$runtime" "$compose" "$trust" "$regression_runtime"; do
  if [[ ! -f "$file" ]]; then
    echo "Required HTTPS release helper is missing: $file" >&2
    exit 1
  fi
done
[[ -x "$runtime" && -x "$trust" ]]

bash -n "$runtime" "$trust" "$regression_runtime"
node --input-type=module --check <"$probe"
if grep -Eq '(^|[[:space:]])(mapfile|readarray)([[:space:]]|$)' "$runtime" "$trust"; then
  echo 'HTTPS helpers must remain compatible with the repository host Bash 3.2.' >&2
  exit 1
fi

if GAMA_STAGING_PROJECT=not-a-staging-project "$runtime" >/dev/null 2>&1; then
  echo 'HTTPS runtime accepted an unscoped Compose project.' >&2
  exit 1
fi
if node --input-type=module - unsupported-mode <"$probe" >/dev/null 2>&1; then
  echo 'TLS probe accepted an unsupported mode.' >&2
  exit 1
fi

compose_json="$(
  GAMA_RELEASE_HTTPS_FIXTURE=/tmp/gama-release-https-contract \
    docker compose --project-name gama-wp-staging-contract \
      --file "$compose" config --format json
)"
node -e '
  const assert = require("node:assert/strict");
  const config = JSON.parse(process.argv[1]);
  assert.deepEqual(Object.keys(config.services), ["wordpress-tls"]);
  const service = config.services["wordpress-tls"];
  assert.equal(
    service.image,
    "wordpress:7.1.0-php8.4-apache@sha256:b8f37de278183840a09f5a4b5bf5ec9f09177a9984d2fe5cc072b4388128bd9d",
  );
  assert.equal(service.restart, "no");
  assert.equal(service.ports, undefined);
  assert.equal(service.privileged, undefined);
  assert.deepEqual(
    service.volumes.map(({ source, target, read_only: readOnly }) => ({
      source,
      target,
      readOnly,
    })),
    [
      { source: "/tmp/gama-release-https-contract/apache.conf", target: "/run/gama-release-https/apache.conf", readOnly: true },
      { source: "/tmp/gama-release-https-contract/ca.crt", target: "/run/gama-release-https/ca.crt", readOnly: true },
      { source: "/tmp/gama-release-https-contract/leaf.crt", target: "/run/gama-release-https/leaf.crt", readOnly: true },
      { source: "/tmp/gama-release-https-contract/leaf.key", target: "/run/gama-release-https/leaf.key", readOnly: true },
    ],
  );
' "$compose_json"

grep -Fq 'libnss3-tools_3.98-1ubuntu0.2_amd64.deb' "$dockerfile"
grep -Fq 'e5b42390b02c21851bc04e9557ec48539a913f9b09637220c4b1db0d1386b3fb' "$dockerfile"
grep -Fq 'libnss3-tools_3.98-1ubuntu0.2_arm64.deb' "$dockerfile"
grep -Fq '02d5f5e9d7a40d79fd23448b3f4016b7c83113f2b0df9f55efa16a39be33ce97' "$dockerfile"
grep -Fq '2:3.98-1ubuntu0.2' "$dockerfile"
grep -Fq '2:4.35-1.1build1' "$dockerfile"
grep -Fq 'COPY wordpress/tests/release-https-trust.sh /usr/local/bin/gama-release-https-trust' "$dockerfile"
if grep -Eq 'apt(-get)? (update|upgrade)|aptitude' "$dockerfile"; then
  echo 'Browser image must not introduce mutable apt metadata or upgrades.' >&2
  exit 1
fi

grep -Fq '/root/.local/share/pki/nssdb' "$trust"
grep -Fq '/root/.pki/nssdb' "$trust"
grep -Fq -- '-t C,,' "$trust"
grep -Fq 'update-ca-certificates' "$trust"
grep -Fq 'NODE_EXTRA_CA_CERTS' "$trust"
grep -Fq 'https://wordpress-tls' "$runtime"
grep -Fq 'option get home' "$runtime"
grep -Fq 'option get siteurl' "$runtime"
grep -Fq 'option update home' "$runtime"
grep -Fq 'option update siteurl' "$runtime"
grep -Fq 'trap cleanup EXIT INT TERM' "$runtime"
grep -Fq 'release-https-runtime.sh' "$regression_runtime"
if grep -Fq -- '--env WP_BASE_URL=http://wordpress' "$regression_runtime"; then
  echo 'Release regression still invokes the matrix over HTTP.' >&2
  exit 1
fi

for directive in \
  'SSLEngine on' \
  'SSLCertificateFile /run/gama-release-https/leaf.crt' \
  'SSLCertificateKeyFile /run/gama-release-https/leaf.key' \
  'SSLProtocol -all +TLSv1.2 +TLSv1.3' \
  'ProxyRequests Off' \
  'ProxyPreserveHost On' \
  'RequestHeader set X-Forwarded-Proto "https"' \
  'ProxyPass "/" "http://wordpress/"' \
  'ProxyPassReverse "/" "http://wordpress/"'; do
  grep -Fq "$directive" "$runtime"
done

if grep -Eqi 'ignoreHTTPSErrors|ignore-certificate-errors|disable-web-security|unsafely-treat-insecure-origin-as-secure|NODE_TLS_REJECT_UNAUTHORIZED' \
  "$dockerfile" "$probe" "$runtime" "$compose" "$trust" "$regression_runtime"; then
  echo 'HTTPS release helpers contain a certificate or browser-security bypass.' >&2
  exit 1
fi
if grep -Eqi 'security add-trusted-cert|certutil.+(/Users/|\$HOME|~/)|docker (system )?prune|runtime-smoke.+--clean' \
  "$dockerfile" "$probe" "$runtime" "$compose" "$trust" "$regression_runtime"; then
  echo 'HTTPS release helpers can mutate host trust or broad Docker/runtime state.' >&2
  exit 1
fi

echo "GSWEB-27 HTTPS sidecar, trust, negative-certificate and cleanup contract passed for $REPOSITORY_ROOT."
