# GSWEB-26 — immutable deployment and rollback

## Current scope — 2026-09-08

The owner approved local + production, with **no remote staging environment**,
and approved the detailed no-staging specification on 2026-09-07.
[The implementation plan](../../superpowers/plans/2026-09-07-wordpress-no-staging-release.md)
is in progress on `feature/GSWEB-9`, with changes left uncommitted. The earlier
staging-to-production workflow is historical; it is not an operational
prerequisite of the accepted design.

The manifest, transport, single-candidate producer, provenance/publisher
boundaries, host transaction and workflow integration have passed their task
reviews. Whole-change review found eleven issues; scoped independent review
confirmed all eleven addressed, with no new Critical or Important breakage
identified in the fix diff. Local tests passed. There has been no registry publication,
fresh remote CI for these changes, or production operation. Gate C remains
NO-GO; this document is not permission to deploy.

## One tested release

The release image is built by `wordpress/runtime/Dockerfile` and contains the
pinned WordPress/PHP runtime, WP-CLI, theme and first-party plugins. A trusted
candidate has the full source SHA, a `release` marker and `linux/amd64` platform.
CI must build it once, and both real rehearsal consumers must test that exact
image ID. Each writes its success receipt only after its assertions pass.

`wordpress/release/candidate.py seal` verifies those two receipts against the
candidate, reads the exact package inventory from the image, saves that image
without rebuilding, hashes the TAR and emits the closed version-1 manifest.
The transport artifact is named
`wordpress-release-<full-git-sha>-<run-id>-<run-attempt>` and contains exactly
`release.json` and `image.tar`.

The read-only source validator binds the fetched repository, main-push run,
workflow, exact attempt, four WordPress jobs, approved merged PR and effective
required checks. Until legacy retirement, its four existing CI jobs must also
pass for the exact main SHA. A Check Run cannot hide a failing or pending
required commit status of the same name.

The transport validates the immutable GitHub artifact ID/digest, closed
manifest, protected extraction destination and TAR hash. It never extracts
Docker layers or executes artifact files as tools. A separate publisher
revalidates the source, loads the verified TAR, and publishes only to
`ghcr.io/grzegorzrzeznikiewicz/gama-wordpress`. It pulls the resulting digest
and checks config ID, platform, source label, release marker and ordered image
layers against the candidate. It never builds and receives no SSH/SMTP secrets.

The deploy reference is exactly
`ghcr.io/grzegorzrzeznikiewicz/gama-wordpress@sha256:<digest>`.
A mutable tag, another repository, development image or unrelated green run
does not authorize a release. A transport receipt includes a runner-local
path: a separate publisher runner must revalidate/download the same immutable
artifact into its own protected temporary directory.

## Persistent data and recovery contract

`wordpress/deploy/compose.yaml` separates database, uploads and installed core
volumes. Code installation replaces core files from the selected image while
WordPress is stopped; it must preserve the current database and uploads.
Only the explicitly authorized initial install may bootstrap CMS/content.
An ordinary update must not reset the editor's content or import a local DB.

The independently reviewed host-side transaction implements this contract:

- A shared lock covers first cutover, standard release and recovery. After
  acquiring it, recheck mode, accepted installation, pending journal, current
  main SHA and actual installation state.
- Before mutation, durably record the previous digest, observed persistent
  resources and verified off-host backup evidence. Refuse missing, stale,
  altered or incorrectly bound evidence.
- First cutover begins only from `off`, with a fresh version/operator/window
  authorization and verified legacy recovery evidence. It uses only the
  stable WordPress namespace, verifies it before routing and does not silently
  enable subsequent automatic releases.
- An empty installation means no project containers (including one-offs),
  networks or volumes and no conflicting reserved resource names. A network-only
  remnant or an unlabelled reserved volume is not permission to bootstrap.
- Standard failure restores the prior accepted image with **current** DB and
  uploads. Recovery must not require healthy failing PHP or a new backup.
  First-cutover failure restores the saved legacy route without deleting WP.
- Preserve the original failed outcome and a blocking incident record even
  when recovery succeeds. Interrupted operations require inspection of the
  durable host journal; a missing SSH response is not evidence of no mutation.
- Process-group cleanup alone cannot establish Docker-daemon completion.
  Host deployment uses the explicit `--mutation-only` helper path, then separate
  read-only readiness checks. Abnormal daemon-mutating helper, image-pull or
  routing completion leaves blocking interrupted/incident state even when its
  local clients have stopped. A verification failure after conclusively completed
  writes remains eligible for automatic recovery. Linux procfs and waitid support
  are explicit host prerequisites; no stdout marker proves completion.
- A failed manual recovery retains its immutable original target and previous
  incident evidence. A newly authorized operation may retry that exact target
  and resource identity after an ordinary failure. Interrupted/uncertain work
  still blocks recovery; no journal deletion or invented replacement target.

Data restore remains the separately approved GSWEB-24 operation in a new
namespace. Legacy removal remains GSWEB-30 after stabilization and fresh
approval of the exact inventory. See [production pipeline](GSWEB-29-production-pipeline.md)
for the host/workflow integration status and operational prerequisites.

## Rehearsal evidence, not a staging service

The historical name `wordpress/tests/staging-rollback-runtime.sh` now denotes
one disposable release-regression fixture, not a remote server or promotion
dependency. Together with `wordpress/tests/production-deployment-runtime.sh`,
it consumes one supplied candidate and checks actual row ID/title/content and
media hashes across deploy and code rollback. Both fresh final-fix runs also
refused deliberate title/content corruption, post deletion, media corruption
and media deletion, restoring exact owned fixtures before successful receipts.
No production resource is used.

Local native ARM development evidence is explicitly non-promotable. Two
amd64 rollback-base starts failed under QEMU on this ARM Mac; a successful
native fixture does not replace the still-required clean amd64 CI run.
The fixed `gama-wordpress` preview and its data must remain untouched by these
checks. Use only the reviewed uniquely owned fixtures; do not run fixed
namespace reset/restore gates on the owner's Docker daemon.

The former staging workflow and commands are preserved in
[the historical 19a348d document](https://github.com/grzegorzrzeznikiewicz/company-site/blob/19a348dea7451b1b9780e336724731a9155321fe/docs/agent-workflows/wordpress-migration/GSWEB-26-deployment-rollback.md).
They are not instructions for enabling the new process.
