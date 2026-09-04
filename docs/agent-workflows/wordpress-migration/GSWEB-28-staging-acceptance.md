# GSWEB-28 — staging acceptance and migration runbook

## Acceptance scope

The rehearsal starts from a fresh, isolated `gama-wp-staging-*` namespace and
deploys the immutable candidate produced by `wordpress/bin/build-release`.
Database, uploads and installed Core are named persistence boundaries. Staging
uses `noindex`, `example.test` recipients and Mailpit; it cannot deliver to a
real recipient. The exact image ID, project name, test reports and traces are
recorded by `wordpress/tests/staging-rollback-runtime.sh`.

The candidate must pass all of the following before Gate C:

- public desktop/mobile navigation, logo, contact form, URL, WCAG 2.1 AA and
  performance budgets;
- Editor changes to Hero/CTA, menu, footer, services, modules, posts and media
  without code access;
- Editor denial for plugins, users, settings, Core updates and administrator
  promotion;
- Administrator access to users, installed plugins and Site Health, plus a
  create/delete Editor account exercise;
- delivery into the isolated mail sink and the public blog/content inventory;
- candidate deployment, database/media persistence and rollback to the exact
  previous image.

## Editing instructions

1. Sign in at `/wp-login.php`. Editors use **Appearance → Editor** for the
   header, navigation, footer, Hero, services, modules and contact section.
2. Use **Posts** to create, publish, update or return an article to draft. Use
   the Media Library to upload an image and always provide meaningful alt text,
   except for intentionally decorative images where an empty alt is correct.
3. Preview desktop and mobile before saving. Keep the established heading order,
   approved palette and existing section anchors (`services`, `modules`,
   `contact`), because the menu and CTA links depend on them.
4. Administrators manage accounts and inspect Site Health. Theme, plugin and
   WordPress Core releases are deployed as reviewed images; the dashboard must
   not be used to install or update production code.
5. Privacy policy and terms remain drafts until their legal wording is approved.
   Do not publish their placeholder copy.

## Production migration runbook

### Ownership and required inputs

| Responsibility | Owner at Gate C | Required input |
| --- | --- | --- |
| Product/content acceptance | Grzegorz Rzeźnikiewicz | staging and known-deviation approval |
| Release execution and evidence | repository release operator | successful CI SHA and immutable image digest |
| Production host, TLS and routing | infrastructure operator named for the window | host access, certificate paths, proxy/DNS change method |
| Backup and restore | infrastructure operator named for the window | off-host destination and latest verified restore point |
| Stabilization decision | Grzegorz Rzeźnikiewicz with release operator | duration, metrics and rollback authority |

The infrastructure operator, exact deployment window and stabilization duration
must be recorded in the Gate C decision. They are intentionally not guessed by
the repository.

### Preflight and GO/NO-GO

1. Record the production WordPress host, current React/Symfony release, DNS/proxy
   owner and all resources shared with other projects. Do not remove anything.
2. Require green `WordPress Quality Gates` for the selected commit. Promote the
   exact staging-tested `ghcr.io/...@sha256:<digest>`; never rebuild or promote a
   moving tag.
3. Create a new off-host backup with `wordpress/bin/backup`, verify its
   `SHA256SUMS`, and confirm a recent full restore drill. A stale or local-only
   backup is NO-GO.
4. Confirm production secrets exist only in the protected deployment environment
   and host `.env`; confirm SMTP uses the approved real provider, not Mailpit.
5. Confirm TLS paths, apex redirect, health checks, free capacity, monitoring,
   rollback digest and the legacy routing target. Any missing owner, digest,
   credential, certificate or rollback target is NO-GO.

### Cutover (GSWEB-29 only after fresh approval)

1. Freeze content changes for the agreed window and note UTC start time.
2. Deploy the approved image into the production WordPress namespace without
   changing public traffic. Run the one-shot Core installer and idempotent
   bootstrap, preserving database and uploads.
3. Verify `/`, `/blog/`, a post, `/wp-login.php`, `/wp-admin/`, the logo, menu,
   contact validation, a controlled real-mail delivery, canonical URLs, HTTPS
   headers, `robots.txt`, sitemap and monitoring.
4. Switch only the documented proxy/DNS routing target to WordPress. Record the
   exact change, operator and UTC timestamp.
5. Repeat public smoke, WCAG/performance probes and contact delivery. Monitor
   HTTP 5xx, latency, PHP errors, database health and mail failures for the
   accepted stabilization duration.

### Rollback

1. For a code-only defect, run `wordpress/bin/rollback-staging`'s production
   equivalent with the recorded previous immutable digest; retain database and
   uploads.
2. For an unsafe cutover, route traffic back to the recorded React/Symfony
   target. Do not delete the WordPress database or uploads.
3. Restore data only into a fresh replacement namespace with
   `wordpress/bin/restore`; database rollback needs an explicit owner decision
   because it can discard writes made after cutover.
4. Record the incident, evidence and final routing state. GSWEB-30 remains
   forbidden until Gate D after stabilization.

## Known deviations and initial Gate C state

- Legal pages contain owner-review placeholders and remain drafts.
- Staging intentionally differs from production in mail transport, indexing,
  hostname, TLS certificate and secrets.
- A native-browser 200% zoom and human assistive-technology spot check remains
  an owner acceptance item; automation covers reflow, keyboard use and WCAG
  rules but does not claim to replace that human check.
- The production infrastructure operator, deployment window and stabilization
  duration have not yet been supplied.

Until the independent rehearsal review is green and the owner explicitly
accepts this runbook, the known deviations and a concrete window, Gate C is
**NO-GO**. No command in GSWEB-28 changes production traffic.
