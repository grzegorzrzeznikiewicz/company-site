FROM wordpress:cli-2.12.0-php8.4@sha256:1e1d1485277d15e0331b598b6e19972243128ead978b7134d758097d82116b99 AS wp_cli

# External extensions pinned in wordpress/config/extensions.lock.json (GSWEB-31).
# BuildKit refuses the build when a downloaded archive does not match its
# checksum; only the extracted plugin directories reach the final image.
FROM wp_cli AS external_extensions
USER root
ADD --checksum=sha256:da9c8424b90fc700b09484c20a13aaa3e4ea75edd05a175bf100c6484daee064 \
    https://downloads.wordpress.org/plugin/google-site-kit.1.192.0.zip /tmp/external-extensions/google-site-kit.zip
ADD --checksum=sha256:94df004d8de3cbdfeed523cf28a091ad9ce3690e2f7fa75b937ed1dd6b92ccc9 \
    https://downloads.wordpress.org/plugin/complianz-gdpr.7.5.9.zip /tmp/external-extensions/complianz-gdpr.zip
ADD --checksum=sha256:3714cf615d51f854774fca791ac20d7bd584dda4f1cd425c29ad275162c9b91e \
    https://downloads.wordpress.org/plugin/wp-consent-api.2.1.0.zip /tmp/external-extensions/wp-consent-api.zip
RUN mkdir /tmp/external-plugins \
    && for archive in /tmp/external-extensions/*.zip; do unzip -q "$archive" -d /tmp/external-plugins; done \
    && grep -Eq '^ \* Version: +1\.192\.0$' /tmp/external-plugins/google-site-kit/google-site-kit.php \
    && grep -Eq '^ \* Version: +7\.5\.9$' /tmp/external-plugins/complianz-gdpr/complianz-gpdr.php \
    && grep -Eq '^ \* Version: +2\.1\.0$' /tmp/external-plugins/wp-consent-api/wp-consent-api.php \
    && find /tmp/external-plugins -type d -exec chmod 0755 {} + \
    && find /tmp/external-plugins -type f -exec chmod 0644 {} +

FROM wordpress:7.1.0-php8.4-apache@sha256:b8f37de278183840a09f5a4b5bf5ec9f09177a9984d2fe5cc072b4388128bd9d

ARG GAMA_GIT_SHA
ARG GAMA_RELEASE_MARKER=release
LABEL org.opencontainers.image.source="https://github.com/grzegorzrzeznikiewicz/company-site" \
      org.opencontainers.image.revision="$GAMA_GIT_SHA" \
      com.gamasoftware.wordpress.release-marker="$GAMA_RELEASE_MARKER"

COPY --from=wp_cli /usr/local/bin/wp /usr/local/bin/wp
COPY wordpress/theme/gama-software /usr/src/wordpress/wp-content/themes/gama-software
COPY wordpress/plugins/gama-contact /usr/src/wordpress/wp-content/plugins/gama-contact
COPY wordpress/plugins/gama-seo /usr/src/wordpress/wp-content/plugins/gama-seo
COPY wordpress/plugins/gama-security /usr/src/wordpress/wp-content/plugins/gama-security
COPY wordpress/plugins/gama-local-mailpit /usr/src/wordpress/wp-content/plugins/gama-local-mailpit
COPY wordpress/plugins/gama-mail-transport /usr/src/wordpress/wp-content/plugins/gama-mail-transport
COPY --from=external_extensions /tmp/external-plugins/google-site-kit /usr/src/wordpress/wp-content/plugins/google-site-kit
COPY --from=external_extensions /tmp/external-plugins/complianz-gdpr /usr/src/wordpress/wp-content/plugins/complianz-gdpr
COPY --from=external_extensions /tmp/external-plugins/wp-consent-api /usr/src/wordpress/wp-content/plugins/wp-consent-api
COPY wordpress/bin/bootstrap /usr/local/bin/gama-wordpress-bootstrap
COPY wordpress/runtime/install-release /usr/local/bin/gama-wordpress-install-release

RUN rm -rf \
      /usr/src/wordpress/wp-content/plugins/akismet \
      /usr/src/wordpress/wp-content/plugins/hello.php \
      /usr/src/wordpress/wp-content/themes/twentytwentythree \
      /usr/src/wordpress/wp-content/themes/twentytwentyfour \
    && chmod 0755 /usr/local/bin/gama-wordpress-bootstrap /usr/local/bin/gama-wordpress-install-release \
    && find /usr/src/wordpress/wp-content/themes/gama-software /usr/src/wordpress/wp-content/plugins/gama-* -type d -exec chmod 0755 {} + \
    && find /usr/src/wordpress/wp-content/themes/gama-software /usr/src/wordpress/wp-content/plugins/gama-* -type f -exec chmod 0644 {} +
