# WordPress No-Staging Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the approved automatic standard WordPress release pipeline without staging, preserving exact tested artifacts, data and separately approved first cutover.

**Architecture:** The unprivileged CI builds one candidate and exercises both real release rehearsals. Read-only validation binds its artifact to an approved main push; a separate publisher promotes that image without rebuilding. One host coordinator serializes first cutover, standard deployment and recovery, records durable state and preserves DB/uploads.

**Tech Stack:** Existing pinned WordPress/MariaDB/Compose images, Bash, GitHub Actions, Python standard library (3.9+ for portable metadata/archive/control helpers). No new Python dependencies. Frontend/QA retain their pinned Node 24.14.0 environment.

**Spec:** [Accepted design](../specs/2026-09-07-wordpress-no-staging-release-design.md), accepted by the owner on 2026-09-07.

## Global Constraints

- Work only in `/Users/grzegorzrzeznikiewicz/Programowanie/PHP/Projekty/GamaSoftware/web`, on current `feature/GSWEB-9`; no additional Git worktrees.
- No commits, amendments, merge, push, image publication or production operations in this implementation session. Leave changes uncommitted and preserve earlier work.
- Existing baseline at execution start: `87cab81`; implementation reference is `19a348dea7451b1b9780e336724731a9155321fe`. Existing documentation commits are not new runtime evidence.
- "Nie tworzymy zdalnego stagingu ani dodatkowej instalacji kandydata na serwerze produkcyjnym."
- "Pierwsze przełączenie React/Symfony na WordPress pozostaje osobną operacją, wymagającą świeżej zgody na konkretną wersję, operatorów i okno."
- "Usunięcie starego stosu oraz odtworzenie produkcyjnych danych wymagają odrębnych decyzji."
- "Wersja początkowa pipeline'u przyjmuje jedną platformę `linux/amd64`." Confirm host architecture before enabling it; no silent emulation or alternate image selection on production.
- "Obie próby: regresja/akceptacja z rollbackiem i izolowany model produkcyjny z szyfrowanym SMTP, przyjmują ten sam jawny identyfikator obrazu. Nie budują własnego kandydata i nie modyfikują jego warstw."
- "Brak lub niepoprawna wartość oznacza odmowę mutacji." Deployment modes are exactly `off`, `legacy`, `wordpress`.
- "Automatyczny rollback nie wymaga zdrowia wadliwego nowego procesu PHP ani ponownego backupu jako warunku przywrócenia kodu."
- "Nierozliczony stan blokuje kolejne mutacje." Never infer success from a lost SSH response.
- Four existing named WordPress gates, exact ZIP lifecycle, role/SEO/contact/browser/restore evidence remain required. Tests must exercise behavior, not just grep YAML.
- Do not run `runtime-smoke.sh --clean`, `wordpress/bin/reset`, or fixed-production-namespace tests against the owner's daemon. Runtime work uses fresh, proven-owned namespaces or an isolated daemon, never the live preview.
- No test may create a Git commit to disguise uncommitted work. Local candidate evidence is explicitly development-only; trusted release production happens from a genuinely clean CI checkout. A new remote CI run is not claimed without authorized publication of source.
- Implementers do not spawn agents; controller dispatches the independent review. Reviews use scoped snapshots/diffs of uncommitted changes, not empty `HEAD..HEAD` ranges. Keep evidence because no commit history will replace it.

## File and interface map

| Unit | Files | Responsibility |
| --- | --- | --- |
| Manifest | `wordpress/release/manifest.py`, `wordpress/tests/release/test_manifest.py` | Closed data schema, strict types, source binding, artifact naming; no I/O or subprocesses |
| Transport | `wordpress/release/transport.py`, `wordpress/tests/release/test_transport.py` | Bounded safe ZIP container for `release.json` + `image.tar`, hash-before-load, exclusive destination |
| Candidate | `wordpress/release/candidate.py`, `wordpress/bin/build-release`, runtime rehearsal scripts | One image, independently derived inventory, receipts and archive, no modified candidate layers |
| Promotion | `wordpress/release/github_source.py`, `wordpress/release/promote.py`, corresponding tests | Read-only GitHub provenance/approval verification, separate Docker publisher and digest identity |
| Host transaction | `wordpress/release/host.py`, `wordpress/release/host_ops.py`, `wordpress/bin/production-release`, tests | Lock, protected journal, freshness, backup, deployment, verification, recovery |
| Entry points | production/rollback/CI/legacy workflows and boundary tests | Privilege separation, off-by-default mode guards, no staging dependency, wiring to real helpers |
| Evidence | existing release guides, Gate C, Confluence source and this plan's ledger | Accurate version-bound results, updated operational handoff without claiming a live deployment |

