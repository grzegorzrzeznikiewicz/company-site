# GSWEB-25 — CI and quality gates

`.github/workflows/wordpress-ci.yml` adds four named checks without changing
or deleting the React/Symfony workflows:

- **WordPress Source and Build** validates extension policy and static
  contracts, lints every first-party runtime JS/CSS asset, checks all
  first-party production PHP with WPCS/PHPCS and PHPStan, audits every QA
  dependency lock, builds reproducible packages, scans secrets and runs the
  controlled failure fixtures;
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
by CI. The failure contract proves that malformed PHP, syntax-invalid
JavaScript, invalid CSS, a real PHPStan type error, a failing test process, an
invalid package build input and a high-confidence token fixture each stop their
gate. Fixtures live only in temporary storage; the token is assembled rather
than committed or printed.

## 2026-09-06 acceptance and collection guard correction

The published green jobs for commit `1398f41` remain historical evidence, but
they did not execute two already-required guards. The release acceptance
contract also compared the case of its technical-verdict marker even though the
approved Gate C document deliberately says `Historical technical verdict` and
still contains both `VERDICT: NO-GO` and `remote CI`. The correction makes only
that marker comparison case-insensitive. The NO-GO and remote-CI requirements
remain exact, blocking assertions.

The Source and Build contract block now runs both the real acceptance contract
and its isolated five-case regression fixture. The release regression runtime
now runs the existing matrix collection contract inside the browser image, with
networking disabled, immediately after building that pinned image and before
the HTTPS/browser run. The collection contract executes Playwright discovery;
it requires Chromium and WebKit across desktop, tablet and phone (six release
cases) and the unchanged 39 non-release cases.

Exact focused local proof from the corrected revision:

```bash
wordpress/tests/release-acceptance-contract-regression.sh
wordpress/tests/release-acceptance-contract.sh
wordpress/tests/wordpress-ci-contract.sh
docker run --rm --network none --entrypoint node gama-wordpress-browser:gsweb27 \
  ./specs/support/release-matrix-contract.cjs
```

The acceptance fixture is behavioral: it invokes the real contract and accepts
both lowercase and capitalized historical markers while rejecting a missing
technical-verdict marker, missing `VERDICT: NO-GO` or missing `remote CI`. The
CI wiring mutations are static and reject either omitted call. A runtime
mutation of the collected Playwright JSON was also checked in the pinned image;
removing one browser/viewport case was rejected by the real validator.

Fresh remote CI still has to execute the corrected revision. The historical
runs do not prove this new wiring, the public staging/user-preview gate remains
open, required checks on `main` still need owner reconciliation, and Gate C
remains NO-GO until its existing remote, public and owner acceptance conditions
are satisfied.

## Source coverage and policy

The asset gate uses Node 24.14.0 by digest and an npm lock containing ESLint
10.10.0 plus Stylelint 17.15.0. It checks the only three first-party runtime
assets: the theme `style.css`, and the contact plugin's `contact-form.js` and
`contact-form.css`. ESLint recommended browser rules and zero allowed warnings
are blocking. Stylelint extends the maintained standard configuration with four
specific compatibility exceptions:

- `custom-property-pattern` permits WordPress's generated
  `--wp--preset--...` hierarchy;
- `selector-class-pattern` permits first-party BEM and WordPress block class
  underscores;
- `no-descending-specificity` permits component-grouped theme rules;
- `media-feature-range-notation` preserves the broadly supported min/max media
  query syntax used by the theme.

The PHP gate covers all 25 production PHP files in the theme and every
first-party plugin: contact, SEO, security, mail transport and local Mailpit.
Theme PHP retains the full `WordPress` ruleset, text-domain check and global
prefix check. Plugins use `WordPress-Core`; errors block while warnings remain
advisory. Four named compatibility exceptions are scoped in
`phpcs-plugins.xml.dist`: PSR-4 class filenames, upstream PHPMailer camel-case
properties, intentional empty-string environment fallbacks and the existing
non-Yoda strict comparisons. There is no blanket path exclusion.

