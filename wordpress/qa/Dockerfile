FROM composer:2.10.3@sha256:4d045ea9f71d5d111a95e608400da61d187e487adf9eaf2dfe068998a8d4f584 AS composer_source

FROM wordpress:cli-2.12.0-php8.4@sha256:1e1d1485277d15e0331b598b6e19972243128ead978b7134d758097d82116b99

USER root
COPY --from=composer_source /usr/bin/composer /usr/local/bin/composer
WORKDIR /qa
COPY wordpress/qa/composer.json wordpress/qa/composer.lock ./
RUN test "$(php -r 'echo PHP_MAJOR_VERSION.".".PHP_MINOR_VERSION;')" = "8.4" \
    && test "$(composer --version --no-ansi | awk '{print $3}')" = "2.10.3" \
    && test "$(wp --version --allow-root | awk '{print $2}')" = "2.12.0" \
    && composer validate --strict --check-lock \
    && composer install --no-interaction --prefer-dist --no-progress \
    && composer check-platform-reqs
COPY wordpress/qa/phpcs.xml.dist wordpress/qa/phpcs-plugins.xml.dist wordpress/qa/phpstan.neon.dist ./
COPY wordpress/qa/phpstan-bootstrap.php ./
COPY wordpress/qa/validate-theme-json.php wordpress/qa/extract-theme-json-i18n.php ./
USER 33:33