### Task 1: Closed manifest and exact source binding

#### Shared data contracts

`ReleaseValidationError(ValueError)` is the only public validation exception.
JSON input must reject duplicate keys and non-finite numbers. Unknown fields
are errors at every manifest-controlled level. Python booleans are not integers.
Source API responses may contain additional documented GitHub fields; select
and independently validate the exact required provenance before comparing.

Closed manifest version 1:

```json
{
  "schema_version": 1,
  "repository": "grzegorzrzeznikiewicz/company-site",
  "git_sha": "1234567890abcdef1234567890abcdef12345678",
  "workflow_id": 123,
  "workflow_path": ".github/workflows/wordpress-ci.yml",
  "run_id": 987654321,
  "run_attempt": 1,
  "event": "push",
  "ref": "refs/heads/main",
  "platform": "linux/amd64",
  "image_id": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "archive_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "packages": [
    {"name": "wordpress", "version": "7.1.0"},
    {"name": "theme/gama-software", "version": "0.4.1"},
    {"name": "plugin/gama-contact", "version": "0.3.2"},
    {"name": "plugin/gama-seo", "version": "0.1.0"},
    {"name": "plugin/gama-security", "version": "0.1.1"},
    {"name": "plugin/gama-local-mailpit", "version": "0.1.0"},
    {"name": "plugin/gama-mail-transport", "version": "0.1.0"}
  ],
  "evidence": [
    {"name": "release-regression", "status": "passed", "image_id": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "run_id": 987654321, "run_attempt": 1},
    {"name": "production-runtime", "status": "passed", "image_id": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "run_id": 987654321, "run_attempt": 1}
  ]
}
```

The package names and evidence names are the exact required sets, with no
duplicate or missing entry; versions are read from the candidate, never
inferred from the manifest under test. Version values can evolve without
changing the schema. Provenance `expected` is an independently supplied mapping
with exactly `repository`, `git_sha`, `workflow_id`, `workflow_path`, `run_id`,
`run_attempt`, `event`, `ref`, `platform`. General schema validation can represent
a `pull_request` run at `refs/pull/<positive-id>/merge`; promotion additionally
requires exactly `push` + `refs/heads/main` from a successful trusted source.

Artifact name is exactly
`wordpress-release-<git_sha>-<run_id>-<run_attempt>`.
Receipt names do not stand in for their real test results. Producer writes a
receipt only after the corresponding executable test succeeds; consumer checks
all four CI jobs before promotion.

---

#### Implementation steps

**Files:** Create `wordpress/release/manifest.py`; create `wordpress/tests/release/test_manifest.py`.

**Interfaces:**

- `parse_manifest(raw: str) -> dict`: reject duplicate keys/NaN; validate and return a detached normalized data value.
- `validate_manifest(manifest: dict, expected: dict | None = None) -> dict`: strict closed schema and optional complete exact provenance equality, raising `ReleaseValidationError`.
- `artifact_name(manifest: dict) -> str`: validate first, then return the exact naming contract.
- No file, Docker, network or subprocess access in this module.

- [x] **Step 1: Write a failing behavioral test.** Name the caught break: accepting a release whose CI attempt or evidence image differs from the trusted source.

```python
def test_rejects_evidence_from_another_attempt(self):
    release = literal_valid_manifest()
    release['evidence'][1]['run_attempt'] = 2
    with self.assertRaises(ReleaseValidationError):
        validate_manifest(release)
```

`literal_valid_manifest()` is a test-owned copy of the JSON above, not a call
to production code. Add literal expectations for the valid artifact name,
exact expected binding, unknown/missing fields, `True` used as an ID, zero and
negative IDs, upper/short SHA, unsafe repository/ref/workflow/path, wrong
platform, duplicate/missing packages/evidence, failed evidence, mixed image,
duplicate JSON keys (including nested) and non-finite JSON numbers. Reject
partial `expected` and expected values with invalid types; never ignore a
source key because it was omitted by the caller.

- [x] **Step 2: Run RED.** `python3 -m unittest discover -s wordpress/tests/release -p 'test_manifest.py' -v`. If the module is absent, have the test assert the expected production boundary is available, yielding an explicit failed assertion before implementation; do not present a syntax error as RED.
- [x] **Step 3: Implement strict reusable primitives and the manifest functions.**

