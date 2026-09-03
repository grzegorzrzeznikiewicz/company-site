# Gama Contact

Package identifier: `gama-software/gama-contact`. The plugin slug and text
domain are `gama-contact`, its PHP namespace is `GamaSoftware\Contact`, global
identifiers use `gama_contact_`, constants use `GAMA_CONTACT_`, future blocks
use `gama-software/*`, and future REST routes use `gama-contact/v1`.

Version `0.1.0` requires WordPress 7.1 and PHP 8.4 and is licensed under
GPL-2.0-or-later. It has no PHP or JavaScript dependencies, so it deliberately
has no Composer/npm manifest, `vendor`, or `node_modules`. There are no bundled
third-party assets requiring attribution.

## Scope and lifecycle

This is a behavior-free scaffold for GSWEB-11. GSWEB-20 owns form fields,
validation, anti-spam, delivery, recipient configuration, and any privacy
review. This version registers no form, shortcode, block, REST route, mail,
cron event, role, capability, post type, content, or administrator setting.

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
wordpress/bin/test-package wordpress/dist/gama-contact-0.1.0.zip
```

`SOURCE_DATE_EPOCH` may be set to a non-negative Unix timestamp whose UTC date
is within ZIP's 1980–2107 range. When omitted, the package command uses the
current Git commit timestamp. The artifacts under `wordpress/dist` are local,
ignored build output and must not be uploaded, released, or distributed without
separate approval.
