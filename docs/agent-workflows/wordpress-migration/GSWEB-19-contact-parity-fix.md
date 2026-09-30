# GSWEB-19 / GSWEB-20 — Contact parity correction

Date: 2026-09-05. Branch: `feature/GSWEB-9`.

## Defect and scope

The owner reported that Contact was wrong. The legacy reference is
`src/app/components/site/ContactSection.tsx`, `ContactForm.tsx`, and the
GSWEB-9 baseline screenshots. It uses one centered form card, not a second
promotional text column.

The live WordPress card measured only **50px at a 320px viewport** and 98px
on desktop. A flex child with horizontal auto margins and no explicit width
collapsed around the nested grid's intrinsic sizing. Independently, the Core
Shortcode block applied `wpautop` to multiline form HTML, adding `br` elements
and orphan paragraphs. These defects made the section very tall and unreadable.

## Correction

- Theme 0.4.1: one 100%-width card capped at 42rem (672px), 32px mobile/48px
  desktop padding, single-column mobile fields and paired name/e-mail from
  768px, full-width phone/message, centered 40px submit button. Inputs retain
  the legacy 16px mobile / 14px desktop font size.
- Remove the extra promotional column and nested gray card. Preserve direct,
  unlocked Core blocks and the replaceable shortcode boundary.
- Keep a visitor-facing, editable e-mail fallback when the plugin is inactive.
- Contact plugin 0.3.2: compact inter-element markup and valid error/action
  containers survive Core shortcode formatting without global filter changes.
  Empty error spacing collapses; the empty live region remains available to
  assistive technology. Server validation, rate limiting and mail transport
  remain unchanged.
- Existing editor content, posts, database and uploads were not reset. The
  local front-page template was confirmed to use the theme source.

## Verification

- RED: the new browser geometry test failed with expected width 288px versus
  actual 50px at viewport 320px.
- GREEN: five viewport widths (320, 390, 767, 768, 1440), exact card/field/button
  geometry and input font size, no extra `br`/anonymous paragraphs, no horizontal
  overflow. The font-size assertion was also observed RED before its correction.
- GREEN: browser required-field validation, first-invalid-field focus, Mailpit
  delivery and visible error on simulated transport failure.
- GREEN: desktop/mobile release regression including navigation, logo, Axe
  WCAG 2.1 AA checks and existing performance budgets (4/4 combined tests).
- Visual inspection: corrected desktop in the authenticated Gama Chrome
  profile and mobile screenshot from the pinned browser test runner.

Browser evidence is local at
`/tmp/gama-contact-layout-red-artifacts-4/contact-parity-final-verified/report/`.
The runner used its existing pinned Playwright image with Docker host networking
and `WP_BASE_URL=http://localhost:8090`, so both HTML and canonical CSS/script
URLs were reachable. Assertions now fail if theme or form CSS is not loaded;
merely checking visibility had not caught the original regression.

- GREEN: `wordpress/tests/theme-contract.sh` (source, schema, WPCS, deterministic
  translations/packages and isolation), contact-plugin source contract,
  contact-form browser-gate contract, plugin packaging contract, PHP syntax and
  Prettier checks.
- GREEN: ZIP-only lifecycle for theme 0.4.1 and plugin 0.3.2 in two separate,
  disposable WordPress projects. The theme run included editor save/reset,
  navigation, responsive primitives and the inactive-plugin Contact fallback.
  Browser artifacts are retained at
  `/var/folders/r9/m_xhb8q97jx6v8_rvg2xqd9m0000gn/T/codex-gsweb12-artifacts/gama-theme-package-1788603113-66746-12065/browser-artifacts.tar`.
- Independent review: **APPROVE**, no open P0/P1/P2. The reviewer independently
  exercised the renderer with the installed WordPress code and verified that
  both one and two `wpautop` passes preserve the form, four errors, nonce and
  live region without added `br`/`p` elements. Its mobile-font observation was
  corrected and covered before final verification.

Repeated local sends reached the existing five-per-hour anti-spam limit during
one intermediate run. Only local contact-rate transients were cleared; the
final clean-fixture browser run passed 4/4. The test counters were cleared again
afterward so the owner's manual test is not blocked. Production anti-spam
configuration, the public site's traffic and content were not changed.

## Follow-up candidate verification

The clean source commit `04b306398cd2a071a38799e85def56745a358a05` then passed
`wordpress/tests/staging-rollback-runtime.sh` (exit 0) in the separate project
`gama-wp-staging-9342-69152`: 2/2 release regression and 13/13 acceptance tests,
including the new exact Contact geometry test and Editor changes to Contact.
Deployment and rollback to the actual preceding commit preserved database and
uploaded media. The local rehearsal archives are retained under
`/tmp/gama-contact-release.zBUpFs/`; image identities and archive checksums are
recorded in [Gate C](GSWEB-28-gate-c.md).

The disposable test project was cleaned up, while the user's `gama-wordpress`
preview remained healthy at HTTP 200. Jira GSWEB-19 is now `Testowanie`, with
the correction, test evidence and remaining owner acceptance recorded in its
comment. This does not claim a public staging deployment or production mail
delivery.

## Release boundary

This is a local correction, not an epic completion or production deployment.
The previous Gate C technical approval must not be reused for the old UI or
the new release without renewed candidate/staging verification. The isolated
candidate rehearsal is now green; remote CI, usable public staging and owner
acceptance remain outstanding, so Gate C stays NO-GO. No push, published
artifact, production cutover or legacy retirement was performed as part of
this fix.