```python
def positive_id(value):
    return type(value) is int and value > 0

def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ReleaseValidationError('duplicate JSON key')
        result[key] = value
    return result
```

Use anchored full matches, exact dictionaries/sets, no string coercion, and
deep-copy or reconstruct the validated result to prevent returned input aliases.
`artifact_name` uses validated integers and the full lower-case SHA.
- [x] **Step 4: Run GREEN and negative cases.** Repeat the focused command, then the complete current `wordpress/tests/release` discovery. `git diff --check`. Self-review and report RED/GREEN outputs. Leave changes uncommitted.
- [x] **Step 5: Independent scoped spec and quality review; fix and re-review before Task 2.**

### Task 2: Safe artifact transport and verified image archive

**Files:** Create `wordpress/release/transport.py`, `wordpress/tests/release/test_transport.py`.

**Interfaces:** consumes `parse_manifest`, `validate_manifest`, `ReleaseValidationError`.
Produces `unpack_release(zip_path, new_destination, expected) -> dict` and
`verify_archive(directory, expected) -> dict`, returning the validated manifest.
Destination is a new absolute directory; never overwrite an existing path.
The exact transport members are `release.json` (at most 64 KiB) and
`image.tar` (at most 4 GiB). At most two regular ZIP members, at most 4 GiB
+ 64 KiB expanded size. Hash stream the TAR before Docker is invoked; never
extract Docker layers. The downstream engine receives a verified TAR, not
files executable as validation tools.

- [x] **Step 1: RED with real `zipfile` fixtures in `TemporaryDirectory`.** Catch path traversal or metadata that allows an extra file to be written outside the destination. Exercise the actual unpacker and assert no outside file/destination is left on rejection.

```python
for unsafe in ('../outside', '/absolute', 'a/../image.tar', 'a\\image.tar'):
    with self.subTest(unsafe=unsafe):
        archive = make_zip_with_literal_member(unsafe)
        with self.assertRaises(ReleaseValidationError):
            unpack_release(archive, self.destination, self.expected)
        self.assertFalse(self.outside.exists())
```

Also reject duplicates, directory/symlink/special/encrypted entries, corrupt CRC,
ZIP-bomb size declarations/streamed overflow, absent manifest/TAR, extra members,
preexisting/symlink destination or ancestors and changed bytes. A good fixture
with a small literal TAR byte sequence must preserve exact bytes and hashes.
- [x] **Step 2: Implement inspection before extraction, bounded streaming and exclusive staging directory.** Use `ZipFile.infolist()`, inspect `external_attr` and `flag_bits`, exact names, strict JSON; use `os.open(..., O_CREAT | O_EXCL | O_WRONLY | O_NOFOLLOW, 0o600)`. Compare streamed count with declared size. On error remove only resources created by this invocation; never follow a link during cleanup.
- [x] **Step 3: GREEN:** `python3 -m unittest discover -s wordpress/tests/release -p 'test_transport.py' -v`; all release unit tests; `git diff --check`.
- [x] **Step 4: Independent review of the archive trust boundary, including TOCTOU and cleanup ownership.**

### Task 3: One candidate for both real rehearsal consumers

**Files:** Create `wordpress/release/candidate.py`, `wordpress/tests/release/test_candidate.py`; modify `wordpress/bin/build-release`, `wordpress/tests/staging-rollback-runtime.sh`, `wordpress/tests/production-deployment-runtime.sh`; add a test-only SMTP CA mount override under `wordpress/tests/`; create `wordpress/runtime/Dockerfile.dockerignore` for release context hygiene without changing the shared root `.dockerignore` or legacy build contexts. The narrow prerequisite below may also modify `wordpress/bin/deploy-production` and `wordpress/bin/rollback-production`; their bootstrap/update/recovery behavior remains Task 5 work.

**Interfaces:**

