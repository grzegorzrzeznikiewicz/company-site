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
