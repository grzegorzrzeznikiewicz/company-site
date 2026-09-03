# GSWEB-12 Gate A decision

Status: **APPROVED** on 2026-09-03 (Europe/Warsaw).

This gate records the reviewed inputs that GSWEB-12 may consume. It follows
the owner's approval to execute the complete GSWEB-8 epic and two independent
review cycles: GSWEB-11's final range `edcf80d..aeaf1c8` was approved with no
findings, and the amended GSWEB-12 implementation brief was approved after its
runtime, schema, browser, reset and packaging contracts were made executable.

## Accepted package boundary

- Theme presentation lives in `wordpress/theme/gama-software`; durable contact
  behavior lives in the independently installable `gama-contact` plugin.
- WordPress Core, external extensions, database, uploads, caches, logs,
  environment values and secrets are never theme/plugin package inputs.
- First-party packages use exact positive allowlists, one top-level directory,
  stable file order/modes/timestamps, a sorted manifest and SHA-256.
- Package acceptance installs only a canonical regular, non-symlink ZIP from
  `wordpress/dist` in a unique, label-checked disposable Compose project.
  Cleanup failures are failures and the final container, volume and network
  label queries must all succeed with empty output.
- The accepted runtime minima are WordPress 7.1 and PHP 8.4. Package metadata
  uses SPDX `GPL-2.0-or-later`; WordPress's human-readable theme header uses
  the explicitly mapped `GPL v2 or later` spelling and includes the full GPL
  v2 licence text.
- No artifact may be pushed, uploaded, attached, released, installed on a
  shared host or deployed by this gate.

The accepted `gama-contact` 0.1.0 artifact has SHA-256:

```text
daa72e164ef5bf60ba772501e8b61b5dcf7451ff4600cc0df5ada4e9ac0c8c17
```

## Immutable runtime inputs

These are multi-platform index digests resolved and independently checked on
2026-09-03. They support both linux/amd64 and linux/arm64; an
architecture-specific child manifest must not replace them.

```text
wordpress:cli-2.12.0-php8.4@sha256:1e1d1485277d15e0331b598b6e19972243128ead978b7134d758097d82116b99
wordpress:7.1.0-php8.4-apache@sha256:b8f37de278183840a09f5a4b5bf5ec9f09177a9984d2fe5cc072b4388128bd9d
mariadb:10.11.18-jammy@sha256:8020e05c4c498d06c87f0a1db010eb79bd6f8fb30e9b763d4690c34ce1e61008
composer:2.10.3@sha256:4d045ea9f71d5d111a95e608400da61d187e487adf9eaf2dfe068998a8d4f584
mcr.microsoft.com/playwright:v1.54.2-noble@sha256:18b4bcff4f8ba0ac8c44b09f09def6a4f6cb8579e5f26381c21f38b50935d5d8
```

The Composer image is only the source of the Composer 2.10.3 executable in a
multi-stage QA image. Its final stage is the pinned WP-CLI/PHP 8.4 image, so
`composer check-platform-reqs` evaluates the real PHP 8.4 runtime rather than
the PHP 8.5 runtime currently present in the Composer image.

## Static QA contract

The exact development dependencies live under `wordpress/qa`, outside the
18-file theme package:

- `dealerdirect/phpcodesniffer-composer-installer` 1.2.1;
- `opis/json-schema` 2.6.0;
- `squizlabs/php_codesniffer` 3.13.6;
- `wp-coding-standards/wpcs` 3.4.1.

`composer.lock` is versioned, the installer plugin is explicitly allowed, and
validation may run `composer validate --strict --check-lock`, `composer
install --no-interaction --prefer-dist --no-progress` and `composer
check-platform-reqs`, never `composer update`.

PHPCS must discover the WordPress standards and run the aggregate `WordPress`
ruleset over every theme PHP file, with minimum WordPress 7.1, text domain
`gama-software` and global prefix `gama_software`. Blanket exclusions are not
accepted.

The exact schema reached through
`https://schemas.wp.org/wp/7.1/theme.json` is vendored unchanged with SHA-256:

```text
718d6e0109a06933eea29d8261ebdf5fcfabe4926bcfb30c44e2e16a3a535f9a
```

It declares JSON Schema Draft-07. `opis/json-schema` may support newer drafts,
but validation must honor the schema's declared Draft-07 dialect, run from the
local file with networking disabled, assert the theme's exact `$schema` URL,
and include a mutation that proves invalid data is rejected.

The pinned WP-CLI 2.12.0 image generates POT files with its bundled i18n
command, fixed locale/timezone/headers and no `--skip-theme-json`. Two clean
runs must be byte-identical to the versioned POT and contain known strings from
both `theme.json` and PHP.

## ZIP-only browser contract

The original GSWEB-11 package Compose contract remains unchanged. GSWEB-12 may
compose a separate theme-only extension that adds a Playwright service on the
internal project network without publishing a host port or mounting checkout
source into WordPress.

The browser image contains a dedicated `wordpress/qa/e2e` package and lock
with Node `22.*` and exact `@playwright/test` 1.54.2. It does not install the
legacy React application's Node 24 dependency tree. Tests and configuration
are baked into the image. They authenticate to the disposable WordPress by
service name, exercise all Site Editor templates/parts, record browser errors,
and retain the canonical-ZIP, exact-label preflight and zero-residue cleanup
guarantees from `aeaf1c8`.

Gate A is an implementation gate only. Staging, production cutover and old
stack retirement remain governed by their later gates and fresh live-operation
authority.
