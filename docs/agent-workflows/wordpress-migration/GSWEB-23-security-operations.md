# GSWEB-23 — security and update operations

## Runtime inventory

The reviewed baseline is WordPress 7.1 on PHP 8.4. The only active extensions
are the first-party `gama-contact` 0.3.2, `gama-local-mailpit` 0.1.0,
`gama-mail-transport` 0.1.0, `gama-security` 0.1.1 and `gama-seo` 0.1.0
plugins, plus the first-party
`gama-software` 0.4.1 theme. These versions were checked against package metadata
and the local WP-CLI inventory on 2026-09-06. All use GPL-2.0-or-later and have no paid runtime
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

## Administrator account runbook

Account changes are production data changes. Only a named, authenticated
Administrator may perform the normal wp-admin steps below. Never use a shared
account, put a password or reset link in Jira/evidence, or give Administrator to
a user whose work fits the Editor role.

### Create an account

1. Require an approved ticket naming the person, business purpose, environment,
   requested role, accountable owner and review/removal date. Search the current
   user list for the login and email before creating anything.
2. Use **Users → Add New** over the production HTTPS origin. Create a named
   account with Editor by default. Administrator requires a separately recorded
   need and owner approval; never promote merely to work around a denied Editor
   capability.
3. Use WordPress's generated strong password. Send an invitation through the
   configured production mail path only after mail delivery is verified, or
   provide the credential through the owner's approved out-of-band secret
   channel. Do not retain the generated password.
4. Have the person confirm notification and login in the exact approved target.
   In staging, have an Editor edit only the designated acceptance draft, then
   verify that plugin/theme installation, settings and user administration stay
   denied. Re-open the user record and verify the exact role. Record only the
   ticket, WordPress user ID/login, role, operator, time and verification
   result.

### Reset or recover access

1. Verify the requester against the account owner through a channel independent
   of the locked account. Confirm the exact login/email and record the request;
   never accept only an email or chat message as identity proof.
2. Prefer WordPress's **Lost your password?** flow when the registered mailbox
   and production delivery are known to work. Otherwise a different named
   Administrator may use **Users → Edit → Set New Password** and transfer the
   generated password through the approved secret channel. Never send it in the
   ticket or ordinary chat.
3. The user signs in, replaces any administrator-set password promptly and
   signs out other sessions from their profile. For suspected compromise,
   suspend further account work, preserve the security/log evidence and require
   the incident owner to confirm session invalidation and any role/email changes
   before closing the ticket.
4. If no named Administrator can authenticate, stop the normal procedure. A
   repository document is not break-glass authority: the owner and
   infrastructure operator must approve a bounded recovery window, confirm a
   fresh backup, recover only the exact account through an audited host-side
   procedure, verify login/role, and remove any temporary recovery access.

### Deactivate or remove an account

1. Require owner approval for the exact WordPress user ID and inventory the
   account's posts/pages before deletion. Confirm a fresh recoverable backup and
   select a named, active destination user for content ownership. Never select
   **Delete all content** for production content.
2. For an immediate departure or suspected compromise, a different named
   Administrator first blocks the exact account's access using the approved
   WordPress password/session controls and verifies its old login is rejected.
   Do not change any unrelated user.
3. A different named Administrator removes the account under **Users** and
   chooses **Attribute all content to** the approved destination. Do not delete
   the last usable Administrator or the account performing the operation. If
   the reassignment target or ownership is unclear, stop without deleting.
4. Verify that the old login is rejected, the reassigned content remains
   published with the intended owner, and the Administrator/Editor matrix still
   holds. Record IDs, roles, counts, operator, time and result, but no personal
   secrets or reset material.

The retained disposable Administrator/Editor acceptance evidence demonstrates
the role matrix and account exercise mechanics only. It does not prove an owner
account was provisioned, target mail was delivered, host recovery was performed
or a real account was removed. Each target-specific operation still needs its
fresh approval and verification.

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

The security owner and designated operator perform this review once every
calendar month, even when no update is released. The monthly ticket records the
installed Core, theme and plugin versions, upstream security/update notices,
the empty-or-reviewed external-extension allowlist, and either the candidate
Jira tasks or an explicit "no change" result. Every update follows the existing
pinned-artifact, CI, staging, rollback and approval gates below. This cadence
does not enable automatic updates or schedule unattended deployment. Missed
reviews are overdue operational work; they are not silently rolled into the
next month. Critical security notices start the same procedure immediately
rather than waiting for the monthly date.

1. Create a Jira subtask and update the pinned version/checksum or first-party
   SemVer in source. Never update a production extension from wp-admin.
2. Run source contracts, PHPCS, reproducible package checks and the disposable
   ZIP lifecycle.
3. Restore the latest backup into the isolated rehearsal environment and run
   the browser regression suite, role matrix, headers, login throttling,
   contact delivery and SEO checks.
4. Deploy the exact checked artifact to staging, record its checksum and obtain
   the release approval required by Gate C.
5. Only after Gate C and fresh owner approval for the deployment window, deploy
   the same immutable artifact to production using the pipeline. Verify health,
   logs and smoke tests. A code rollback must retain the current database and
   uploads. Do not automatically restore their pre-release backup: that can
   discard legitimate writes. Data recovery requires a separate owner decision
   and a verified restore into a fresh replacement namespace, followed by an
   approved traffic switch; see [the backup/restore procedure](GSWEB-24-backup-restore.md)
   and [the cutover runbook](GSWEB-28-staging-acceptance.md).

Security updates are expedited through the same gates; bypassing the artifact
or restore checks is not an accepted emergency procedure.