- CLI `python3 wordpress/release/candidate.py build --output <new-dir>` builds once, validates clean checkout/provenance/platform and returns `candidate.json` with `image_id`, `git_sha`, `platform` and source metadata; no publish.
- Rehearsals consume `GAMA_RELEASE_IMAGE_ID`, `GAMA_RELEASE_GIT_SHA`, `GAMA_RELEASE_RUN_ID`, `GAMA_RELEASE_RUN_ATTEMPT`, `GAMA_RELEASE_RECEIPT_DIR` and never build or layer-change that candidate. They write `release-regression.json` or `production-runtime.json` only after all real assertions pass.
- CLI `... seal --candidate <candidate.json> --receipts <dir> --output <new-dir>` validates both receipts, inspects the same image, derives package versions inside it, `docker save`s it, hashes it and writes manifest/TAR. No fabricated success receipt.
- Standard build is clean-CI-only, with marker `release`, platform `linux/amd64`, and recorded SHA. Developer local rehearsals may use an explicit non-promotable dirty candidate with a source-content fingerprint; they never produce a trusted release manifest or masquerade as clean CI proof.

Local emulation refinement, 2026-09-08: two amd64 rollback-base attempts
failed with QEMU internal SIGSEGV on the owner's arm64 daemon, before
candidate deployment. Add `--development-platform linux/arm64` only together
with `build --development-dirty`; the compatibility `build-release` wrapper
may accept that option only with its explicit `--test-dirty <marker>` mode.
The default and every clean/release build remain `linux/amd64`. Rehearsals
may consume the native local candidate only with explicit
`GAMA_RELEASE_DEVELOPMENT_PLATFORM=linux/arm64` and an inspected
`development` image marker; other/mismatched platforms or a release marker
with the override must refuse before mutation. Build the separate rollback
base for that same explicitly selected test platform. Add behavioral tests
that the native option cannot produce a release or bypass seal, and that
unset overrides still enforce amd64. Run both real local consumers against
one new native development candidate and retain the failed amd64 evidence.
Native local success does not satisfy the still-required exact amd64 CI gate.

- [x] **Step 1: RED through CLI/subprocess boundary fixtures.** A recording Docker executable returns hand-written inspect/inventory data and only the documented commands. Assert one build, both consumers receive identical image ID, rejected labels/platform never seal, missing/failed/mixed receipts never seal, and dirty source never seals as a release. Mocks substitute only Docker/Git process boundaries; archive/schema logic remains real.

```python
self.assertEqual(result.returncode, 0)
self.assertEqual(read_receipt('release-regression')['image_id'], IMAGE_A)
self.assertEqual(read_receipt('production-runtime')['image_id'], IMAGE_A)
self.assertEqual(recorded_commands.count(['build', 'candidate']), 1)
```

The recording adapter validates full real argv rather than manufacturing the
receipt/assertion. Test expectations use separate literals.
For the full real-consumer orchestration unit test, external `openssl` and
`curl` commands may also use recording boundaries; the scripts and receipt
writers remain real. This unit proof does not establish actual TLS, SMTP or
browser behavior: retain and separately verify the real isolated rehearsals.
- [x] **Step 2: Implement producer and inject candidate into rehearsals.** Keep the previous rollback image separate. Replace production rehearsal's candidate CA `FROM` rebuild with a read-only test-only CA file mount / PHP `openssl.cafile` override, validating real STARTTLS without touching image layers. Generate unique namespaces/ownership tokens before acquiring resources. Install cleanup only after acquiring ownership; never delete an existing stable namespace on a preflight rejection.

The current helpers hardcode a Compose file and stable-only rollback. To run
real helper paths safely on the owner's daemon, add an explicit optional
`--rehearsal-fixture <absolute-dir>` boundary only for proven-owned unique
`gama-wp-production-candidate-test-<token>` namespaces, with dynamic loopback
ports. It selects the repository-owned test Compose override mounting exactly
the fixture CA and PHP CA configuration read-only. The real stable production
namespace must reject this option before any Docker mutation. Rehearsal rollback
may use this same explicit boundary; ordinary production rollback stays stable-only.
Test both refusal and real command wiring. Do not duplicate deployment logic
inside tests or rewrite deployment scripts in a temporary checkout. This does
not create any namespace on the production server or authorize such an operation.
- [x] **Step 3: Emit receipts after success, binding to real container `.Image`, SHA and CI attempt; include the existing browser/acceptance result checks.** Preserve DB row ID/title/content and media hash across deploy and rollback; do not weaken those assertions to mere file existence.
- [x] **Step 4: GREEN unit contracts, then actual isolated Docker rehearsals with the same development candidate.** Preserve owner preview and record limited local provenance and explicit test platform. The exact clean linux/amd64 release path is additionally exercised in CI after source publication is authorized; neither emulation failure nor native local success is a passed CI gate.
- [x] **Step 5: Independent review of candidate identity and namespace safety.**

### Task 4: Read-only provenance and separate registry promotion

