# Gate C — production readiness review

## Decision

- **VERDICT: NO-GO**
- Historical technical verdict for repository commit
  `6f0d11f3020afd4ad332afb90487d016e6353de6`: **APPROVE, superseded by the
  Contact defect reported on 2026-09-05**. It is not approval of that UI or of
  the corrected release candidate.
- Review date: 2026-09-04; defect follow-up: 2026-09-05; remote CI/infrastructure
  follow-up: 2026-09-06
- Reviewed environment: isolated local deployment-model rehearsals plus a
  read-only probe of `staging.gama-software.com`
- P0: none
- Contact parity P1: locally corrected and independently approved in
  `04b3063`; fresh isolated candidate acceptance and rollback passed on
  2026-09-05. Public staging and owner acceptance are still outstanding.

NO-GO remains in force after the local Contact correction because remote
CI/release evidence, a usable public staging endpoint and owner/infrastructure
decisions are missing. It is not approval
to run GSWEB-29 or change production traffic.

## Fresh Contact-candidate rehearsal — 2026-09-05

- Source: clean `feature/GSWEB-9` at
  `04b306398cd2a071a38799e85def56745a358a05` (theme 0.4.1, contact 0.3.2).
- Command: `wordpress/tests/staging-rollback-runtime.sh`, with retained evidence
  root `/tmp/gama-contact-release.zBUpFs/`; exit status **0**.
- Isolated project: `gama-wp-staging-9342-69152`.
- Candidate image:
  `sha256:3f9abb36a79d3711631095623fbcdcbe6d63300ade9c0de5df6a8391eeee579c`.
  This is the rehearsal's local `test-candidate-sha-...` image, not a published
  registry release or remote-CI artifact.
- **2/2 regression checks passed** (desktop/mobile, navigation/logo, Axe WCAG
  2.1 AA and existing performance budgets).
- **13/13 acceptance checks passed**, including the added five-viewport Contact
  geometry/loaded-CSS check, form delivery/errors, content inventory, blog,
  Hero/CTA, services/modules and Editor/Administrator capability boundaries.
- The exact previous source commit was
  `043beee6490664758bdbbff55d7a9cdf9156a398`, image
  `sha256:b9fe0078c4db6723ddad2f005328613bbbd15ebd4d075396381cc0a8925f4507`.
  Deployment and code rollback preserved the database marker and upload SHA-256.
- `noindex` and local Mailpit delivery were verified. Cleanup removed only the
  disposable project's test resources; its container query was empty afterward.
  The separate `gama-wordpress` preview remained healthy at HTTP 200.
- Retained regression archive:
  `gama-wp-staging-9342-69152-browser-artifacts.tar`, SHA-256
  `7b752403748f9504105c54b838cc63989e633bb134e4706e573ce619002c43da`.
- Retained acceptance archive:
  `gama-wp-staging-9342-69152-acceptance-artifacts.tar`, SHA-256
  `232ed27318243b6fff97917e3188b6d7cd444735ab370ed4bacce896ec97e8b4`.
- Evidence review exposed a stale CI consumer: package lifecycle still named
  contact 0.3.1 and theme 0.4.0. Commit `b988700` now validates the requested
  package against source metadata and consumes contact 0.3.2/theme 0.4.1. Its
  behavioral RED/GREEN contract and relevant package/CI contracts pass; an
  independent task review returned APPROVE with no findings. This repairs the
  local workflow definition but is not a substitute for a remote green run.

This refresh closes the missing _local_ candidate-rehearsal evidence for the
Contact fix. It does not restore a blanket Gate C approval, substitute for the
owner's visual/accessibility acceptance, or authorize publication or cutover.

## Historical verified evidence

The following is historical evidence for the earlier revisions, not proof that
the Contact layout was acceptable. Previous visibility/reflow checks missed a
card that collapsed to 50px at a 320px viewport. The follow-up adds exact card
and field geometry plus explicit loaded-stylesheet assertions; see
[the Contact correction](GSWEB-19-contact-parity-fix.md).

