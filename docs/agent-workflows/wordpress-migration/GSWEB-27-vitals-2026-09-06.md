# GSWEB-27 local Core Web Vitals diagnostic — 2026-09-06

This is a reproducible local lab comparison, not field data or release
acceptance. It compares a frozen source-built React home page with an immutable
WordPress candidate and records WordPress-only blog routes. Gate C remains
**NO-GO**. LCP 2500 ms, CLS 0.1 and INP 200 ms are diagnostic references only;
the owner has not approved them as project budgets.

## Result

All 40 retained samples were valid: five fresh browser contexts for every
route and viewport, run sequentially. All reported metrics were finite, the
required browser APIs were supported in a secure localhost context, every
sample included trusted interaction evidence, all three metrics survived the
real pagehide/navigation finalization, and there were no HTTP or console
failures.

| Target | Route | Viewport | LCP median (min–max), ms | CLS median (min–max) | INP median (min–max), ms |
| --- | --- | --- | ---: | ---: | ---: |
| React baseline | home | 1440×900 | 80 (76–88) | 0 (0–0) | 40 (24–48) |
| WordPress | home | 1440×900 | 68 (64–72) | 0 (0–0) | 16 (16–24) |
| React baseline | home | 390×844 | 68 (64–72) | 0 (0–0) | 40 (32–40) |
| WordPress | home | 390×844 | 60 (56–64) | 0 (0–0) | 16 (16–24) |
| WordPress | blog archive | 1440×900 | 52 (48–68) | 0 (0–0) | 16 (8–24) |
| WordPress | blog archive | 390×844 | 44 (44–52) | 0 (0–0) | 16 (16–24) |
| WordPress | representative article | 1440×900 | 48 (44–52) | 0 (0–0) | 24 (8–24) |
| WordPress | representative article | 390×844 | 44 (40–52) | 0 (0–0) | 16 (0–24) |

The WordPress-only routes have no real legacy equivalent, so their baseline is
**N/A**, not zero. The single INP value of zero within the article/phone range
was a callback actually reported by `web-vitals`; the validator distinguishes
that from a missing callback.

## Frozen inputs and conditions

- React source: `c26e19699c7a66a15e0854cf3bb4fce342bf2e2c`, built from its
  lockfile using
  `node:24.14.0-alpine@sha256:7fddd9ddeae8196abf4a3ef2de34e11f7b1a722119f91f28ddf1e99dcafdf114`
  (local image ID
  `sha256:efcd3ed05d1465d72e238ab5bb84f6ed3f425a79266a34e122515a9d130193c9`).
- WordPress source: `c631efbff87dfdb33888e431feac91b3572c4e9f`; measured candidate
  image ID
  `sha256:b25e98f36be5610cabb914c1ea6a0493a4cb8c0ed88e775931c08e02cc9e04cd`
  with the same OCI revision label; Apache 2.4.68 (Debian).
- Browser image ID:
  `sha256:05ae7465aabad3f4e2b1f2302a6e430d991c199895f0fd26c0ac5214f7e60110`;
  Playwright 1.62.1, Node 24.18.1, Chromium 151.0.7922.34 and `arm64`.
- Exact collector: QA-only `web-vitals` 6.2.1, Apache-2.0, injected before
  page scripts. No CDN, analytics endpoint or external metric transmission.
- Browser and WordPress shared the WordPress container's network namespace.
  Both targets used distinct `http://127.0.0.1` loopback ports with no host
  publication, an unthrottled network, fresh context/cache, reduced motion and
  the same browser/viewport settings.
- The baseline was served as unchanged build output by Node's HTTP server with
  no compression and `Cache-Control: no-store`. This is not the historical
  public nginx deployment and does not establish infrastructure parity.

Home samples alternated baseline then candidate within each viewport. Both
semantic adapters navigated to Contact and typed the same name, email, phone
and message without submitting. They produced 145 trusted events per sample
(five clicks, 70 keydowns and 70 input events); the responsive React journey
adds one menu click on phone. WordPress-only samples used two trusted keyboard
events each. The fixture was empty during home measurement. Only afterward it
received one synthetic article and one imported logo attachment.

## Collector controls and lifecycle

The actual pinned-browser control rejected a no-input page as invalid because
INP was missing. A synthetic layout shift reported CLS `0.328125`, and a
trusted main-thread-blocking click reported INP `264 ms`. The separate React
and WordPress semantic-adapter controls both passed with reported INP `16 ms`,
145 trusted events and `formSubmitted: false`.

Each page stores exact local callback events synchronously in same-origin
session storage and mirrors them to the Playwright binding. Navigation to a
same-origin finalizer triggers pagehide/visibility lifecycle reporting; the
next document reads the retained events. Validation requires LCP, CLS and INP
to be present after that transition. It does not require the library to invoke
an unchanged callback a second time after pagehide.

## Evidence and cleanup

Raw evidence is retained at
`/tmp/gama-gsweb27-vitals-evidence-20260906-final2`. It contains phase raw JSON,
the merged 40-sample JSON, summary, actual controls, environment,
command statuses, cleanup result and `SHA256SUMS`. The manifest itself has
SHA-256
`b9d715a40074b241f4fc371fcf5629cbb04227752b9521e8870ba4b9d6af2b37`;
all nine listed files verified.

The exact temporary WordPress `home` and `siteurl` values were restored before
teardown. Owner preview returned HTTP 200 before and after. The diagnostic
namespace `gama-wp-staging-cwv-6f2b`, all of its containers, networks and
volumes, and the source/config fixture were absent after cleanup. A retained
injected-exit control also restored options and removed the exact resources.

## Limits and decision boundary

These very low local loopback values are only comparative diagnostics. They do
not represent CrUX or other field p75, production caching/compression/CDN,
public-network latency, slow devices or networks, native phones, Safari, or
assistive-technology behavior. They do not answer the still-open owner budget
question. Public staging, field evaluation, production approval and the other
GSWEB-27 acceptance evidence remain separate work.
