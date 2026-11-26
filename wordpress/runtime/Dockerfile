FROM wordpress:cli-2.12.0-php8.4@sha256:1e1d1485277d15e0331b598b6e19972243128ead978b7134d758097d82116b99 AS wp_cli

FROM wordpress:7.1.5-php8.4-apache@sha256:98a3fba3639b89fe1ade0cf6d37e61bc8934de872cf26d9dc5286962b554e3d1

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