- The clean repository builds local release image
  `sha256:1946785ed178afeb6aa6660311ec031641a665f3e8be738698822e556045c620`
  with revision `e197dc731ceb0b9fd4a992db1e917abc0bdef4fc`.
- The exact-commit rehearsal passed 2/2 desktop/mobile regression checks and
  12/12 acceptance checks. It covered Axe WCAG 2.1 AA, performance budgets,
  logo and navigation, the contact form, content, blog, Editor/Admin boundaries,
  and Editor saves of Hero/CTA, services, modules, Contact, menu, footer, posts
  and media.
- Staging used `noindex` and isolated Mailpit delivery. Database and uploads
  survived deployment and rollback.
- Rollback used source from the actual previous commit rather than a second
  label of the candidate. The final proof moved from candidate image
  `sha256:9b4e9b5414f01abbe99ac4f80d1e8b669b5925cb6e97647159d739c29972e20c`
  to previous-commit image
  `sha256:d482fc618b9459b781e2d1eb16f96a781baa8cdea92fa1cb997f5bd26787ba71`
  while retaining database content and media.
- Deployment-model backup/restore recreated the exact recorded image, database
  identity and upload SHA-256 in a fresh namespace in 14 seconds. Restore
  refuses a mismatching image ID or revision.
- The staging and backup/restore runtimes passed concurrently with dynamic
  loopback ports and separate test image/manifest names.
- The production-model runtime passed an isolated candidate deployment, first
  stable deployment, authenticated STARTTLS mail delivery, fail-closed invalid
  SMTP handling, database/upload persistence and an exact-image code rollback.
- Production promotion is manual, consumes the run-bound staging artifact and
  immutable digest without rebuilding, and gates the stable namespace behind
  the protected `wordpress-production-cutover` environment. A failed public
  smoke test has an independent fail-safe route back to the legacy target.
- Production rollback can route to the legacy target without depending on
  WordPress, its database or backup availability. Code-only rollback preserves
  database/uploads and requires the exact recorded previous immutable image.
- Deployment never copies its secrets file into a release directory. Production
  SMTP is environment-only, encrypted, rejects local/Mailpit hosts consistently
  in both deployment validation and the first-party mail transport, and fails
  closed instead of falling back to local PHP mail.
- Theme, deployment, backup/restore, acceptance, CI failure-injection and
  tracked-secret contracts pass. The E2E dependency audit reports zero known
  vulnerabilities.
- Three independent Gate C reviews found no P0. The final review closed all
  technical P1 findings and approved the implementation with high confidence.
  Its sole P2 observation (SMTP hostname-rule consistency) was fixed before
  commit and the mail/deployment contracts plus WPCS were repeated successfully.

## Gate C blockers

### P1 — remote CI and promotable artifact

