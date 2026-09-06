# GSWEB-27 HTTPS rehearsal implementation report

Date: 2026-09-06 (Europe/Warsaw)

## Status

**DONE_WITH_CONCERNS** — the bounded HTTPS test-environment follow-up, signal
cleanup correction and local port-validation portability correction are
implemented and verified. Fix round 2 is ready for focused independent
rereview, but the published remote run is still failed and a fresh remote CI
run is required. GSWEB-27 as a whole remains open for native/assistive-
technology, CWV/budget, CI, public-staging and owner evidence.

## Change

- Added an Apache TLS reverse-proxy sidecar using the already pinned
  `wordpress:7.1.0-php8.4-apache` digest. It has no host port, preserves the
  request host, sets `X-Forwarded-Proto=https`, reverses proxy redirects and
  accepts TLS 1.2+ only.
- Added per-run ephemeral CA/leaf generation, restrictive private-key modes,
  exact disposable `home`/`siteurl` switching/restoration, and success/failure
  cleanup of the sidecar, trust volume and generated fixture. `EXIT` preserves
  its incoming status, while real `INT` and `TERM` return 130 and 143 after the
  same cleanup.
- Added container-only OS/NSS/Node trust. Chromium uses
  `/root/.local/share/pki/nssdb`; an existing legacy NSS DB in the fresh
  container is also respected. No CA key enters the browser container.
- Added only `libnss3-tools` 3.98-1ubuntu0.2 to the QA image, using the reviewed
  amd64/arm64 official URLs and exact SHA-256 mapping. The build rejects an
  unsupported architecture or mismatched `libnss3`/`libnspr4` dependency.
- Added real certificate-negative probes and a valid HTTPS/mixed-content/Node
  request-context probe. The unchanged six cases, Playwright configuration,
  budgets and zero-tolerance diagnostics remain intact.
- Wired the lifecycle and safety contract into the existing release regression
  and documented the dated result.

## TDD / diagnostic record

1. Existing retained HTTP baseline: Chromium 3/3 PASS, WebKit 0/3 at the
   unchanged console gate with `Prefetch request denied: URL must be secure
(HTTPS)`; archive SHA-256
   `245aafd86537a10c8970df7db4494d79d9818482dd34a3755149ea1586999ac6`.
2. RED: `wordpress/tests/release-regression-contract.sh` reached the unchanged
   six-case collection contract, then failed because
   `release-tls-probe.cjs` did not exist.
3. GREEN: `wordpress/tests/release-https-contract.sh` passed after the minimal
   sidecar/trust/probe implementation.
4. Portability RED/GREEN: the new contract rejected Bash-4-only `mapfile` on
   the repository's Bash 3.2 host; the runtime now uses a portable exact-count
   check.
5. Focused runtime RED: all three TLS probe modes passed, then the closed
   timeout-policy contract rejected a helper copied under `specs/support`.
   Root cause was scanner scope, not TLS. The image now moves the helper outside
   the collected specs tree; the source helper itself now uses a direct ESM
   Playwright import and the existing allowlisted `WP_BASE_URL`, so the source
   semantic policy passes without an exclusion. A container
   `npm test -- --list` then passed the semantic policy and collected exactly
   45 cases, including the existing six release cases.
6. Focused runtime RED: all six release cases passed, then public metadata
   serialization failed due nested shell quoting. Metadata is now generated as
   a fixture and installed into the artifact volume.
7. Focused GREEN: certificate negatives, valid Chromium/WebKit/Node HTTPS,
   mixed-content probe, six cases, metadata/archive creation, exact URL restore
   and teardown all completed. Archive SHA-256:
   `e8210e1efb55f33d2c84270124c1af98b421bf59c557c2a40eb685215c1b3970`.
8. The initial injected exit-97 check returned 97 and cleanup passed, but the
   first implementation report did not retain its raw command/output directory.
   The independent review correctly treated that as an evidence gap and also
   found that the shared `EXIT INT TERM` trap could convert cancellation to 0.
