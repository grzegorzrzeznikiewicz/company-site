# GSWEB-29 — gated production pipeline

The repository now contains a production path, but it is deliberately inert
until Gate C is formally GO and an owner starts an approved window. Neither
workflow runs on push, pull request or a schedule.

## Exact release promotion

`.github/workflows/wordpress-staging.yml` publishes
`wordpress-staging-release-<git-sha>` only after the immutable image has been
deployed to staging and its public health/noindex check has passed. The artifact
records the full Git SHA, exact GHCR digest and staging workflow run ID.

`.github/workflows/wordpress-production.yml` accepts that SHA, staging run ID
and the approved UTC window. It rejects a failed or different staging run,
requires green WordPress quality gates, downloads the evidence and verifies the
OCI revision label. The accepted immutable reference is either the documented
`ghcr.io/<owner>/gama-wordpress:sha-<accepted-sha>@sha256:<digest>` form emitted
by staging or the untagged repository-at-digest form. A SHA tag must equal the
approved Git SHA; mutable tags, other SHA tags and malformed digests are
rejected. Production never rebuilds the image. The two mutating jobs use
separate protected GitHub environments:

- `wordpress-production` deploys the candidate into an isolated
  `gama-wp-production-candidate-<run-id>` namespace on a dynamic loopback port,
  performs local smoke and controlled encrypted SMTP delivery, and cannot
  replace the stable service;
- `wordpress-production-cutover` verifies that exact candidate, proves the
  configured backup mount source, backs up a healthy existing stable namespace
  (or requires it to be completely absent), deploys the exact image to the
  stable namespace, invokes the infrastructure-owned, root-owned
  `/usr/local/sbin/gama-wordpress-cutover` hook and verifies the public HTTPS
  home, blog, login and indexability.

Both environments must have required reviewers configured before the workflow
is enabled. Starting the workflow is not a substitute for the separate cutover
approval on the second environment.

The candidate project is removed with its three candidate-only volumes after
the rehearsal by an EXIT trap. An `always()` cleanup job repeats the same
strictly run-scoped removal, and the rehearsal also clears that exact namespace
before a retry. None of these cleanup paths accepts the stable project name.

## Required host configuration

The host owns `/srv/gama-wordpress-production/.env`. It must be a regular file
containing production database, WordPress administrator, contact sender and
recipient values plus:

```dotenv
WP_ENVIRONMENT_TYPE=production
WP_HOME=https://gama-software.com
WORDPRESS_HTTP_PORT=8080
GAMA_MAIL_SINK_HOST=
GAMA_SMTP_HOST=smtp.provider.example
GAMA_SMTP_PORT=587
GAMA_SMTP_USERNAME=secret-at-runtime
GAMA_SMTP_PASSWORD=secret-at-runtime
GAMA_SMTP_ENCRYPTION=tls
```

The illustrative host, user and credentials above are not repository defaults.
The real values belong only to the protected environment and host file. The
workflow also requires `PRODUCTION_BACKUP_ROOT` to be an existing mounted
off-host path, `PRODUCTION_BACKUP_EXPECTED_SOURCE` to exactly match its audited
`findmnt` source, and `PRODUCTION_SMOKE_RECIPIENT` to be the approved controlled
mailbox. Server, SSH and GHCR credentials use the `PRODUCTION_*` secret names in
the workflow. A mount alone is not acceptance evidence: its source and the
fresh restore drill remain explicit Gate C records.

The SSH operator may be non-root, but its production provisioning must authorize
the workflow's explicit `sudo` operations. Root retains ownership of the
installed tools and hooks (`0750`), candidate/deployment evidence (`0600`) and
backup directories/files (`0700`/`0600`). Tool, hook and evidence integrity
checks run through that same privilege boundary; backup verification elevates
the directory traversal and `sha256sum -c` together. The workflow does not
broaden those modes or require root SSH login.

The workflow never copies the secret-bearing host `.env` into a release
directory. Only non-secret release evidence (SHA, immutable image, previous
image, window and backup reference/source) is retained root-readable. All
third-party actions that receive production or staging credentials are pinned
to full commit SHAs.

The cutover hook is infrastructure-owned because this repository cannot infer
whether the real route is Nginx, a load balancer or DNS. It must accept:

```text
gama-wordpress-cutover --project gama-wp-production --port 8080 \
  --image <immutable-reference> --deployment-run-id <run-id>
```

It must atomically target the already healthy local WordPress port, preserve the
recorded legacy route and fail non-zero when it cannot verify the change. The
pipeline refuses a missing hook, a non-root-owned hook or one writable by group
or others.

## Rollback and GSWEB-30 boundary

`.github/workflows/wordpress-production-rollback.yml` is also manual and uses
the protected `wordpress-production-rollback` environment. `code-only` first
backs up the current WordPress database and uploads off-host, then redeploys the
exact previous immutable image while retaining both volumes.
`routing-to-legacy` intentionally does not wait for a backup; it calls the root-owned
`/usr/local/sbin/gama-wordpress-rollback-routing` hook. It never imports a
database, removes volumes or deletes the React/Symfony stack.

The legacy-routing branch runs independently of WordPress container and backup
health so it remains available during a total application failure. If the
public smoke after cutover fails, the deployment workflow invokes the same
legacy hook automatically and keeps the run failed for investigation.

The rollback hook must accept `--target legacy`, `--deployment-run-id` and
`--rollback-run-id`, then verify that the saved legacy route is public. Data
restore remains the isolated GSWEB-24 process and needs a separate owner
decision.

GSWEB-30 is not automated here. Legacy removal stays forbidden until the
accepted stabilization period is complete, Gate D is GO and the owner gives a
fresh destructive approval for an exact inventory.

## Current execution status

The pipeline and contracts are implemented and were published on
`feature/GSWEB-9` in [PR #8](https://github.com/grzegorzrzeznikiewicz/company-site/pull/8)
on 2026-09-06 with owner approval. They have not been merged into `main` or run
against production; no real SMTP message has been sent, and no traffic or
production data has been changed. Remote CI is recorded on the PR; the first
Linux release-regression job passed its isolated production-model rehearsal,
which is not a real production deployment. The read-only
GitHub audit found no protected WordPress deployment environments or their
`STAGING_*` / `PRODUCTION_*` secrets. Environment configuration, public staging
acceptance, production host inputs and a fresh deployment-window approval remain
Gate C requirements.

`wordpress/tests/production-deployment-runtime.sh` separately proves on an
ephemeral Docker namespace: isolated candidate deployment, first stable deploy,
an authenticated STARTTLS delivery into a trusted local fixture, fail-closed
invalid SMTP, database/uploads persistence across redeploy and code rollback.

`wordpress/tests/production-workflow-boundary-contract.sh` extracts and executes
the real staging, production and rollback workflow blocks. Its pinned,
network-disabled Linux fixture runs the SSH-side blocks as a disposable UID
2000 operator, crosses a fixture-only authorized elevation boundary for the
named root reads, and proves direct reads remain denied. It also covers the
tag-at-digest handoff, malformed/mutable/wrong-SHA negatives, both production
backup checks, rollback backup/extraction, ownership/mode/symlink failures and
checksum corruption. This is local workflow evidence, not host provisioning or
a production deployment.
