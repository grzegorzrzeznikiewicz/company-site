# Gama Contact

Package identifier: `gama-software/gama-contact`. The plugin slug and text
domain are `gama-contact`, its PHP namespace is `GamaSoftware\Contact`, global
identifiers use `gama_contact_`, constants use `GAMA_CONTACT_`, future blocks
use `gama-software/*`, and future REST routes use `gama-contact/v1`.

Version `0.2.0` requires WordPress 7.1 and PHP 8.4 and is licensed under
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

## Lifecycle

Activation idempotently stores only `gama_contact_schema_version=1`.
Deactivation preserves it. Default uninstall removes the plugin files through
WordPress while preserving that durable option. Permanent deletion is not
implemented; a later version may add it only behind an explicit Administrator
choice with capability and nonce checks, an exact data inventory, multisite
handling, and integration coverage.

## Build and test

From the repository root:

```sh
wordpress/bin/validate-extensions-lock
wordpress/bin/package plugin gama-contact
wordpress/bin/test-package wordpress/dist/gama-contact-0.2.0.zip
```

`SOURCE_DATE_EPOCH` may be set to a non-negative Unix timestamp whose UTC date
is within ZIP's 1980–2107 range. When omitted, the package command uses the
current Git commit timestamp. The artifacts under `wordpress/dist` are local,
ignored build output and must not be uploaded, released, or distributed without
separate approval.
