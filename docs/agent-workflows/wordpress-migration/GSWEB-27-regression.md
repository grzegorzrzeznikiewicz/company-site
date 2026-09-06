# GSWEB-27 — browser and viewport regression evidence

The automated release matrix contains six cases: Chromium and WebKit at desktop
1440×900, tablet 768×1024 and phone 390×844. The unnamed Chromium project keeps
the existing full-suite and screenshot identities. The named `webkit` project
collects only `release-regression.spec.ts`, so it does not duplicate Editor,
Admin or screenshot suites. Navigation follows the menu actually rendered at
each breakpoint: tablet uses visible primary links at 768 px and phone uses the
Core responsive dialog.

Every case verifies the immutable candidate rather than a source-mounted site:
homepage status and content, exact logo, contact form, navigation destinations,
blog status, duplicate IDs, horizontal overflow, WCAG 2.0/2.1 A/AA axe results,
browser diagnostics and the existing timing/resource/transfer budgets.

Automated accessibility uses `@axe-core/playwright` 4.13.0 with the WCAG 2.0 A/
AA and WCAG 2.1 A/AA rule tags. The suite also retains the existing keyboard,
focus, semantic navigation, form-label and editor tests. Automated scans do not
replace the manual Editor/Admin and assistive-technology checks in GSWEB-28.

Local-container budgets are TTFB below 1.5 s, DOMContentLoaded below 4 s, load
below 5 s, no more than 50 resources and at most 1 MB transferred. Console
errors, uncaught page errors and failed requests are zero-tolerance. These are
release gates, while production monitoring thresholds are defined separately in
the cutover runbook.

Playwright 1.54.2 was upgraded to 1.62.1 after the audit identified
GHSA-7mvr-c777-76hp. The npm audit is clean, and the matching Microsoft browser
image is pinned by digest. CI stores the full HTML report, last-run status,
screenshots and traces (when produced) as the SHA-qualified
`wordpress-release-evidence` artifact for 14 days.

## Local proof — 2026-09-06

This is dated local-container evidence, not CI or public-staging acceptance.

- Environment: isolated Compose namespace
  `gama-wp-staging-4789-97159`; HTTP-only internal origin
  `http://wordpress`; host local preview remained HTTP 200 at
  `http://localhost:8090/` after exact-label cleanup.
- Candidate image:
  `sha256:3ea406e7c81293a5ba35b222a7911818bcf9d673165c0f9b3d60c478ecd3caa5`;
  OCI revision `1398f41dbcb39a627ff554c1cf96c801f5f6e552`.
- Rollback baseline image:
  `sha256:b9fe0078c4db6723ddad2f005328613bbbd15ebd4d075396381cc0a8925f4507`;
  revision `043beee6490664758bdbbff55d7a9cdf9156a398`.
- Browser test image:
  `sha256:e3010fa158c210804902a1b42e3bffc2be3489de45da7b16a884895ab6d761ea`,
  built from the pinned Playwright 1.62.1 Noble image digest
  `sha256:dcc5531e97840b9b5e794f2814476b21571c5124a3fca2267d73041f56e7580e`.
- Engines: Chromium `151.0.7922.34`; WebKit `26.5` (Linux Playwright
  emulation, Safari 26.5 user agent; not native Safari hardware).
- Raw evidence:
  `/tmp/gsweb27-browser-matrix.CfMnoH/gama-wp-staging-4789-97159-browser-artifacts.tar`
  (HTML report, `.last-run.json`, three WebKit screenshots/error contexts/traces,
  and all six inline performance attachments).

| Engine   | Viewport | Result              |    TTFB | DOM loaded |    Load | Resources |  Transfer |
| -------- | -------- | ------------------- | ------: | ---------: | ------: | --------: | --------: |
| Chromium | desktop  | PASS                | 28.5 ms |    73.6 ms | 73.7 ms |        11 | 278,820 B |
| Chromium | tablet   | PASS                | 29.9 ms |    59.7 ms | 59.7 ms |        11 | 166,482 B |
| Chromium | phone    | PASS                | 27.4 ms |    57.1 ms | 57.3 ms |        11 | 166,482 B |
| WebKit   | desktop  | FAIL at diagnostics |   26 ms |     126 ms |  126 ms |        13 | 284,506 B |
| WebKit   | tablet   | FAIL at diagnostics |   36 ms |     138 ms |  138 ms |        13 | 172,168 B |
| WebKit   | phone    | FAIL at diagnostics |   28 ms |     126 ms |  126 ms |        13 | 172,168 B |

All three WebKit cases reached and passed the functional, accessibility,
overflow and performance assertions, then failed the unchanged zero-tolerance
console assertion. WebKit emitted exactly
`Prefetch request denied: URL must be secure (HTTPS)` eight times on desktop,
eight times on tablet and twice on phone. `pageerror` and `requestfailed` stayed
empty, and every recorded HTTP request completed successfully.

