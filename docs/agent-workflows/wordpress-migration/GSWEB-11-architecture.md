# GSWEB-11 WordPress package boundaries

This decision records Gate A for the repository structure. It separates
presentation from reusable behavior before GSWEB-12 and GSWEB-20 build on the
interfaces.

Gate A was approved on 2026-09-03 after the final GSWEB-11 fix re-review and
the independent GSWEB-12 brief re-review returned no findings. The exact
toolchain, schema integrity and ZIP-only browser decisions are recorded in
[`GSWEB-12-gate-a.md`](GSWEB-12-gate-a.md).

That approval is a historical decision about the initial boundary and does not
describe the packages as they exist today. At Gate A, `gama-contact` 0.1.0 was
a behavior-free lifecycle scaffold and `gama-software` was the GSWEB-10 runtime
scaffold. The current source contains the `gama-contact` 0.3.2 contact behavior
and the `gama-software` 0.4.1 production-theme foundation. The current commands,
allowlists and lifecycle below supersede the scaffold examples without changing
the approved ownership boundary.

## Versioned package layout

- `wordpress/theme/gama-software` is the first-party block-theme source.
- `wordpress/plugins/<slug>` is one independently installable first-party
  plugin per durable capability. `gama-contact` is the first such plugin.
- `wordpress/config` contains the versioned external-extension inventory and
  its schema.
- `wordpress/bin` contains the supported build, validation, and isolated
  package-test commands; `wordpress/tests` contains their contracts.
- `wordpress/dist` is ignored local build output and is never a source input.

Both local Compose services mount six first-party leaves individually and
read-only: the `gama-software` theme and the `gama-local-mailpit`,
`gama-mail-transport`, `gama-contact`, `gama-seo`, and `gama-security` plugins.
Their `themes` and `plugins` parents remain writable so the official image can
initialize Core. Package lifecycle tests do not use these source mounts: they
install one canonical ZIP into a generated disposable Compose project.

GSWEB-12 subsequently expanded the initial theme scaffold into the current
`gama-software` 0.4.1 theme package, with production metadata, the complete
licence, documentation, templates, parts, patterns, quality checks, and
packaging. The ownership decision remains unchanged.

## Ownership and runtime classification

The theme owns templates, template parts, patterns, Global Styles, and
presentation assets. A feature belongs in a plugin when it must survive a
theme change or owns mail, integration calls, endpoints, cron, capabilities,
durable content, options, schema, or migrations. The contact form and delivery
therefore live in `gama-contact`, independently of the active theme.

| Asset | Classification | Policy |
| --- | --- | --- |
| First-party theme/plugins | versioned code | Independently versioned, tested, and allowlist-packaged. |
| WordPress Core | pinned runtime input | Supplied by `wordpress:7.1.0-php8.4-apache`, never copied or patched in Git. |
| External plugins/themes | locked release input | Not vendored; GSWEB-23 will add reviewed entries to `extensions.lock.json`. |
| Database and uploads | persistent runtime state | Project volumes locally; backup/restore operationally; never packaged. |
| Cache, logs, and temp files | disposable runtime state | Rebuildable, ignored, and excluded from packages. |
| Local environment and secrets | runtime configuration | Only `.env.example` and variable names are versioned; values never enter packages or logs. |

## Package identity and dependencies

The plugin directory, slug, and text domain are `gama-contact`; version is
`0.3.2`; package identifier is `gama-software/gama-contact`; namespace is
`GamaSoftware\Contact`. Global identifiers/options/hooks use `gama_contact_`,
constants use `GAMA_CONTACT_`, future blocks use `gama-software/*`, and future
REST routes use `gama-contact/v1`. It requires WordPress 7.1 and PHP 8.4 and is
licensed GPL-2.0-or-later with the full licence in each ZIP.

Dependencies are package-local. Add `composer.json` only when PHP tooling or a
runtime dependency is actually used, commit `composer.lock`, and use
`composer install` in CI/builds. Add `package.json` only when a JS/CSS build is
actually used, commit `package-lock.json`, and use `npm ci`. Never commit or
package `node_modules`; do not package `vendor` for a dependency-free runtime.
Neither current package has a dependency manifest because neither consumes
either ecosystem.

External WordPress extensions use
`wordpress/config/extensions.lock.json`, validated against the closed Draft
2020-12 `extensions.schema.json` by
`wordpress/bin/validate-extensions-lock`. Each future entry must record type,
slug, exact version, canonical HTTP(S) source, SHA-256, licence, supported
WordPress/PHP ranges, purpose, and the owning Jira decision. GSWEB-23 owns
selection and the first non-empty lock. The validator is a focused PHP
implementation running in the already-pinned WP-CLI PHP 8.4 image; it reads the
schema and supports only the keywords the repository schema actually uses.

