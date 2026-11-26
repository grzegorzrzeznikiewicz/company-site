# Gama Software Website

[![WordPress Quality Gates](https://github.com/grzegorzrzeznikiewicz/company-site/actions/workflows/wordpress-ci.yml/badge.svg)](https://github.com/grzegorzrzeznikiewicz/company-site/actions/workflows/wordpress-ci.yml)
[![WordPress Production Deployment](https://github.com/grzegorzrzeznikiewicz/company-site/actions/workflows/wordpress-production.yml/badge.svg)](https://github.com/grzegorzrzeznikiewicz/company-site/actions/workflows/wordpress-production.yml)

Company website for Gama Software, <https://gama-software.com>. Since the
2026-09-30 cutover the site runs only on WordPress: a first-party block theme
plus small first-party plugins, edited in the WordPress Site Editor.

The former React/Vite frontend and Symfony/PostgreSQL contact API were retired
in GSWEB-30. Their last full source is preserved by the Git tag
`legacy-react-symfony-final`; see [Legacy stack](#legacy-stack).

Release history: [CHANGELOG.md](CHANGELOG.md).

## Requirements

- Docker with Docker Compose

Local `php`, `node` and `composer` are not required; every tool runs in a
pinned container.

## Local development

```bash
cp wordpress/.env.example wordpress/.env
wordpress/bin/start
```

- Site: `http://localhost:8090`
- WordPress admin: `http://localhost:8090/wp-admin/`
- Test email inbox (Mailpit): `http://localhost:8027`

The example local administrator is set in `wordpress/.env` (see
`wordpress/.env.example`). Local mail never leaves Mailpit.

```bash
wordpress/bin/start       # start and idempotently bootstrap WordPress
wordpress/bin/stop        # stop only gama-wordpress containers
wordpress/bin/restart     # recreate containers without deleting data
wordpress/bin/logs        # follow logs
wordpress/bin/wp core version
wordpress/bin/test-mail   # prove outbound local mail reaches Mailpit
```

`wordpress/bin/reset --confirm` and `wordpress/tests/runtime-smoke.sh --clean`
are destructive. Inspect `wordpress/bin/reset --list-targets` first and never
run them against a preview you want to keep.

## Packages

| Package | Path | Version |
| --- | --- | --- |
| Theme `gama-software` | [`wordpress/theme/gama-software`](wordpress/theme/gama-software/README.md) | 0.4.2 |
| Plugin `gama-contact` (contact form) | [`wordpress/plugins/gama-contact`](wordpress/plugins/gama-contact/README.md) | 0.3.3 |
| Plugin `gama-seo` | [`wordpress/plugins/gama-seo`](wordpress/plugins/gama-seo/README.md) | 0.1.0 |
| Plugin `gama-security` | [`wordpress/plugins/gama-security`](wordpress/plugins/gama-security/README.md) | 0.1.1 |
| Plugin `gama-mail-transport` (production SMTP) | [`wordpress/plugins/gama-mail-transport`](wordpress/plugins/gama-mail-transport/README.md) | 0.1.0 |
| Plugin `gama-local-mailpit` (local only) | `wordpress/plugins/gama-local-mailpit` | 0.1.0 |
| External plugin `google-site-kit` (Site Kit by Google) | pinned in [`wordpress/config/extensions.lock.json`](wordpress/config/extensions.lock.json), not vendored | 1.192.0 |

Build and verify a package:

```bash
wordpress/bin/package theme gama-software
wordpress/tests/theme-contract.sh
wordpress/bin/package plugin gama-contact
wordpress/tests/plugin-package-contract.sh
wordpress/bin/test-package wordpress/dist/gama-contact-0.3.3.zip
```

Files in `wordpress/dist` are ignored local artifacts. Do not upload or
distribute them without owner approval.

Adding or changing a theme feature or plugin: see
[`docs/EXTENDING.md`](docs/EXTENDING.md).

## CI and releases

- [`wordpress-ci.yml`](.github/workflows/wordpress-ci.yml) — four required
  quality gates on every PR and push to `main`.
- [`wordpress-production.yml`](.github/workflows/wordpress-production.yml) —
  promotes the exact CI-built image of a merged `main` commit to production
  when the repository variable `GAMA_DEPLOYMENT_MODE` is `wordpress` and the
  merged PR carries the owner-recorded `GAMA-SOLO-AI-REVIEW-V1` report for its
  exact head SHA, submitted before the merge.
- [`wordpress-production-rollback.yml`](.github/workflows/wordpress-production-rollback.yml)
  — owner-approved manual recovery.

Release, backup, restore and rollback procedures are documented in
[`docs/agent-workflows/wordpress-migration/`](docs/agent-workflows/wordpress-migration/README.md)
(GSWEB-24, GSWEB-26 and GSWEB-29).

## Project structure

```text
.
├── wordpress/
│   ├── theme/gama-software/   # block theme (templates, parts, patterns, theme.json)
│   ├── plugins/               # first-party plugins, one capability each
│   ├── config/                # external-extension lock and schema
│   ├── bin/                   # local runtime, packaging and release commands
│   ├── tests/                 # contract, runtime and release tests
│   ├── qa/                    # pinned QA toolchains and Playwright specs
│   ├── release/, routing/     # production release and routing tooling
│   └── runtime/, deploy/      # production image and Compose files
├── docs/                      # migration records, editor guides, extension guide
└── .github/workflows/         # WordPress CI, production release and rollback
```

## Legacy stack

The React 18/Vite frontend (`src/`), Symfony 8 contact API and EasyAdmin panel
(`backend/`), their Docker/CI files and `bin/*` wrappers were removed in
GSWEB-30 after the owner's Gate D decision on 2026-11-26. To inspect or rebuild
them, check out the tag:

```bash
git fetch origin tag legacy-react-symfony-final
git checkout legacy-react-symfony-final
```

The tag points at the last `main` commit that still contained the full legacy
source and its CI/deploy workflows.

## License

Copyright © 2026 Gama Software. All rights reserved. The WordPress theme and plugins
are licensed GPL-2.0-or-later, as declared in their headers.
