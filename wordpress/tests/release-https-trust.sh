#!/usr/bin/env bash
set -euo pipefail

ca_certificate="${GAMA_RELEASE_CA_CERTIFICATE:-/run/gama-release-trust/ca.crt}"
certificate_name='Gama Software ephemeral release test CA'
modern_nss_database='/root/.local/share/pki/nssdb'
legacy_nss_database='/root/.pki/nssdb'

if [[ "$#" -eq 0 ]]; then
  echo 'Trusted HTTPS wrapper requires a command.' >&2
  exit 64
fi
if [[ "$(id -u)" -ne 0 ]]; then
  echo 'Trusted HTTPS wrapper must run as root in the ephemeral browser container.' >&2
  exit 1
fi
if [[ ! -f "$ca_certificate" ]] || grep -Eq 'BEGIN .*PRIVATE KEY' "$ca_certificate"; then
  echo 'The browser trust mount must contain only the public ephemeral CA certificate.' >&2
  exit 1
fi
openssl x509 -in "$ca_certificate" -noout >/dev/null
test "$(dpkg-query -W -f='${Version}' libnss3-tools)" = '2:3.98-1ubuntu0.2'

install -m 0644 "$ca_certificate" /usr/local/share/ca-certificates/gama-release-test-ca.crt
update-ca-certificates >/dev/null

import_nss_certificate() {
  local database="$1"
  mkdir -p "$database"
  if ! certutil -L -d "sql:$database" >/dev/null 2>&1; then
    certutil -N --empty-password -d "sql:$database"
  fi
  certutil -D -d "sql:$database" -n "$certificate_name" >/dev/null 2>&1 || true
  certutil -A -d "sql:$database" -n "$certificate_name" -t C,, -i "$ca_certificate"
  certutil -L -d "sql:$database" -n "$certificate_name" >/dev/null
}

import_nss_certificate "$modern_nss_database"
if [[ -d "$legacy_nss_database" ]]; then
  import_nss_certificate "$legacy_nss_database"
fi

export NODE_EXTRA_CA_CERTS="$ca_certificate"
exec "$@"