**Files:** Create `wordpress/release/github_source.py`, `wordpress/release/promote.py`, `wordpress/tests/release/test_github_source.py`, `wordpress/tests/release/test_promote.py`.

**Interfaces:**

- `resolve_source(event_payload, api, mode, *, operation='standard') -> dict | None`: return complete trusted provenance plus selected artifact metadata. Standard operation with `off`/invalid/non-WordPress mode returns no promotion before artifact/registry/SSH operations. The explicit `first-cutover` operation is a separate path: only mode `off`, a trusted-main manual dispatch, exact selected CI run/attempt and recorded authorization/window may resolve source. It never authorizes an automatic off-mode publication; permission-bearing first-cutover jobs additionally require the configured owner approval boundary.
- API adapter is read-only with explicit repo/run/workflow/attempt/artifact endpoints and complete pagination for checks/reviews/PRs. API errors, redirects to untrusted origins and partial pagination fail closed.
- First-cutover approval contract: the manual promotion run must be its first attempt, from the fetched trusted production workflow on this repository's main. Its creation time and current UTC must be inside the explicit approved start/end window. The fixed `wordpress-production-cutover` environment must have nonempty required User reviewers; actual approval history must contain an unambiguous approved entry by a configured identity, with a canonical JSON comment binding authorization ID, promotion run/attempt, source SHA/run/attempt, immutable artifact ID/GitHub ZIP digest, operators and window. A formatter exposes the exact comment. Observe the configured `prevent_self_review` boolean; do not invent a requirement for two human operators. Team-only/ambiguous configurations and reused dispatch attempts refuse. API history supplies no approval timestamp/attempt: do not fabricate either. A comment or event input alone is never approval; downstream privileged jobs retain the real configured gate.
- Compare event against fetched run, exact workflow path/id, repository IDs and names, full head SHA, event, branch, attempt and successful conclusion. Require all four existing named quality jobs for this exact attempt.
- Require merged PR targeting this repo's main with this merge SHA, a valid approving review and actual required branch/ruleset protections. Do not let an author self-approval, dismissed approval, another PR/SHA or empty configured checks satisfy proof.
- Before promotion also verify all effective required checks for this exact main SHA; until GSWEB-30 this includes `Backend Quality (Symfony)`, `Backend Tests`, `Frontend Quality`, and `End-to-End Tests`. An approved PR's earlier test-merge checks do not substitute for the released main SHA. Pending parallel legacy CI may be observed with a bounded read-only wait, never treated as success; failure or expiry stops promotion. Bind these four mandatory legacy jobs to fetched workflow metadata for the existing exact `.github/workflows/ci.yml` path and their actual Actions runs/jobs; another workflow reusing their names is not proof. Resolve its numeric workflow ID from the API, never guess it.
- CLI `promote.py validate-source --event <json> --mode <mode> --operation <standard|first-cutover> --output <new-json>` uses read-only token; `validate-transport` delegates Task 2; `publish --release-dir <dir> --source <json> --repository <allowed-image-repo> --output <new-json>` has registry write permission plus the read-only GitHub access needed for a fresh provenance/attempt check. It has no other write permission and no SSH/SMTP secrets. Operation comes from the trusted workflow entry point, not an arbitrary field self-asserted by the artifact.
- Registry output contains source provenance, image ID, archive hash and `image=<allowed-repo>@sha256:<digest>`; readback must match candidate config ID, platform, revision, `release` marker and ordered RootFS layers. Publisher never builds or receives SSH/SMTP secrets.

The allowed image repository is exactly
`ghcr.io/grzegorzrzeznikiewicz/gama-wordpress`, preserving the existing
release image repository defined by `wordpress-staging.yml`; no new registry
destination is introduced. Reject other repositories even when supplied to the CLI.

- [x] **Step 1: RED with recorded complete GitHub responses and a local HTTP fixture.** Catch privilege escalation from fork/PR, wrong repo/ref/SHA/workflow, failed run, mixed attempt, empty checks, missing approval and altered archive. Assert rejection before artifact download or Docker publish. Exercise production validator code, not a simulated implementation.

```python
for mutation in ('fork', 'pull_request', 'wrong_sha', 'failed', 'attempt_mismatch'):
    response = run_source_fixture(mutation)
    self.assertNotEqual(response.returncode, 0)
    self.assertEqual(response.registry_operations, [])
```