PHPStan 2.2.13 runs at level 5 with phpstan-wordpress 2.0.4 and WordPress 7.1.0
stubs. It is limited to one process and 1 GiB because loading the complete
WordPress stubs exceeded 512 MiB locally. `treatPhpDocTypesAsCertain` is false.
There is no baseline, `ignoreErrors` list or excluded production path. A QA-only
bootstrap supplies the string type of the runtime-derived `GAMA_CONTACT_URL`;
it does not change plugin behavior.

## Vulnerability audit policy

`wordpress/tests/wordpress-dependency-audit.sh` audits all three WordPress QA
locks: `qa/composer.lock`, `qa/assets/package-lock.json` and
`qa/e2e/package-lock.json`. Composer audits the lock including development
tools, fails for an abandoned package and has no advisory or severity ignore.
Both npm audits use `--package-lock-only --audit-level=low`, include development
tools and therefore block every reported severity. Audit services remain
networked, no credentials are passed, and an unavailable service is a failure;
the npm failure path is exercised against an unreachable registry. Incidental
output from `composer install` or `npm ci` is not accepted as the audit gate.

## Reproducibility, action pins and cache controls

Composer, npm and container inputs remain locked, the PHP and browser QA images
are digest-pinned, and the asset image adds the approved Node 24.14.0 digest.
Every external action is pinned to a full commit SHA with a readable major
version comment. On 2026-09-06 the official GitHub API resolved the pins to:

- `actions/checkout` v7.0.1 — `3d3c42e5aac5ba805825da76410c181273ba90b1`;
- `actions/upload-artifact` v7.0.1 — `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a`;
- `actions/download-artifact` v8.0.1 — `3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c`;
- `actions/cache` v6.1.0 — `55cc8345863c7cc4c66a329aec7e433d2d1c52a9`.

The referenced `action.yml` files all declare `runs.using: node24`; no forced
Node 20 compatibility warning is expected.

Persistent caches contain only serialized WordPress QA tool images with
BuildKit inline cache metadata. Source QA
keys include runner OS, Composer/npm locks, QA Dockerfiles and lint/static
analysis configuration. Browser QA keys include runner OS, the E2E lock and
package metadata, browser Dockerfile, Playwright configuration and timeout
policy. Restored images expose dependency/build layers to the same `docker build`
and Compose commands through explicit `--cache-from` inputs; the inline metadata
is what makes those layers reusable on a fresh runner after `docker load`, while
Docker still validates every context layer. Cache misses build the pinned
browser QA image before the consumer command and are valid cold runs. Cache
contents never include secrets, databases, uploads,
release evidence, source-built ZIPs or other Docker projects. Package checksum,
manifest, install and allowlist validation always runs and never trusts a
cache.

## Safe local mapping

The source job maps to these non-destructive commands from the repository root:

```bash
wordpress/bin/ci-image-cache restore source
wordpress/bin/validate-extensions-lock
wordpress/tests/mount-contract.sh
wordpress/tests/contact-plugin-contract.sh
wordpress/tests/contact-form-browser-contract.sh
wordpress/tests/mail-transport-plugin-contract.sh
wordpress/tests/seo-plugin-contract.sh
wordpress/tests/security-plugin-contract.sh
wordpress/tests/backup-restore-contract.sh
wordpress/tests/production-deployment-contract.sh
wordpress/tests/theme-contract.sh
wordpress/tests/plugin-package-contract.sh
wordpress/tests/ci-package-input-contract.sh
wordpress/tests/release-acceptance-contract.sh
wordpress/tests/release-acceptance-contract-regression.sh
wordpress/tests/wordpress-ci-contract.sh
wordpress/tests/ci-failure-contract.sh
wordpress/tests/wordpress-assets-quality.sh
wordpress/tests/wordpress-php-quality.sh
wordpress/tests/dependency-audit-contract.sh
wordpress/tests/wordpress-dependency-audit.sh
wordpress/bin/ci-image-cache save source
```

