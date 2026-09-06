FROM mcr.microsoft.com/playwright:v1.62.1-noble@sha256:dcc5531e97840b9b5e794f2814476b21571c5124a3fca2267d73041f56e7580e

RUN set -eux; \
    test "$(dpkg-query -W -f='${Version}' libnss3)" = '2:3.98-1ubuntu0.2'; \
    test "$(dpkg-query -W -f='${Version}' libnspr4)" = '2:4.35-1.1build1'; \
    architecture="$(dpkg --print-architecture)"; \
    case "$architecture" in \
      amd64) \
        package_url='https://security.ubuntu.com/ubuntu/pool/main/n/nss/libnss3-tools_3.98-1ubuntu0.2_amd64.deb'; \
        package_sha256='e5b42390b02c21851bc04e9557ec48539a913f9b09637220c4b1db0d1386b3fb' \
        ;; \
      arm64) \
        package_url='https://ports.ubuntu.com/ubuntu-ports/pool/main/n/nss/libnss3-tools_3.98-1ubuntu0.2_arm64.deb'; \
        package_sha256='02d5f5e9d7a40d79fd23448b3f4016b7c83113f2b0df9f55efa16a39be33ce97' \
        ;; \
      *) \
        echo "Unsupported browser QA architecture: $architecture" >&2; \
        exit 1 \
        ;; \
    esac; \
    curl --fail --location --proto '=https' --tlsv1.2 --output /tmp/libnss3-tools.deb "$package_url"; \
    echo "$package_sha256  /tmp/libnss3-tools.deb" | sha256sum --check --strict; \
    test "$(dpkg-deb --field /tmp/libnss3-tools.deb Package)" = 'libnss3-tools'; \
    test "$(dpkg-deb --field /tmp/libnss3-tools.deb Version)" = '2:3.98-1ubuntu0.2'; \
    test "$(dpkg-deb --field /tmp/libnss3-tools.deb Architecture)" = "$architecture"; \
    dpkg --install /tmp/libnss3-tools.deb; \
    test "$(dpkg-query -W -f='${Version}' libnss3-tools)" = '2:3.98-1ubuntu0.2'; \
    rm /tmp/libnss3-tools.deb

WORKDIR /tests
COPY wordpress/qa/e2e/package.json wordpress/qa/e2e/package-lock.json ./
RUN npm ci --ignore-scripts
COPY wordpress/qa/e2e/playwright.config.ts ./
COPY wordpress/qa/e2e/timeout-policy.tsconfig.json ./
COPY wordpress/qa/e2e/specs ./specs
COPY wordpress/tests/release-https-trust.sh /usr/local/bin/gama-release-https-trust
RUN mv ./specs/support/release-tls-probe.cjs ./release-tls-probe.mjs \
    && chmod 0755 /usr/local/bin/gama-release-https-trust
CMD ["npm", "test"]