- [x] **Step 2: Implement exact API validation and bounded artifact download by immutable artifact ID, never latest-by-name.** Recheck source attempt before publishing; bind GitHub ZIP digest and local manifest hash. Unpack under runner temp, not executable checkout.
- [x] **Step 3: Implement Docker `load`, inspect, tag, push and pull by digest with identity readback.** Reject any allowed repository mismatch or newline before writing GitHub outputs. Unit tests assert actual command boundary arguments and refusal ordering, and use no external registry.
- [x] **Step 4: GREEN focused unit tests, all release unit tests, `git diff --check`; independent trust-boundary review.**

### Task 5: Serialized host transaction with durable recovery state

**Files:** Create `wordpress/release/host.py`, `wordpress/release/host_ops.py`, `wordpress/bin/production-release`, `wordpress/tests/release/test_host.py`, `wordpress/tests/release/test_host_ops.py`; modify `wordpress/bin/deploy-production` and `wordpress/bin/rollback-production` where needed to separate bootstrap from code-only update. Update the corresponding first-install/update calls in `wordpress/tests/production-deployment-runtime.sh` and its strict recording boundary in `wordpress/tests/release/test_candidate.py` as needed for that explicit helper interface; preserve the actual scripts and receipt writers.

**Interfaces:**

- `execute(request: dict, state_dir: Path, ops) -> dict` coordinates a validated request with fields `operation_id`, `kind` (`first-cutover`, `standard`, `code-rollback`, `routing-rollback`), full `git_sha`, immutable `image`, validated source evidence and explicit first-cutover authorization reference. No secret values in request/journal.
- Manual recovery uses the existing `.github/workflows/wordpress-production-rollback.yml` and `wordpress-production-rollback` environment. Its closed request variant additionally requires `recovery_authorization` (forbidden on forward requests), bound to actual first-attempt active main workflow_dispatch approval by configured User reviewers. The canonical comment binds authorization ID, promotion run/attempt, operation/target operation IDs, kind, previous SHA/digest, operators and UTC window. Host verifies the actual approval and protected journal/resource target, not a request boolean. Expose a pure pre-gate authorization-comment formatter; no per-run manually provisioned host approval file. Forward current-main freshness must not block authorized previous-version recovery.
- `ops` boundary methods: `preflight(request)`, `current_state()`, `current_main_sha()`, `backup(scope, operation_id)`, `deploy(image, bootstrap=False)`, `verify(image, public=True)`, `switch_routing(target, operation_id)`; production implementations execute strict argv, never request-controlled shell strings.
- Implement GitHub source/current-main, Docker image/platform/resources, repository backup invocation/checksums and HTTPS/content/SMTP-transport checks directly. Only unknown infrastructure-specific off-host backup/encryption/retention/restore and legacy backup/routing-recovery evidence may use explicitly configured root-owned adapters. Require bounded closed JSON, fresh operation/version/resource-bound evidence and actual artifact/checksum/source data, not an unbound success flag. Missing configuration/adapters refuse; this task does not install or configure them on a host.
- Protected state root `/srv/gama-wordpress-production/control` contains `mode`, `accepted.json`, `operation.json`, `incident.json`; advisory `flock`/`fcntl.flock` lock held throughout all mutation and verification. Parent paths, files and operational tools must be root-owned, not symlinks, not group/world writable. Data inputs are parsed, never sourced as shell.
- Read/recheck mode, accepted state, pending journal, current main and actual health only after lock. A stale SHA is `skipped`, duplicate completed operation is idempotent, conflicting ID/SHA/digest or interrupted state rejects.
- Journal starts before mutation and contains actual prior digest, persistent resource IDs and verified off-host backup reference. Atomic fsync+rename state writes; failed/ambiguous terminal state stays blocking until explicit incident resolution.

- [x] **Step 1: RED on real filesystem state plus controlled `ops` boundaries.** Catch two simultaneous deployments or retry mutating twice. Use processes to contend for the real file lock and verify ordered operations, exact journal state and single side effect. Reject symlink/writable parents, pending operation, off mode, partial install and changed main without calls to deploy.

```python
self.assertEqual(execute(stale_request, state_dir, ops)['status'], 'skipped')
self.assertEqual(ops.deploy_calls, [])
```