The package lifecycle job consumes CI artifacts. Its safe local equivalent
first creates the exact allowlisted packages, then uses disposable Compose
namespaces. The explicit host-side artifact directory survives Compose cleanup;
copy it out before disposing of the machine if the evidence must be retained:

```bash
package_artifact_root="$(mktemp -d /tmp/wordpress-browser-artifacts.XXXXXX)"
wordpress/bin/ci-image-cache restore browser
SOURCE_DATE_EPOCH=1767225600 wordpress/bin/package plugin gama-contact
SOURCE_DATE_EPOCH=1767225600 wordpress/bin/package theme gama-software
wordpress/bin/test-package "$(wordpress/bin/require-ci-package plugin gama-contact wordpress/dist/gama-contact-0.3.2.zip)"
GAMA_THEME_ARTIFACT_ROOT="$package_artifact_root" wordpress/bin/test-package "$(wordpress/bin/require-ci-package theme gama-software wordpress/dist/gama-software-0.4.1.zip)"
wordpress/bin/ci-image-cache save browser
```

The runtime job's `--clean` and restore operations intentionally target the
fixed `gama-wordpress` namespace and curl services on `localhost:8090` and
`localhost:8027`. Run the entire checkout and command sequence **inside** a
separate disposable Linux VM or CI runner with its own loopback and Docker
daemon. Never run it from the user's host, in another host checkout, or merely
through a remote `DOCKER_CONTEXT`: that would split the Docker daemon and bind
mounts from the host-side `localhost` probes and could still reach the user's
preview. Inside the disposable guest, use an exit trap to mirror both workflow
`always()` steps: save the QA cache and then remove the fixed runtime resources
even when a preceding check fails.

```bash
set -euo pipefail

cleanup_runtime() {
  local command_status=$?
  local cache_status=0
  local reset_status=0

  wordpress/bin/ci-image-cache save browser || cache_status=$?
  wordpress/bin/reset --confirm || reset_status=$?

  if (( command_status != 0 )); then
    return "$command_status"
  fi
  if (( cache_status != 0 )); then
    return "$cache_status"
  fi
  return "$reset_status"
}
trap cleanup_runtime EXIT

wordpress/bin/ci-image-cache restore browser
wordpress/tests/runtime-smoke.sh --clean
wordpress/bin/start
wordpress/tests/backup-restore-runtime.sh
```

The release regression scripts generate exact disposable staging and guarded
production-model namespaces and preserve the explicit rollback fixture. Their
explicit host-side artifact directory survives namespace cleanup; retain or
upload it before disposing of the machine:

```bash
release_artifact_root="$(mktemp -d /tmp/wordpress-release-evidence.XXXXXX)"
export GAMA_RELEASE_ARTIFACT_ROOT="$release_artifact_root"
export GAMA_ROLLBACK_BASE_REF=043beee6490664758bdbbff55d7a9cdf9156a398
wordpress/bin/ci-image-cache restore browser
wordpress/tests/staging-rollback-runtime.sh
wordpress/tests/production-deployment-runtime.sh
wordpress/bin/ci-image-cache save browser
```

## Historical duration evidence

GitHub run `34021197096` tested PR merge
`84b0abb5bbe3f41f4b051f6b5c08dabc3591bd6b` for head
`968ed8cdf3241743f07b74cbdb840b3c492a2882` on independent cold Ubuntu runners,
before the new lint/static-analysis/audit gates and persistent caches:

- Source and Build: 31 seconds;
- Package Lifecycle: 5 minutes 59 seconds;
- Release Regression: 5 minutes 41 seconds;
- Runtime and Restore: 4 minutes 33 seconds, failing only at the now-corrected
  portable permission assertion after its 3 minute 27 second clean-runtime step
  had passed;
- overall elapsed time: approximately 6 minutes 34 seconds because downstream
  jobs ran in parallel.

Earlier successful run `34020621325` measured Source and Build at 30 seconds and
Release Regression at 5 minutes 32 seconds. These are historical measurements,
not claims about the expanded workflow. A first run of each new key is expected
to be cold. A later hit should avoid downloading/installing QA dependencies and
reuse Docker layers, but Docker context validation and every quality/package
check still run.