9. Signal RED used the actual HTTPS helper, paused only after its sidecar was
   healthy, and delivered real `INT`. The helper returned 0 instead of 130,
   while the audit still proved exact URL restoration and removal of the
   sidecar, trust volume and private-key fixture. The focused runtime correctly
   failed with status 1. Retained RED directory:
   `/tmp/gsweb27-https-cleanup-red-dbadc8a-final.kqJ36c`; `int.audit` SHA-256:
   `065e28c77e8d5072d7c154fead23a77adc1c9ed7f5db29efc17ffcff7efaf0f8`;
   `command-output.log` SHA-256:
   `6ab9b9bfe3baf56f077667d7cd5068c1aac5001c0f099e76ddbb8564517cfa6c`.
10. Signal GREEN separated the traps: `EXIT` passes its actual status to
    cleanup, `INT` passes 130, and `TERM` passes 143. The actual helper then
    returned 130, 143 and the retained injected 97 respectively. Every case
    restored both exact URLs and left its exact sidecar, trust volume and TLS
    key fixture absent.

## Focused signal-cleanup verification

The bounded runtime used one fresh exact-label fixture and the same already
verified candidate/browser image pair from the successful rehearsal:

```text
GAMA_RELEASE_HTTPS_CLEANUP_CANDIDATE_IMAGE=sha256:60f33f8e680c794ba106831471a18d1da894cd058e7dd6ff8f31b24e5cec53e9 \
GAMA_RELEASE_HTTPS_CLEANUP_BROWSER_IMAGE=gama-wordpress-browser:gsweb27 \
GAMA_RELEASE_HTTPS_CLEANUP_EVIDENCE_ROOT=/tmp/gsweb27-https-cleanup-green-dbadc8a.8eHBcv \
wordpress/tests/release-https-cleanup-runtime.sh
```

Result: exit 0 in namespace
`gama-wp-staging-https-cleanup-11744-9268`.

- `INT`: expected/actual 130/130.
- `TERM`: expected/actual 143/143.
- injected post-sidecar failure: expected/actual 97/97; retained runtime log
  contains `Injected HTTPS cleanup failure-path probe.`
- all three case audits: original/restored `home=http://wordpress` and
  `siteurl=http://wordpress`; exact sidecar absent; exact browser trust volume
  absent; exact TLS fixture absent; private key absent.
- final namespace audit: no containers, no Compose volumes and no staging
  fixture.
- tested candidate revision remained
  `d9486d319fbe69d35d5e4f2f191f27253b537541`, rather than the later
  documentation-only repository HEAD.

Retained GREEN evidence directory:
`/tmp/gsweb27-https-cleanup-green-dbadc8a.8eHBcv`.
Important SHA-256 values:

- `command-output.log`:
  `d5106a5345594e903970bbf97543e6304363ea8fe3030092985910e7c97f7d09`;
- `int.audit`:
  `976836564a8a188c8f4c251713430ffc76a5f624aecf3c1b844a7ba663cc7163`;
- `term.audit`:
  `1e32fd3dc1af4d181618d85ba1968778af2a845e045414aec63be11aa4d126e0`;
- `exit-97.log`:
  `43472a6fa48394fe814d77e1ee86075ffc7bd88b837784eb8e659d296d099ec5`;
- `exit-97.audit`:
  `777f29ff58d421ca251f7716fd922b759c4f50a4cf6c73c48798f567ca8e25cb`;
- `overall-cleanup.audit`:
  `49b14556930378209cdf5a3fc6f89059c04988faae77190a0ccc11cbd71e82e7`;
- `SHA256SUMS`:
  `2306cbff1b847e882a4b7823ef02d29738ca453a01874e641a3580b4c1799b88`.

`wordpress/tests/release-regression-contract.sh` and
`wordpress/tests/release-https-contract.sh` both passed after the correction.
The already successful six-case and 13-case runtimes were retained rather than
rerun because this change is confined to host-shell exit propagation and its
focused cleanup regression.

## Remote CI port-validation correction