The owner authorized publication on 2026-09-06. `feature/GSWEB-9` is now pushed
and [PR #8](https://github.com/grzegorzrzeznikiewicz/company-site/pull/8) is open
against `main`; neither a merge nor a production deployment has occurred.
The first remote runs exposed Linux portability defects, corrected with
independent review in `0ae31a7` and `06571b7`.
[WordPress CI run 34020621325](https://github.com/grzegorzrzeznikiewicz/company-site/actions/runs/34020621325)
passed Source and Build and Release Regression (2 regression checks, 13
acceptance checks, staging rollback and isolated production-model rehearsal).
Its package and runtime jobs exposed additional BSD/GNU text-processing
differences, reproduced and corrected in the follow-up. All four legacy jobs
passed in [run 34020621326](https://github.com/grzegorzrzeznikiewicz/company-site/actions/runs/34020621326).
Use the PR's latest check results as the authoritative full-run status; this
historical partial run is not a complete WordPress gate. No registry digest or
promotion of that digest to public staging has been recorded. Required sequence:

1. Complete the WordPress CI workflow for the published, reviewed revision.
2. Publish the immutable registry image and record its digest.
3. Deploy exactly that digest to the public staging namespace.
4. Execute and retain acceptance evidence against that deployment.

### P1 — public staging infrastructure

The `staging.gama-software.com` endpoint is not an acceptable staging environment.
The previous probe identified a certificate for `blog.gama-software.com`; the
fresh 2026-09-06 07:57 UTC probe still fails hostname verification (curl exit
60). HTTP returns 200 without redirecting to HTTPS. No certificate warning was
bypassed. Infrastructure must configure the correct certificate, routing and
release namespace before the real acceptance run.

The 2026-09-06 read-only GitHub audit also found:

- no repository environments, including the required `wordpress-staging` and
  protected production/cutover/rollback environments;
- no `STAGING_*` or `PRODUCTION_*` secrets. The existing `SERVER_*`, `SSH_*`
  and `PROD_*` names belong to the legacy pipeline and were not repurposed;
- no required status-check names on `main`, despite strict status-check mode;
- only legacy workflows and WordPress CI registered. The manual WordPress
  deployment workflows remain on the feature branch, not the default branch.

Staging needs the confirmed host/user/SSH port, GitHub environment secrets
`STAGING_SERVER_HOST`, `STAGING_SERVER_USER`, `STAGING_SSH_PRIVATE_KEY`,
`STAGING_SSH_PORT`, `STAGING_GHCR_USERNAME`, `STAGING_GHCR_TOKEN`, and the
host-owned `/srv/gama-wordpress-staging/.env`. Do not place their values in Git,
Jira or review comments. The owner has been asked to identify the target host.
Workflow registration must be coordinated with integration: legacy CI can
trigger the existing production deploy after a successful run on `main`, so a
merge is not an infrastructure-neutral way to enable the new workflows.

### P1 — production inputs and owners

Gate C still requires all of the following to be recorded:

- infrastructure operator and release operator;
- exact deployment window with timezone;
- production host, proxy/DNS owner and TLS paths;
- current React/Symfony routing target and previous WordPress digest;
- fresh verified off-host restore point and free-capacity confirmation;
- stabilization duration, metrics/thresholds and rollback authority.

### P2 — owner accessibility spot check

Automation covers WCAG rules, keyboard operation and responsive reflow. A human
native-browser 200% zoom and assistive-technology spot check remains required.

### Jira evidence

The authenticated Gama Software Chrome profile is accessible. On 2026-09-05,
GSWEB-10–30 were moved from backlog to board 1, joining GSWEB-9. The board's
Epic grouping now displays GSWEB-8 with all 22 children. GSWEB-8 was changed to
`W toku`; GSWEB-19 and GSWEB-28 to `Testowanie`, with evidence and remaining
acceptance conditions recorded in comments. No task was marked `Gotowe` merely
because it was moved onto the board. Reconciliation of the other tickets'
acceptance criteria/status remains outstanding and must not be inferred from
local tests.

## Known deviations requiring explicit acceptance

- Legal pages remain unpublished drafts until their wording is approved.
- Staging intentionally uses Mailpit, `noindex`, staging secrets and a staging
  hostname. A wrong TLS certificate is not an acceptable deviation.
- Automated accessibility checks do not replace the human spot check.

## Rollback plan

- Code rollback uses the recorded previous immutable WordPress digest and keeps
  database/uploads.
- Unsafe cutover rollback switches routing to the exact recorded React/Symfony
  target without deleting WordPress data.
- Data restore creates a fresh replacement namespace from the verified off-host
  backup; it never overwrites the live database in place.
- Grzegorz Rzeźnikiewicz and the named release operator authorize rollback; the
  named infrastructure operator executes routing changes.

## Owner decisions required before GSWEB-29

After remote CI and real staging are green, the owner must explicitly accept
the exact digest, staging result, editing guide, runbook, known deviations,
operators, window, stabilization plan and rollback authority. Starting GSWEB-29
and switching production traffic then requires a separate unambiguous command.
