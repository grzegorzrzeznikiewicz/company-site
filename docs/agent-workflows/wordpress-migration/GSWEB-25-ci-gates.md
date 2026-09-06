# GSWEB-25 — CI and quality gates

`.github/workflows/wordpress-ci.yml` adds four named checks without changing
or deleting the React/Symfony workflows:

- **WordPress Source and Build** validates extension policy, static contracts,
  PHPCS, packaging reproducibility, secret scanning and controlled failure
  fixtures;
- **WordPress Package Lifecycle** downloads the exact SHA-named artifact from
  the build job and runs clean ZIP install/activate/deactivate/delete checks plus
  the browser suite;
- **WordPress Runtime and Restore** starts a clean local model, exercises mail,
  contact, security and SEO, then proves a full database/uploads restore;
- **WordPress Release Regression** rehearses immutable deployment, browser
  regression and acceptance, persistence, encrypted SMTP and code rollback in
  disposable staging/production-model namespaces.

The workflow has read-only repository permission, workflow-scoped concurrency,
explicit timeouts and SHA-qualified artifact names. Package outputs and browser
evidence are retained for 14 days. No production or staging secret is consumed
by CI. The failure contract proves that malformed PHP, a failing test process,
an invalid package build input and a high-confidence token fixture each stop
their gate; the fixture value is assembled only in temporary storage and is not
committed or printed.

The existing `.github/workflows/ci.yml`, `deploy.yml` and `rollback.yml` remain
the active legacy React/Symfony path until Gate D. `.gitlab-ci.yml` and the
scripts under `build/` are classified as historical/unknown-use deployment
assets and are retained unchanged until GSWEB-30 verifies their consumers and
shared-host impact. The new WordPress CI workflow performs no deployment.

Repository branch protection should require all four WordPress job names above
in addition to the current legacy checks during the stabilization period.

## Linux runner portability

The first remote runs on [PR #8](https://github.com/grzegorzrzeznikiewicz/company-site/pull/8)
exposed machine-specific assumptions that local macOS checks did not detect:

- Docker builds now respect the caller's configuration instead of defaulting
  to a macOS-only `/private/tmp` directory.
- The resolved browser build context must equal the actual repository root;
  the checkout directory no longer has to be named `web`. Both the local name
  and a `company-site` fixture pass; a different context ending in `/web` is
  rejected.
- Legacy ESLint excludes the isolated `wordpress/` project, just as it excludes
  `backend/`. Its React rules remain unchanged; WordPress has its own quality
  and browser gates.
- Release regression fetches full history and uses the explicit previous
  WordPress revision `043beee6490664758bdbbff55d7a9cdf9156a398` as its rehearsal
  baseline. A shallow checkout cannot resolve `HEAD^`, and the first parent of
  this migration's PR merge is the legacy-only `main`, not a WordPress release.
  This fixture baseline does not select a production rollback image.
  The QA-only annotated tag `qa/wordpress-rollback-baseline-2026-09-05` retains
  this already-public commit after a squash/rebase merge or source-branch
  deletion. Keep the tag while CI uses this SHA; it is not a production release.

Named jobs are not automatically required checks. The 2026-09-06 read-only
GitHub audit found no required status-check names configured on `main`; branch
protection must be reconciled before integration.
