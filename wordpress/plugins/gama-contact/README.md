# Gama Contact

Package identifier: `gama-software/gama-contact`. The plugin slug and text
domain are `gama-contact`, its PHP namespace is `GamaSoftware\Contact`, global
identifiers use `gama_contact_`, constants use `GAMA_CONTACT_`, future blocks
use `gama-software/*`, and future REST routes use `gama-contact/v1`.

Version `0.3.2` requires WordPress 7.1 and PHP 8.4 and is licensed under
GPL-2.0-or-later. It has no PHP or JavaScript dependencies, so it deliberately
has no Composer/npm manifest, `vendor`, or `node_modules`. There are no bundled
third-party assets requiring attribution.

## Form, security, and delivery

The dependency-free first-party implementation was chosen instead of a
third-party form plugin, so there is no extra license, recurring cost, activity
or vendor dependency to audit. The `[gama_contact_form]` shortcode renders the
theme-independent form with required name, e-mail, phone and message fields.
It validates and sanitizes on the server, preserves browser input after errors,
and sends plain-text mail through WordPress. Messages are not stored in the
database.

Submissions require a same-origin request and a WordPress nonce. A hidden
honeypot silently absorbs simple bots and a salted per-IP transient permits at
most five attempts per hour. CAPTCHA and a consent checkbox are deliberately
absent until traffic or the legal owner demonstrates that either is required.
Errors returned to visitors never expose transport or server details.

Configure the recipient and sender in deployment environment variables; never
export them through WordPress content or commit production values:

```dotenv
GAMA_CONTACT_RECIPIENT=founders@gama-software.com
GAMA_CONTACT_SENDER=no-reply@gama-software.com
```

The existing WordPress mail transport remains replaceable by SMTP/API
configuration at environment level without changing this plugin.

## Local and disposable installation

The repository's local runtime mounts this source directory read-only into both
WordPress services. `wordpress/bin/start` activates `gama-contact`
idempotently; do not try to install or update a ZIP over that mounted directory.
Verify the active source-mounted plugin and its only durable option with:

```sh
wordpress/bin/wp plugin is-active gama-contact
wordpress/bin/wp plugin get gama-contact --field=version
wordpress/bin/wp option get gama_contact_schema_version
```

To inspect the distributable rather than the source mount, build the ZIP and
use the repository's disposable, no-host-port lifecycle. It creates a unique
Compose namespace and removes that namespace and its volumes afterward:

```sh
wordpress/bin/package plugin gama-contact
wordpress/bin/test-package wordpress/dist/gama-contact-0.3.2.zip
```

For a separate disposable WordPress installation where the built ZIP is
available to WP-CLI, the equivalent operator flow is:

```sh
wp plugin install /absolute/path/to/gama-contact-0.3.2.zip
wp plugin activate gama-contact
wp plugin is-active gama-contact
wp plugin get gama-contact --field=version
wp option get gama_contact_schema_version
```

Do not use those standalone commands to write into production or the
repository's read-only Compose mounts.

## Activation, deactivation and reactivation

Activation idempotently stores only `gama_contact_schema_version=1`.
Deactivation stops the shortcode, REST route, assets, translations and form
delivery hooks without deleting the plugin files or that option. Reactivation
registers those runtime hooks again and idempotently restores the schema marker
to `1`. A theme switch does not affect either the active plugin or its data.

Use the source-mounted local runtime or an explicitly disposable installation,
then verify the state after each operation:

```sh
wordpress/bin/wp plugin deactivate gama-contact
wordpress/bin/wp plugin status gama-contact
wordpress/bin/wp option get gama_contact_schema_version
wordpress/bin/wp plugin activate gama-contact
wordpress/bin/wp plugin is-active gama-contact
wordpress/bin/wp option get gama_contact_schema_version
```

The expected option value before deactivation, while inactive and after
reactivation is `1`; the successful `is-active` check after reactivation proves
the form hooks are loaded again. Default uninstall removes the plugin files
through WordPress while preserving that durable option. Permanent deletion is
not implemented; a later version may add it only behind an explicit
Administrator choice with capability and nonce checks, an exact data inventory,
multisite handling, and integration coverage.

## Internationalization workflow

The user-facing source messages are Polish. PHP uses the `gama-contact` text
domain, and `src/Support/I18n.php` loads that domain on `init` from the installed
plugin's `languages/` directory. The current package deliberately contains only
the translation template `languages/gama-contact.pot`; its positive allowlist
does not yet admit locale files.

Prepare translations offline in a writable review copy, never inside an
immutable production installation or either read-only Compose mount. With a
reviewed WP-CLI i18n toolchain already available, refresh the template and
compile reviewed locale catalogues as follows:

```sh
wp i18n make-pot /path/to/review-copy/gama-contact \
  /path/to/review-copy/gama-contact/languages/gama-contact.pot \
  --domain=gama-contact
wp i18n make-mo /path/to/review-copy/gama-contact/languages
```

Name each translation pair `gama-contact-<locale>.po` and
`gama-contact-<locale>.mo`, for example `gama-contact-en_US.po` and
`gama-contact-en_US.mo`. Review the refreshed POT, every PO translation and its
compiled MO together. Including a locale requires a separate versioned package
update that adds only those reviewed PO/MO paths to the positive allowlist in
`wordpress/bin/package` and to the package contract. Until that change is
approved, packaging correctly rejects them as unexpected files. Rebuild and
test the ZIP after that review; never generate or edit catalogues in a running
production filesystem.

## Build and test

From the repository root:

```sh
wordpress/bin/validate-extensions-lock
wordpress/bin/package plugin gama-contact
wordpress/bin/test-package wordpress/dist/gama-contact-0.3.2.zip
```

`SOURCE_DATE_EPOCH` may be set to a non-negative Unix timestamp whose UTC date
is within ZIP's 1980–2107 range. When omitted, the package command uses the
current Git commit timestamp. The artifacts under `wordpress/dist` are local,
ignored build output and must not be uploaded, released, or distributed without
separate approval.