Published base `177afe9209e222bf8d519ccf44ec10d779c6ece6` was exercised by
remote run `34033786293`, job `101488200053`, at PR merge revision
`c9e73849342b1041df2842511a398868cfc3a671`. Direct evidence from the complete
job log is limited to the following sequence: the unchanged six-case collection
contract passed, the TLS sidecar reached `Healthy`, no TLS probe acknowledgement
was printed, and the runtime finished with exit 1. The uploaded browser archive
contains only its root directory.

- full remote log:
  `/tmp/gama-ci-177afe9.vJE57g/release-regression.log`, SHA-256
  `c44d318947eeaa4dbbf72cfc982e889077536a82457d498c08eed35d70c9c44d`;
- empty remote browser archive:
  `/tmp/gama-ci-177afe9.vJE57g/release/gama-wp-staging-21310-2635-browser-artifacts.tar`,
  SHA-256
  `f13f329e77aca432b2e13d4400eebe084fdfb626819676a6b531aed3a2f3951f`.

### Diagnosis and RED

Local Docker Engine 29.7.2 / Compose 5.5.0 directly reports
`HostConfig.PortBindings={}` for an unbound container. Bash 3.2.57 locally
continues after the old standalone false `[[ "{}" == null ]]`, while Bash 5 in
the pinned WordPress container exits 1 for the same command under `set -e`.
That shell difference explains why the local assertion was silently ineffective.

The unmodified real helper then ran in the exact disposable namespace
`gama-wp-staging-https-port-20663-15568`. Its live sidecar was captured with
`PortBindings={}`. On Bash 3.2 the helper incorrectly continued through all TLS
probes and the six-case matrix and returned 0; this is direct evidence of the
local masking behavior, not evidence for this fix. It restored both exact URLs
and removed the sidecar, trust volume, TLS fixture and namespace. Retained
diagnostic directory:
`/tmp/gsweb27-https-port-red-177afe9.2wFBUR`; `runtime.audit` SHA-256
`fe67a9309771274089fb7f9dd03a19f48a3f8108f5881b50954e20d010175249` and
`runtime.log` SHA-256
`e76e679af45c61b60e75ccb8fe9c494f6f363dcb4890f799795d1ddbd03f67f9`.

The test-first port contract was RED with status 64 because the runtime did not
yet expose its real validation boundary without starting the lifecycle. Its
retained output is
`/tmp/gsweb27-https-port-contract-red-177afe9.fRPDhQ/output.log`, SHA-256
`1ded05671af7afcb237422788aecfdf85b0ce6147a7aac5ceef452c4342ab9f3`.

The exact runner `PortBindings` value and runner Bash version were not printed
in the remote log. Attribution of that remote exit to `{}` plus the Bash
behavior is therefore a strong inference from the earliest possible failing
operation and the direct local reproductions, not a direct observation of the
runner value.

### Short contract and GREEN

The amended runtime has one sourceable validation function used by its real
lifecycle:

- `docker inspect` must itself succeed; missing/failed inspection is rejected;
- only `null` and `{}` mean no host publication;
- every nonempty or malformed value is rejected;
- the TLS sidecar Compose definition remains without `ports` or host networking.

The focused behavioral contract uses actual Docker objects. It accepts a real
unbound `{}` container, rejects a running loopback-only publication with a
nonempty `443/tcp` binding, rejects a missing container fail-closed, and also
checks the older `null` serialization. Final contract output:
`/tmp/gsweb27-https-port-contract-green-final-177afe9.78dZhT/output.log`,
SHA-256
`6f0e1ec1dba2a951fcaf318ac33ae4d1d2d1ee4bbc3b14e203c4ef647cdf6d46`.

The real helper then passed the formerly failing boundary with live
`PortBindings={}` in the same exact disposable project. Focused paths returned
`INT=130`, `TERM=143`, and injected failure 97. All three restored exact
`home=http://wordpress` and `siteurl=http://wordpress`; their exact sidecars,
trust volumes, TLS fixtures and private keys were absent. Final cleanup found no
project containers, Compose volumes or staging fixture.

Retained runtime GREEN directory:
`/tmp/gsweb27-https-port-runtime-green-177afe9.vAkz7u`. Important SHA-256
values:

- `int.audit`:
  `83a9d98e40d89429f176b7280d99ac27ba6a33e518a057d0383478ad84305e52`;
- `term.audit`:
  `57c5e0461ec92d0fdfa8992af59f03fedc2609002c65ff4fb7cdb8183188c7ca`;
- `exit-97.audit`:
  `0022da1b7138a4add51d2379208e9e0b50baeea88bf40abc5b23671d989da537`;
- `overall-cleanup.audit`:
  `cdc52cccd310c1075982e178b525e47ad537d65a6b49ca139d5fc7170e8e71dc`;
- `SHA256SUMS`:
  `20cca3907f83b9adf172c83ea4a9ca9dbc6618bca98bc07b6fb500ea5ba6d007`.

This GREEN is deliberately limited to the corrected port boundary and retained
failure/signal cleanup behavior. The old successful local matrix is not
attributed to this fix, the 13-case acceptance runtime was not rerun, and a
fresh full remote CI run remains required after focused review.

## Full verification

Command:

```text
GAMA_ROLLBACK_BASE_REF=qa/wordpress-rollback-baseline-2026-09-05 \
GAMA_RELEASE_ARTIFACT_ROOT=<unique directory> \
wordpress/tests/staging-rollback-runtime.sh
```

Result: exit 0. Namespace `gama-wp-staging-11623-4388` completed:

- certificate negatives: Chromium/WebKit reject untrusted CA;
- hostname negatives: Chromium/WebKit reject a trusted wrong hostname;
- valid HTTPS: Chromium/WebKit and Playwright request context return 200;
- mixed-content request lists: empty in both engines;
- release matrix: 6/6 PASS;
- immutable staging acceptance: 13/13 PASS;
- candidate image:
  `sha256:60f33f8e680c794ba106831471a18d1da894cd058e7dd6ff8f31b24e5cec53e9`,
  revision `d9486d319fbe69d35d5e4f2f191f27253b537541`;
- browser QA image:
  `sha256:9ad4a30dc3f3905453d5422b22c4decd3b2dde229bf6352c5d13c194650c2b4b`;
- ephemeral CA SHA-256 fingerprint:
  `EE4DA9618D07E1F6EA97E6E56A45786F98A794B3D34020466A5C33E8C080D587`;
  leaf fingerprint:
  `E33FCADF3ED3CDA4DBDE21B5B8330C4F9CC7B868D1FB02F5A071B235633B2549`;
- rollback baseline image:
  `sha256:b9fe0078c4db6723ddad2f005328613bbbd15ebd4d075396381cc0a8925f4507`;
- persistence/upload and code-only rollback assertions: PASS;
- browser archive SHA-256:
  `403c39bc7de7d0d3d132ed9c1e7a3eb77a549e487e20013da4f21362ed8f83fa`;
- acceptance archive SHA-256:
  `ef9e533e5a0a82d65195dc8b8275d5d2ac6f1d8a236704c1d005911d48a66c8f`.

Raw evidence directory:
`/var/folders/r9/m_xhb8q97jx6v8_rvg2xqd9m0000gn/T/gsweb27-https-final.MOQu39`.

The browser archive `.last-run.json` is `passed` with no failed tests. It
contains the public CA/leaf fingerprints and the three TLS probe JSON files,
and contains neither private-key filenames nor a PEM private-key marker. Final
resource audit found no containers for the rehearsal project, no labeled
browser trust volume, and no generated TLS fixture.

## Remaining limits

- This is local Linux Chromium/WebKit emulation, not native Safari hardware.
- The unrelated pre-existing `release-acceptance-contract.sh` remains RED at
  its `Technical verdict` text check because that phrase is absent from
  `GSWEB-28-gate-c.md` both at `HEAD` and in the worktree. This follow-up did
  not change that out-of-scope document; the real 13-case acceptance runtime
  passed twice during the full rehearsals.
- No public infrastructure, browser/OS host trust, user profile, release image,
  application dependency, Playwright policy, workflow, secret or package lock
  was changed.
- GSWEB-27 still needs the broader acceptance evidence listed in the dated
  regression document.