- [x] **Step 2: Implement standard transaction.** Verify healthy accepted install/platform and mount/source/retention/restore proof before backup; backup before stopping WP; recheck prior volumes. Preserve current DB/uploads, avoid bootstrap/content reset during ordinary update. Verify public HTTPS, homepage/blog/login/logo/menu/contact/indexability and controlled SMTP via the production adapter.
- [x] **Step 3: Implement first-cutover path.** Requires mode `off` and validated authorization for SHA, operators/window. Verify legacy backup and routing recovery record before host mutation; install only the stable WP namespace, verify locally/SMTP, create WP backup, route and publicly verify. Record first acceptance; do not automatically enable standard mode as a side effect of an unverified outcome.
- [x] **Step 4: Implement recovery.** Standard failure restores previous image with current DB/uploads, no PHP-health prerequisite or fresh backup; first failure restores legacy route and keeps WP data. Always preserve original failure and incident barrier. Test signals and lost response by terminating child operation and inspecting durable journal rather than claiming EXIT traps cover SIGKILL.
- [x] **Step 5: GREEN focused tests and actual isolated container data-preserving update/recovery, then independent concurrency/security review.** No live production access.

### Task 6: Wire workflows and retire the staging release path

**Files:** Modify `.github/workflows/wordpress-ci.yml`, `.github/workflows/wordpress-production.yml`, `.github/workflows/wordpress-production-rollback.yml`, `.github/workflows/deploy.yml`, `.github/workflows/rollback.yml`; retire `.github/workflows/wordpress-staging.yml`; update `wordpress/tests/production-deployment-contract.sh`, `wordpress/tests/production-workflow-boundary-contract.sh`, `wordpress/tests/wordpress-ci-contract.sh`; add `wordpress/tests/release/test_workflow_boundaries.py`; add the narrow shared legacy coordinator `wordpress/release/legacy.py`, its fixed entry point `wordpress/bin/production-legacy-release` and `wordpress/tests/release/test_legacy.py`.

**Interfaces:** named helpers and CLI from Tasks 1–5; repository variable `GAMA_DEPLOYMENT_MODE`; four existing named WordPress jobs; GitHub environments `wordpress-production`, `wordpress-production-cutover`, `wordpress-production-rollback`. Mode guard precedes permission-bearing jobs and is rechecked at host execution.

The legacy coordinator reuses the reviewed actual host lock/state/atomic and
bounded operational-process cleanup helpers. It accepts only closed nonsecret
data for the two allowlisted legacy operations, fixed service targets and argv;
no generic shell, WordPress acceptance overwrite, incident clearing, data
restore or removal. Preserve the existing /srv/magento-devops vm2 service
contract and make trusted root-owned configuration/credential prerequisites
explicit. Installed code lives below /srv/gama-wordpress-production/tools;
host-config.json is protected below its control directory. This is an interface
convention, not permission to install/change a real host.

Mandatory actual YAML/permission/dependency-graph validation runs in CI using
js-yaml 4.3.2 from the existing WordPress QA assets lock and pinned Node24.14.0
image. Do not add React-root dependency installation or a local-only optional
parser gate. Extracted-step Python tests remain executable with strict controlled
process boundaries; graph checks include meaningful refusal cases.

Legacy verification preserves the existing external vm2 contract: exact expected
runtime/config image identity and Running=true; if Docker Health exists it must
be healthy, with bounded Compose --wait. Missing HEALTHCHECK is not invented
as a new mandatory external config requirement. Cover absent-healthcheck/running,
healthy, unhealthy, stopped and wrong image. Label this identity/running plus
configured-health evidence, not proof of frontend/contact/API application health;
real legacy application smoke/health acceptance remains an operational prerequisite.
WordPress's mandatory health checks are unchanged.

- [x] **Step 1: RED by executing extracted workflow shell steps against controlled boundary executables and event JSON.** Assert untrusted/off/missing mode does not invoke registry or SSH, both rehearsals consume one image, stale attempt refuses, publish does not build, and no production candidate namespace is created. Replace assertions that require obsolete staging/manual-only behavior with the actual approved contract; preserve remaining real checks.
- [x] **Step 2: Wire the CI build, receipts, seal and artifact upload with SHA/run/attempt name.** Preserve all four gates and exact ZIP tests. Release artifact is uploaded only after its two real rehearsals succeed; later promotion requires success of the complete run. Pin all third-party actions using verified existing full SHAs.
- [x] **Step 3: Wire automatic source validation and independent publisher/deployer jobs.** `workflow_run` successful main push only; trusted default-branch tools validate data before using privileges. Manual first cutover takes exact accepted CI run/attempt plus authorization/window and uses the same artifact verifier, never a rebuild.

