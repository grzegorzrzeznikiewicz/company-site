# GSWEB-23 — security and update operations

## Runtime inventory

The reviewed baseline is WordPress 7.1 on PHP 8.4. The only active extensions
are the first-party `gama-contact` 0.3.1, `gama-local-mailpit` 0.1.0,
`gama-mail-transport` 0.1.0, `gama-security` 0.1.1 and `gama-seo` 0.1.0
plugins, plus the first-party
`gama-software` 0.4.0 theme. All use GPL-2.0-or-later and have no paid runtime
dependency. The Mailpit transport is active only in non-production environments
and is explicitly deactivated by a production bootstrap. The production SMTP
transport reads its host, port, credentials and encryption only from runtime
environment variables; deployment rejects Mailpit, localhost, missing
credentials and unencrypted configuration. The runtime independently applies
the same syntax checks and short-circuits `wp_mail()` with failure instead of
falling back to PHP `mail()` when production SMTP is invalid.
`twentytwentyfive` 1.5 remains
inactive as the emergency fallback
theme; unused default plugins and older default themes are deleted by the
idempotent bootstrap.

`wordpress/config/extensions.lock.json` is the authoritative allowlist for any
future external extension. It is intentionally empty. An external plugin may be
introduced only as a separately estimated Jira task with its version, source,
license, data-processing impact, security ownership, update policy and exit
plan reviewed before installation.

## Least privilege

Editors can edit and publish posts/pages, upload media and enter the Site
Editor. They cannot install, activate, update or edit plugins/themes, switch
themes, update core, manage options, promote users or edit users. Administrators
retain deployment and account-management duties. The extra Editor permission is
resolved at request time by `gama-security`; it is not persisted into the
database and therefore cannot drift across environments.

## Request and authentication controls

`gama-security` removes the public generator disclosure, returns generic login
errors, emits `nosniff`, `SAMEORIGIN`, a strict-origin referrer policy and a
minimal permissions policy. HSTS is emitted only for an HTTPS production
request. Repeated login failures are keyed by a salted username/address digest,
bounded to ten failures per 15 minutes and serialized with a MariaDB advisory
lock. The contact form has its own same-origin nonce, honeypot, validation and
atomic per-address limiter and does not persist message content.

WordPress file editing and dashboard file modifications, automatic background
updates and automatic core updates are disabled in immutable deployments.
Production admin traffic is HTTPS-only; the reverse proxy must
set `X-Forwarded-Proto: https`. Secrets and mail addresses are supplied by the
environment and are never exported with content or committed.

## Controlled update procedure

1. Create a Jira subtask and update the pinned version/checksum or first-party
   SemVer in source. Never update a production extension from wp-admin.
2. Run source contracts, PHPCS, reproducible package checks and the disposable
   ZIP lifecycle.
3. Restore the latest backup into the isolated rehearsal environment and run
   the browser regression suite, role matrix, headers, login throttling,
   contact delivery and SEO checks.
4. Deploy the exact checked artifact to staging, record its checksum and obtain
   the release approval required by Gate C.
5. Deploy the same immutable artifact to production using the pipeline. Verify
   health, logs and smoke tests. Roll back the artifact and restore the captured
   database/uploads backup if the release gate fails.

Security updates are expedited through the same gates; bypassing the artifact
or restore checks is not an accepted emergency procedure.