### Expanded workflow: first cold Linux run

[GitHub run `34024401212`](https://github.com/grzegorzrzeznikiewicz/company-site/actions/runs/34024401212)
tested PR head `2d26cbd79bbe806621644185257ddcc024795381` through merge revision
`4715aaa4b67e7304fd8ebc264d115ea319c1ebea` on 2026-09-06. Both new QA cache
keys were absent on the fresh runners:

| Job                 | Wall time            | Result                                                                                                               |
| ------------------- | -------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Source and Build    | 1 minute 2 seconds   | Passed, including all new lint, PHP static-analysis, audit and negative-fixture gates.                               |
| Package Lifecycle   | 6 minutes 26 seconds | Passed for the downloaded Contact 0.3.2 and theme 0.4.1 packages.                                                    |
| Runtime and Restore | 5 minutes 3 seconds  | Failed in the isolated full-restore check; the clean-runtime step passed.                                            |
| Release Regression  | 5 minutes 54 seconds | Passed: 2 browser regression and 13 acceptance tests, staging code rollback and isolated production-model rehearsal. |

These are job outcomes, not final data-persistence acceptance. A subsequent
isolated Linux reproduction found that `wp post list --search` passed an
unsupported search key to `WP_Query`, returned every page and made the restore
assertion select the wrong ID. Two staging rollback assertions use the same
argument and can accept an unrelated page. Both affected scripts require a
targeted correction and fresh exact-ID/content persistence verification.

The source QA cache was saved at 09:22:05 UTC and the browser QA cache at
09:28:01 UTC, both under `refs/pull/8/merge`. Cache keys were respectively
`Linux-wordpress-source-qa-v1-e291787a79e561784b97b2286888f772c1617f800eb0643264b3045ae99aff1d`
and
`Linux-wordpress-browser-qa-v1-9f22322a4e17a5ee953b75f6b4b6116eccd6cdf2d3b79e5c65b2ad9f83fa4938`.
This proves cold creation and persistence, not warm reuse. The next fresh-runner
execution must verify cache restoration and actual dependency-layer reuse.

All four legacy jobs passed in
[run `34024401192`](https://github.com/grzegorzrzeznikiewicz/company-site/actions/runs/34024401192)
for the same head. The WordPress workflow remains **failed overall** until the
full-restore failure is diagnosed, corrected and retested. These isolated CI
results neither accept the public staging host nor authorize Gate C or a
production deployment.

## Legacy preservation and required checks

The existing `.github/workflows/ci.yml`, `deploy.yml` and `rollback.yml` remain
the active legacy React/Symfony path until Gate D. `.gitlab-ci.yml` and the
scripts under `build/` are historical/unknown-use deployment assets and remain
unchanged until GSWEB-30 verifies their consumers and shared-host impact. The
WordPress workflow performs no deployment.

Branch protection should require all four WordPress job names above plus the
legacy checks **Backend Quality (Symfony)**, **Backend Tests**,
**Frontend Quality** and **End-to-End Tests** during stabilization. Named jobs
are not automatically required checks: the 2026-09-06 read-only GitHub audit
found no required status-check names configured on `main`; protection must be
reconciled before integration.

## Linux runner portability

Docker builds respect the caller's configuration rather than defaulting to a
macOS-only `/private/tmp` directory. Browser builds resolve the actual repository
root and do not depend on the checkout directory name. Legacy ESLint still
excludes the isolated `wordpress/` project; the separate WordPress gate owns its
runtime assets.

The PHP fixture loader uses a POSIX character class for the opening tag and HTTP
header assertions normalize CRLF. Backup permission inspection now tries GNU
`stat -c` first and falls back to BSD `stat -f`, avoiding GNU's partial output
on an unsupported `-f` invocation. Release regression fetches full history and
uses `043beee6490664758bdbbff55d7a9cdf9156a398`, retained by the QA-only tag
`qa/wordpress-rollback-baseline-2026-09-05`, instead of `HEAD^`. This fixture
does not select a production rollback image.
