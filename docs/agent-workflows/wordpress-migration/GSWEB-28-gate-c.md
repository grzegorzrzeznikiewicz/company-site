# Gate C — production readiness review

## Decision

- **VERDICT: NO-GO**
- Technical verdict for repository commit
  `e197dc731ceb0b9fd4a992db1e917abc0bdef4fc`: **APPROVE**
- Review date: 2026-09-04
- Reviewed environment: isolated local deployment-model rehearsals plus a
  read-only probe of `staging.gama-software.com`
- P0: none
- Open technical implementation P1: none

NO-GO is caused by missing remote CI/release evidence, an unusable public
staging endpoint and missing owner/infrastructure decisions. It is not approval
to run GSWEB-29 or change production traffic.

## Verified evidence

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
- Theme, deployment, backup/restore, acceptance, CI failure-injection and
  tracked-secret contracts pass. The E2E dependency audit reports zero known
  vulnerabilities.
- Two independent Gate C reviews found no P0. The second review closed all
  earlier technical P1 findings and approved the implementation.

## Gate C blockers

### P1 — remote CI and promotable artifact

The branch/commit is not present in the remote repository. There is no green
`WordPress Quality Gates` run, published SHA-named registry digest or proof that
the same digest was promoted to staging. Required sequence:

1. Push the reviewed branch and run the complete WordPress CI workflow.
2. Publish the immutable registry image and record its digest.
3. Deploy exactly that digest to the public staging namespace.
4. Execute and retain acceptance evidence against that deployment.

### P1 — public staging infrastructure

The current `staging.gama-software.com` probe is not an acceptable staging
environment: HTTPS presents a certificate for `blog.gama-software.com`, while
HTTP does not redirect to HTTPS. Infrastructure must configure the correct
certificate, routing and release namespace before the real acceptance run.

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

GSWEB-8 and GSWEB-22–28 statuses must be verified in the authenticated Gama
Software Jira session. The automated browser cannot do this while macOS is
locked.

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