Read-only trace inspection links the message to the environment with strong but
not absolute attribution: both captured WordPress documents contain a Core
`<script type="speculationrules">` prefetch rule, the tested origin is plain
HTTP, and the trace records the message as a browser console error at
`<anonymous>:0` with no failed network request or application stack. This is
therefore treated as a WebKit secure-prefetch policy conflict in the HTTP-only
test environment. The raw trace cannot prove how native Safari on an HTTPS
deployment behaves, so this is neither a final Safari failure nor a full website
functional pass. No message was filtered, security was not disabled, and no
budget was widened.

The matrix result is 3/6 PASS. A separate HTTPS test-environment run is required
for WebKit/Safari acceptance. GSWEB-27 also remains open for manual
accessibility/assistive-technology checks including native 200% zoom,
CWV/Lighthouse baseline comparison, agreed LCP/CLS/INP budgets, CI evidence and
owner/public-staging approval.

## HTTPS test-environment follow-up — 2026-09-06

The same unchanged six-case matrix subsequently ran against the disposable
internal origin `https://wordpress-tls`. A short-lived CA and SAN leaf were
generated for this rehearsal only. The CA was trusted only inside fresh browser
containers: the OS store for WebKit, Chromium's
`/root/.local/share/pki/nssdb`, and `NODE_EXTRA_CA_CERTS` for the Playwright
request context. Certificate validation was not bypassed and no host trust
store, browser profile, public environment or release application image was
changed.

Before the positive run, both engines rejected the same origin without the CA:
Chromium reported `ERR_CERT_AUTHORITY_INVALID` and WebKit reported an
unacceptable TLS certificate. After importing the CA, both engines rejected an
alias outside the certificate SAN; Chromium reported
`ERR_CERT_COMMON_NAME_INVALID` and WebKit again reported an unacceptable TLS
certificate. The correctly named origin then returned HTTP 200 in Chromium,
WebKit and the Playwright request context. The valid probes recorded no HTTP
resource URL: Chromium observed 13 HTTPS requests and WebKit observed 15.

The release matrix result over verified HTTPS is **6/6 PASS**:

| Engine   | Viewport | Result |    TTFB | DOM loaded |     Load | Resources |  Transfer |
| -------- | -------- | ------ | ------: | ---------: | -------: | --------: | --------: |
| Chromium | desktop  | PASS   | 33.0 ms |    94.3 ms |  94.4 ms |        11 | 278,830 B |
| Chromium | tablet   | PASS   | 27.6 ms |    58.6 ms |  58.6 ms |        11 | 166,492 B |
| Chromium | phone    | PASS   | 30.7 ms |    60.5 ms |  60.6 ms |        11 | 166,492 B |
| WebKit   | desktop  | PASS   | 40.0 ms |   141.0 ms | 141.0 ms |        13 | 284,516 B |
| WebKit   | tablet   | PASS   | 45.0 ms |   148.0 ms | 148.0 ms |        13 | 172,178 B |
| WebKit   | phone    | PASS   | 46.0 ms |   148.0 ms | 148.0 ms |        13 | 172,178 B |

Full rehearsal evidence:

- Namespace: `gama-wp-staging-11623-4388`; no TLS-sidecar host port.
- Candidate image:
  `sha256:60f33f8e680c794ba106831471a18d1da894cd058e7dd6ff8f31b24e5cec53e9`;
  OCI revision `d9486d319fbe69d35d5e4f2f191f27253b537541`.
- Browser QA image:
  `sha256:9ad4a30dc3f3905453d5422b22c4decd3b2dde229bf6352c5d13c194650c2b4b`.
- Ephemeral CA SHA-256 fingerprint:
  `EE4DA9618D07E1F6EA97E6E56A45786F98A794B3D34020466A5C33E8C080D587`;
  leaf fingerprint:
  `E33FCADF3ED3CDA4DBDE21B5B8330C4F9CC7B868D1FB02F5A071B235633B2549`.
- Browser archive:
  `/var/folders/r9/m_xhb8q97jx6v8_rvg2xqd9m0000gn/T/gsweb27-https-final.MOQu39/gama-wp-staging-11623-4388-browser-artifacts.tar`,
  SHA-256
  `403c39bc7de7d0d3d132ed9c1e7a3eb77a549e487e20013da4f21362ed8f83fa`.
- Acceptance archive in the same directory:
  `gama-wp-staging-11623-4388-acceptance-artifacts.tar`, SHA-256
  `ef9e533e5a0a82d65195dc8b8275d5d2ac6f1d8a236704c1d005911d48a66c8f`.
- Full `staging-rollback-runtime.sh`: HTTPS regression 6/6, acceptance
  13/13, exact persistent post/upload checks and immutable candidate-to-baseline
  rollback all passed.

Success and injected-failure cleanup checks restored the exact disposable
`home` and `siteurl` values, removed the sidecar and browser trust volume, and
deleted the generated CA/private-key fixture. The browser archive contains the
public certificate fingerprints and probe results, but no private-key file or
PEM private-key marker.

This closes only the HTTP-environment explanation for the prior WebKit console
errors. It is local Linux Playwright evidence, not native Safari, CI or public
staging acceptance. GSWEB-27 still requires the separately owned CWV/Lighthouse
baseline and budgets, assistive-technology/native-browser evidence, CI
retention, and owner/public-staging approval.