```yaml
concurrency:
  group: wordpress-production
  cancel-in-progress: false
  queue: max
```

Use this group for every WordPress/legacy mutation entry point; keep the host
lock for independent operators. Do not cancel running deployment on new merge.
- [x] **Step 4: Guard both legacy deploy and rollback; only `legacy` permits their standard actions.** Require trusted same-repo main source, not bare manual dispatch on any branch. Retire the remote staging workflow without deleting historical evidence or ephemeral test fixtures. Update docs to distinguish GitHub environment permissions from staging servers.
- [x] **Step 5: GREEN behavioral workflow contracts, YAML validation and all source tests; independent complete wiring review.** Do not change GitHub variables, protections, secrets or environments in this session.

### Task 7: Full verification, evidence and handoff

**Files:** Update `docs/agent-workflows/wordpress-migration/GSWEB-25-ci-gates.md`, `GSWEB-26-deployment-rollback.md`, `GSWEB-28-gate-c.md`, `GSWEB-29-production-pipeline.md`, migration README and `confluence/03-wydania.md`, `04-jakosc-i-odbior.md`, `05-utrzymanie.md`; this plan's ledger records exact verified files and commands.

**Interfaces:** all accepted spec §10 cases mapped to executable tests and version-bound evidence; no claim of operational readiness from a local model alone.

- [x] **Step 1: Run `python3 -m unittest discover -s wordpress/tests/release -p 'test_*.py' -v`; all changed shell contracts; `git diff --check`.** Confirm negative failures are genuine failures, not source-text checks. Root170/170 pinned Linux, actual YAML/10 negatives and all changed shell syntax passed after final fixes; current documentation contracts are checked separately. Exact logs are retained in this plan's workspace.
- [x] **Step 2: On an isolated Linux runner/daemon, run all four quality gate equivalents with preserved pinned inputs.** Completed on2026-09-08 after explicit commit/push authorization: head52b5b48, WordPress run34190269971 all4 PASS and legacy run34190269935 all4 PASS. Actual test-merge f145ec3; 171 unit tests, browser6/6 and acceptance13/13, same image46ca523 in both release consumers, exact persistence/media checks after rollback and five data-loss negatives per consumer. Full isolated restore14s. Downloaded transport passed verify_archive with exact provenance/TAR checksum; all21 retained browser last-run files passed. See GSWEB-29-ci-2026-09-08.md. No owner-preview or production mutation. Steps3–5 below retain the prior handoff history; current publication supersedes their uncommitted/no-CI wording, not their operational gates.
- [x] **Step 3: Review the complete uncommitted change with the most capable reviewer.** Complete whole-change review, one combined fix wave and one scoped independent re-review retained. All eleven findings addressed; no new Critical or Important breakage identified in the fix diff. After this verdict, controller made status-only documentation updates; no code/test changes, commits or worktree cleanup.
- [x] **Step 4: Update human docs/Jira/Confluence to distinguish accepted design, local implementation/tests, absent remote CI and absent production deployment.** On2026-09-08 published existing Confluence03/04/05 and verified all144 fragments/11 links; normalized local source text matches all three publications. Saved and reread one dated implementation/documentation summary comment in GSWEB-8, explicitly superseding historical pending-spec/implementation wording. No Jira status changes. Keep old evidence pinned to original SHA. Gate C remains NO-GO while exact new remote CI/owner/operational inputs are unproven.
- [x] **Step 5: Hand off changes uncommitted.** Local implementation and scoped technical review are handed off with Step2 explicitly incomplete, not a whole-epic or production completion claim. Step4 publication completed after browser access was restored. No commit/push/merge permission inferred; request a specific exception for publishing the reviewed branch to existing PR8 for CI only. Actual production remains gated by confirmed host/architecture/access, TLS/routing/SMTP, owner acceptance, backups/restore/retention/alarms, window/operators and separate fresh cutover approval. GSWEB-30 remains behind stabilization and exact removal approval.

## Plan self-review and execution notes

Spec coverage: §1/§6/§7/§11 in Tasks 4–7; §4 in Tasks 1–3;
§5 in Tasks 2/4/6; §8/§9 in Task 5; every §10 case in Tasks 1–7.
No new business functionality or external infrastructure is added.
Human acceptance replaces the earlier written-spec wait, not operational gates.

Documentation paths were resolved against the actual repository; do not create
a second guide for the same responsibility. Detailed task interfaces may be
refined only within this accepted design, with decisions in the ledger and
tests for the resulting real behavior.
