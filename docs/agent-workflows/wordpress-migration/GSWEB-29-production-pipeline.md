# GSWEB-29 — automatic production releases without staging

## Owner-approved solo review policy — 2026-09-08

The owner explicitly approved replacing the second-human requirement with an
independent AI code review, all green checks and the owner's merge decision.
First cutover remains separately authorized. No GitHub settings, merge or
production operation is authorized merely by accepting this code/doc change.
The earlier request to nominate another human is superseded.

For this repository, effective PR protection may explicitly require zero
approving human reviews, while retaining nonempty required checks and enforcing
classic protections for administrators. A missing PR policy is still refused.
If any effective rule requires one or more human approvals, its stricter
requirement remains enforced; solo mode never silently bypasses it.

With zero required approvals the source validator requires a same-repository
PR merged into main at the exact CI SHA by `grzegorzrzeznikiewicz`, GitHub User
ID50638878, with verified repository admin identity. A direct main push,
unmerged PR, foreign fork or merge by another account does not qualify.
Record the separate AI review as a **COMMENTED pull-request review**, not an
APPROVED self-review, ordinary issue comment or approval by an invented account.
Submit it under the owner account before merge, explicitly bound to the current
PR head via both GitHub `commit_id` and this body format:

```text
GAMA-SOLO-AI-REVIEW-V1
{"head_sha":"<actual full PR head SHA>","result":"approved","report":"<actual independent AI reviewer, scope, findings, disposition and limitations>"}
```

Never copy this placeholder as real evidence. The latest owner-recorded report
must have exactly these three JSON fields, nonempty actual review text and an
approved outcome; use `changes-requested` to record a blocking outcome. New
code requires a fresh review for its SHA. A later owner CHANGES_REQUESTED review
withdraws the prior report; routine comments do not. Submission timestamps, not
review creation IDs, determine the latest decision. Ambiguous latest timestamps
and pending owner AI reports refuse promotion. Missing, stale, pending,
dismissed, malformed or post-merge reports refuse promotion. The source receipt
binds review ID and SHA-256 of its exact body; publisher/host revalidation detects
changes between validation stages. No additional write-token scope is granted
to release jobs to create their own approval.

This report is an **owner-account attestation of an AI review**, not independent
human approval or cryptographic proof of a particular agent's identity. GitHub
account-level provenance cannot distinguish the owner clicking merge from an
authorized tool using that account. Agents must still obtain the owner's actual
merge decision. An editable report is not immutable historical evidence; archive
the review with release evidence. These limits are accepted in the solo model.
The change remains local until separately published and freshly tested in CI;
the green `52b5b48` run below predates it.

Local verification: 43 source/publisher tests and the full pinned isolated
Linux181-test release suite passed with warnings as errors. Independent AI
review found one review-ordering issue, reproduced with failing tests and fixed
using submission time; the scoped re-review approved with no remaining
Critical/Important/Minor findings. This is technical local approval only.