## Lifecycle and release contract

Activation and migrations are forward-only and idempotent. Version 0.3.2 owns
exactly `gama_contact_schema_version=1`. Activation sets that value, while
deactivation and theme switches preserve it. Reactivation is idempotent.
Default uninstall removes installed files and preserves the durable option.
Permanent deletion is intentionally absent; a future implementation requires
an explicit Administrator choice, capability and nonce checks, an exact data
inventory, multisite handling, and an integration test. The plugin resolves
all PHP, asset and translation locations from its installed main-file path, so
the ZIP is portable and never depends on a checkout path.

The supported build entry points are:

```sh
wordpress/bin/package plugin gama-contact
wordpress/bin/package theme gama-software
```

It accepts only the allowlisted type/slug, validates metadata and source paths,
rejects symlinks, unexpected material and secret-like content, and writes one
top-level `gama-contact/` directory into
`wordpress/dist/gama-contact-0.3.2.zip`. The sorted manifest and ZIP checksum
sit beside it. One validated `SOURCE_DATE_EPOCH` controls every ZIP timestamp;
when omitted it is derived from Git. File order and modes are fixed, making
unchanged builds byte-identical without changing tracked sources.

The current plugin allowlist is `CHANGELOG.md`, `LICENSE`, `README.md`,
`readme.txt`, `gama-contact.php`, `uninstall.php`, the two files under `assets/`,
`languages/gama-contact.pot`, the four files under `src/Form/`, the three files
under `src/Lifecycle/`, `src/Plugin.php`, and `src/Support/I18n.php`. The current
theme allowlist is `CHANGELOG.md`, `LICENSE`, `README.md`, `style.css`,
`functions.php`, `theme.json`, `languages/gama-software.pot`, the logo and four
icons under `assets/`, `parts/header.html`, `parts/footer.html`, the eight HTML
files under `templates/`, and the six PHP files under `patterns/`. Any
additional file, including a new translation PO/MO, must first be intentionally
reviewed and added to the positive allowlist and its package contract.

The real acceptance command is:

```sh
wordpress/bin/test-package wordpress/dist/gama-contact-0.3.2.zip
wordpress/bin/test-package wordpress/dist/gama-software-0.4.1.zip
```

It accepts only a matching regular, non-symlink artifact directly under
`wordpress/dist`. It uses a unique generated `gama-package-*` project for the
plugin or `gama-theme-package-*` for the theme, with disposable project-scoped
volumes, no host ports, no checkout source mounts, and the pinned
WordPress/PHP/WP-CLI/MariaDB inputs. Before startup it rejects resources already
carrying the exact generated project label.

The plugin lifecycle installs only the ZIP on clean Core, activates it,
exercises the form boundary, switches between installed Core themes, repeats
deactivation/reactivation, verifies option preservation and installed-only
class paths, then confirms default uninstall removes files but preserves the
schema option. The theme lifecycle installs only its ZIP, verifies installed
files against the archive, exercises Site Editor save and targeted revert,
theme switching, rendering and browser contracts, and restores the ZIP without
overwriting database-backed content. Both scan debug/container logs. Cleanup
removes and queries only the generated namespace; any residue-query failure is
a failure, while the original lifecycle failure status is preserved. Neither
path calls the `gama-wordpress` wrappers or touches their containers or volumes.

Artifacts are local and ignored. Building or testing does not authorize an
upload, release, WordPress.org publication, external attachment, or any other
distribution. Those actions require separate owner approval.

## Adding the next first-party plugin

1. Create `wordpress/plugins/<lowercase-kebab-slug>` using the scaffold's
   structure, not its contact-specific names or behavior.
2. Choose and document an identical slug/text domain, a unique
   `GamaSoftware\<Package>` namespace, global prefix, constant prefix, future
   block namespace, data inventory, and lifecycle policy.
3. Start at SemVer `0.1.0`, declare WordPress 7.1, PHP 8.4, and
   GPL-2.0-or-later consistently, and include the full GPL v2 text.
4. Keep durable behavior in the plugin and presentation in the theme. Add no
   dependency manifest until code or locked QA actually consumes it; when one
   is added, commit its lock and retain independent package builds.
5. Add the exact slug and file set to the positive packaging allowlist and add
   a read-only leaf mount to both local Compose services. Extend the resolved
   mount contract and package-content contract first so each fails before the
   implementation change.
6. Extend the dedicated clean-ZIP test to activate on Core, switch Core themes,
   repeat activation/deactivation, verify owned data and absence of unrelated
   side effects, test default uninstall policy, assert installed-only class
   paths, and scan all debug/runtime logs.
7. Add an external release-inventory entry only if the package becomes an
   approved external input. Review licence, security, compatibility, and Gate
   evidence before any distribution.
