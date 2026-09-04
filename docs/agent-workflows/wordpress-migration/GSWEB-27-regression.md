# GSWEB-27 — release regression, accessibility and performance

The regression target is the immutable candidate image deployed by the GSWEB-26
staging rehearsal, not the source-mounted development environment. Both the
1440×900 desktop and 390×844 mobile viewports verify the public page, exact logo,
contact form, menu destinations, blog response, duplicate IDs, horizontal
overflow and browser diagnostics.

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
