# GSWEB-25 — CI and quality gates

`.github/workflows/wordpress-ci.yml` adds three required checks without changing
or deleting the React/Symfony workflows:

- **WordPress Source and Build** validates extension policy, static contracts,
  PHPCS, packaging reproducibility, secret scanning and controlled failure
  fixtures;
- **WordPress Package Lifecycle** downloads the exact SHA-named artifact from
  the build job and runs clean ZIP install/activate/deactivate/delete checks plus
  the browser suite;
- **WordPress Runtime and Restore** starts a clean local model, exercises mail,
  contact, security and SEO, then proves a full database/uploads restore.

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

Repository branch protection should require all three WordPress job names above
in addition to the current legacy checks during the stabilization period.