API contracts: [review fields](https://docs.github.com/en/rest/pulls/reviews),
[PR details](https://docs.github.com/en/rest/pulls/pulls),
[zero-review branch protection](https://docs.github.com/en/rest/branches/branch-protection).

## Latest publication and CI — 2026-09-08

The owner explicitly authorized commit/push for PR #8 CI only. Implementation
and two independently reviewed CI-fixture fixes are published at
`52b5b48bb6827c8730a88cc0960554055ec768de`. Fresh WordPress and legacy CI passed
all eight jobs; downloaded release transport and browser/persistence evidence
were verified. See [exact CI evidence and remaining gates](GSWEB-29-ci-2026-09-08.md).
This supersedes the earlier same-day uncommitted/no-new-CI wording below.
Gate C remains NO-GO: no merge, registry publication, production configuration
or deployment occurred. An independent GitHub reviewer still needs to be
designated (or the owner must explicitly revise the accepted review policy).

## Accepted scope and actual status — 2026-09-08

The owner approved **local + production only**, with no remote staging and
no additional candidate installation on the production server. The detailed
[no-staging design](../../superpowers/specs/2026-09-07-wordpress-no-staging-release-design.md)
was accepted on 2026-09-07. Standard releases are intended to run automatically
after an approved PR is merged to main and all required checks pass. The first
React/Symfony-to-WordPress cutover remains a separate, freshly approved operation.

Implementation follows the [seven-task plan](../../superpowers/plans/2026-09-07-wordpress-no-staging-release.md)
on `feature/GSWEB-9`. Tasks 1–6 passed independent task reviews, including
fixes to manual routing recovery, operational-child cleanup, durable legacy
replay protection and the shared trusted-main guard. Whole-change review found
eleven issues; their combined fix wave passed fresh local tests. Scoped
independent review confirmed all eleven addressed, with no new Critical or
Important breakage identified in the fix diff. Controller Linux tests passed
170/170, and both actual
same-image consumers passed all five deliberate data-loss negatives each.
This is not new remote CI,
a registry publication, host provisioning or production deployment.

Changes remain uncommitted above `87cab81a06057142463c82201e8cbabe7d2593a1`.
**Gate C is NO-GO.** This guide describes the accepted contract and current
implementation status, not permission to execute a release.

The former manual staging-based pipeline, published in PR #8 on 2026-09-06,
is [historical evidence at 19a348d](https://github.com/grzegorzrzeznikiewicz/company-site/blob/19a348dea7451b1b9780e336724731a9155321fe/docs/agent-workflows/wordpress-migration/GSWEB-29-production-pipeline.md).
Do not execute its candidate-on-production, public-staging or backup-before-
emergency-rollback procedure as the current operating model.

## Exact release, separate privileges

1. Unprivileged WordPress CI preserves all four named quality gates and the
   exact ZIP lifecycles. It builds one `linux/amd64` candidate. The actual
   regression/acceptance-with-rollback and encrypted-SMTP production-model
   consumers both test that same image without rebuilding or modifying layers.
2. The producer seals their successful image/run/attempt-bound receipts,
   independently reads the package inventory, saves that image and emits
   `release.json` plus `image.tar`. The artifact name is
   `wordpress-release-<full-git-sha>-<run-id>-<run-attempt>`.
3. Read-only source validation requires the actual same-repository main-push
   run, exact current attempt, successful WordPress gates, approved merged PR
   and effective required checks. Until legacy retirement, all four existing
   legacy CI gates must also pass for the exact main SHA.
4. The publisher downloads that exact immutable artifact into its own protected
   runner-local directory, verifies its artifact/manifest/TAR hashes and
   rechecks the source. Its only write authority is the registry; it receives
   no SSH or SMTP secrets and never builds. After publishing, it pulls by digest
   and compares the config ID, platform, revision, release marker and layers.
5. A separate host-deployment boundary passes a closed JSON request containing
   that publication. The trusted, preinstalled host coordinator rechecks the
   source, mode, authorization and actual installation under its lock before
   any mutation.

The only accepted deployment reference is
`ghcr.io/grzegorzrzeznikiewicz/gama-wordpress@sha256:<64 lowercase hex>`.
Tags, development images, another repository or a green unrelated run are not
release authority. A transport receipt contains a runner-local path and must
not be reused across runners.

Source validation's exit 3 denotes a retryable pending check; only that case
may be retried within a hard deadline. Invalid or incomplete provenance is a
hard refusal. A successful Check Run cannot mask a failing or pending commit
status of the same required name.

## Three modes, one transaction boundary

`GAMA_DEPLOYMENT_MODE` and the protected host mode are exactly `off`,
`legacy` or `wordpress`. Missing/invalid values refuse mutation. The workflow
must check the mode before privilege and the host must recheck under lock.
The repository variable is not a substitute for host state.

All WordPress and legacy deployment/recovery entry points share the
`wordpress-production` workflow concurrency group with cancellation disabled,
plus the actual host lock at `/srv/gama-wordpress-production/control/lock`.
The lock covers mutation **and verification**, not just an earlier SSH preflight.

The protected control directory contains `mode`, `accepted.json`,
`operation.json`, `incident.json` and the separate `legacy-completed.json`
history of successful legacy operation identities. Tools, configuration and physical
ancestors are root-owned, not symlinks or writable by other accounts.
JSON data is strictly parsed, never sourced as shell. State writes use a private
new file, fsync, atomic rename and directory fsync.

Legacy completion history is durable before the current journal becomes
completed. Replaying an older recorded operation must not deploy it again
or replace a newer journal; conflicting reuse of an ID refuses. The legacy
history does not overwrite WordPress acceptance. Corrupt or oversized history
fails closed under the protected JSON size limit; there is no automatic
eviction, history-deletion or incident-clearing shortcut.

Under the lock, a standard release requires WordPress mode, a healthy accepted
image, unchanged persistent resource identity and the current main SHA.
A stale queued version is skipped; a completed identical operation is
idempotent. Conflicting identities, partial first installation or unresolved
state refuse further mutation. Intent is durable before backup or deployment.

Ordinary deployment replaces only code. It never bootstraps CMS/content,
imports a local database or resets editor changes. Database and uploads remain
the current persistent resources.

## First cutover and real owner approval

First cutover starts only from `off`, with no accepted or partially installed
WordPress production resources. Observation covers all project containers,
including one-offs and other services, project networks/volumes and exact
reserved resource names. Network-only remnants and missing/foreign resource
labels cannot be interpreted as a genuinely absent installation. Observation
of incomplete WordPress remains possible for routing recovery without healthy
PHP. The cutover verifies the legacy backup and routing
recovery evidence before installing the single stable WordPress namespace.
It checks local runtime and SMTP transport, verifies a WordPress backup,
switches routing and verifies public HTTPS/content. It does not automatically
change the deployment mode to `wordpress`.

The existing `wordpress-production-cutover` environment supplies the owner
gate. Authorization binds the exact source/artifact, first-attempt manual
promotion run, named human operators and an active UTC window. The canonical
approval comment is prepared before the gate; formatting it is **not approval**.
The validator checks the configured required User reviewer and actual approved
history, honoring the configured self-review policy. A retried manual run
requires a new dispatch and fresh approval, not reused ambiguous history.

The owner-approval boundary must not grant the registry publisher deployment
or SMTP credentials. A valid publisher-time approval does not authorize a host
transaction after its window expires.

After operational enabling is separately approved, the first-cutover dispatch
accepts one JSON `authorization` input with exactly `authorization_id`,
`git_sha`, `source_run_id`, `source_run_attempt`, `artifact_id`,
`artifact_digest`, `operators`, `window_start`, `window_end`. Use real
validated source/artifact metadata and agreed operators/window, not example
IDs. The workflow supplies its own current dispatch ID/attempt; it does not
let the caller impersonate another run. Review the generated canonical
comment before the configured owner gate. Standard releases do not use this
manual input or gate.

## Recovery and incident handling

Standard-release failure restores the previous accepted immutable image with
**current database and uploads**. Neither a healthy failing PHP process nor a
fresh backup is a prerequisite for code recovery. Failed first cutover restores
the saved legacy route and keeps WordPress data.

Manual recovery uses the existing
`wordpress-production-rollback.yml` workflow and
`wordpress-production-rollback` environment. Its separate authorization binds
the recovery operation, original target operation, kind, previous SHA/digest,
operators and window to actual first-attempt approval history and the protected
host journal. Forward current-main freshness must not prevent an explicitly
authorized return to the previous version.

The recovery dispatch accepts one closed JSON `request`, including the
retained target publication and `recovery_authorization`. The latter names
both the new recovery operation and the distinct original target operation.
Its canonical comment is also prepared before approval. Retain source,
publication and protected host-journal evidence: a mutable image tag or
operator-written success comment is not a replacement for those records.

Recovery journals retain the immutable original deployment in `recovery_target`
and the previous incident evidence. After an ordinary failed recovery, a new
dispatch and fresh approval can still bind to that original target, exact
image/SHA and protected resource identity. The caller cannot replace it with
an invented target or reuse the failed recovery's identity to bypass approval.

Successful recovery does not turn the original failed release into success or
automatically clear its incident barrier. Missing SSH output does not prove
that no mutation occurred. An interrupted journal remains blocking; operators
must inspect protected evidence, potentially surviving child processes and
unresolved daemon-side work
before an explicitly audited resolution. There is no convenience CLI or
workflow step for deleting the barrier.

Operational helpers run in an owned synchronous process group. Abnormal
completion must terminate its live members, but client cleanup alone does not
prove Docker-daemon completion. Host deployment invokes `deploy-production
--mutation-only`: synchronous daemon writes must return success before the
separate read-only readiness checks. Direct helper/rehearsal calls retain their
own health checks. No text marker in Docker/WP output is a completion witness.

Abnormal or timed-out daemon-mutating helper, image-pull or routing operations
remain interrupted even after local process cleanup. Unverifiable Linux
procfs/waitid cleanup also blocks both automatic and manual recovery. Record
the original failure and preserve the incident; do not start another installer
while prior daemon work is unresolved. A health/public/PHP check failure after
known-complete writes still permits the controlled automatic recovery described
above. Operator adapters must not deliberately detach untracked work.

Code rollback, routing recovery and data restore are different operations.
Data restore is the separately approved GSWEB-24 process into a new namespace,
never an automatic import of an older database over newer content.

## Host and infrastructure prerequisites

Trusted release code/configuration must be installed separately with explicit
authority. A release workflow must not copy or replace privileged host tools
before locking or while another operation is using them.

The fixed installed tree is `/srv/gama-wordpress-production/tools/wordpress`.
Forward and recovery workflows invoke `/usr/bin/python3` with its
`bin/production-release --config /srv/gama-wordpress-production/control/host-config.json`.
The host config's `wordpress_root` must match that installed tree. Legacy uses
the same Python executable with `bin/production-legacy-release` and no
request-selected command or path. Install the complete reviewed import tree
and helpers together through the separately approved provisioning procedure.

Legacy additionally requires the root-private, root-owned
`/srv/gama-wordpress-production/control/legacy-config.json`. Its only keys are
`docker` (the protected Docker executable) and `environment`; the latter has
exactly `MAILER_DSN`, `CONTACT_RECIPIENT`, `CONTACT_SENDER`,
`COMPANY_API_APP_SECRET`, `COMPANY_DB_PASSWORD`, `ADMIN_PASSWORD_HASH`.
Values are preinstalled secrets, never dispatch inputs or journal fields.
The fixed external VM2 env file and root Docker registry credentials must
also be protected. No release step installs or transfers these credentials.

The host requires the approved amd64 architecture, protected production
environment and read-only GitHub credential, exact Docker/runtime tools,
public TLS/routing, a controlled SMTP recipient and verified backup storage.
The source validator needs read access to actual repository protection and
approval metadata; Administration read is not a valid `GITHUB_TOKEN` YAML
permission. No token, permission or environment was configured by this work.

The workflow credential is named `WORDPRESS_PROVENANCE_READ_TOKEN`; it needs
the exact endpoint-specific read scopes required by the validator, not new
write scopes. Host SSH secrets belong only to `wordpress-production` and
`wordpress-production-rollback`. The cutover environment supplies the one
owner-approval gate, not publisher deployment credentials. To retain automatic
standard releases, `wordpress-production` must not introduce another manual
per-release approval gate; verify its actual protection rules before enabling.

The host directly checks GitHub provenance, Docker image/resources, actual
backup files and SHA-256 inventory, mount source/target, HTTPS/home/blog/login/
logo/menu/contact/indexability and controlled SMTP transport. Contact is the
homepage section `/#contact`, not an invented `/kontakt/` page. SMTP transport
acceptance still requires separate confirmation in the owner's agreed inbox.

Only provider-specific off-host encryption, retention, restore and legacy
backup/routing facts use explicitly configured root-owned evidence adapters.
Their bounded, closed replies must be fresh and operation/version/resource/
checksum-bound. A mounted path or an unbound success flag is insufficient.
Missing real adapters refuse the release. None has been installed or proven
against actual production infrastructure here.

Before enabling, record the exact host inputs, reviewers/operators, branch
protection and check policy, mode, retention/restore/alarms, approved code
installation, TLS/routing/SMTP proof and fresh clean amd64 CI. The read-only
repository preflight found no deployment-mode variable, no required PR reviews
and empty required-check lists; this does not satisfy the accepted policy.
Changing those settings requires separate authority.

## GSWEB-30 boundary

Legacy deployment and rollback are permitted only in legacy mode under the
same host lock and durable intent rules. Legacy retirement is not a side effect
of a successful WordPress deployment. Keep the old stack and recovery route
through the agreed stabilization period. Gate D and fresh approval for the
exact removal inventory are required before any deletion.

The external legacy Compose file remains `/srv/magento-devops/vm2/docker-compose.yml`.
Legacy verification checks the exact requested runtime/config image identity
and running state, plus `healthy` whenever Docker has a configured healthcheck.
The existing legacy Dockerfiles do not define a healthcheck; a running process
alone does not prove that frontend, contact or API requests work. Actual legacy
application smoke/health acceptance remains required before enabling these
entry points. WordPress's mandatory health checks are unchanged.

Local native development rehearsals, source tests and historical CI are
recorded in [GSWEB-25](GSWEB-25-ci-gates.md) and
[Gate C](GSWEB-28-gate-c.md). They do not establish production readiness.
