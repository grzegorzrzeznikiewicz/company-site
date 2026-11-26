# Extending the Gama Software WordPress site

This guide is the entry point for anyone (person or agent) changing the theme
or adding a plugin. The full package decision record is
[GSWEB-11 architecture](agent-workflows/wordpress-migration/GSWEB-11-architecture.md);
this page summarises the rules and adds the start checklist and Definition of
Done.

## Theme or plugin?

| Put it in the theme `gama-software` | Put it in a plugin `wordpress/plugins/<slug>` |
| --- | --- |
| Templates, template parts, patterns | Anything that must survive a theme switch |
| Global Styles and `theme.json` tokens | Mail, integrations, REST endpoints, cron |
| Presentation assets (logo, icons, CSS) | Capabilities, options, custom post types, schema, migrations |

One plugin owns one durable capability. Existing plugins: `gama-contact`
(form and delivery), `gama-seo`, `gama-security`, `gama-mail-transport`
(production SMTP), `gama-local-mailpit` (local only).

## Rules that apply to every package

- **Blocks:** prefer core blocks, patterns and `theme.json`. A custom block uses
  the `gama-software/*` namespace and a `block.json`; register it from the
  owning package.
- **Hooks and names:** use the package's own prefix (`gama_<slug>_`), constant
  prefix (`GAMA_<SLUG>_`), `GamaSoftware\<Package>` namespace and text domain
  equal to the slug. REST routes use `<slug>/v1`.
- **Compatibility:** WordPress 7.1, PHP 8.4, GPL-2.0-or-later with the full
  licence text in the ZIP.
- **Versioning:** SemVer per package; bump the header, `readme.txt`/`style.css`
  and `CHANGELOG.md` together. A new plugin starts at `0.1.0`.
- **Dependencies:** add `composer.json`/`package.json` only when something
  actually consumes them, always with a committed lock file. Never package
  `node_modules` or an unused `vendor`.
- **Packaging:** every shipped file is on the positive allowlist used by
  `wordpress/bin/package`; a new file must be added there and to the package
  contract first. Builds are byte-reproducible.
- **External extensions:** only paid-licence-free extensions, recorded in
  `wordpress/config/extensions.lock.json` with version, source, SHA-256 and the
  owning Jira decision. The first one is Site Kit by Google (`google-site-kit`,
  GSWEB-31): it is fetched with checksum verification at image build time and
  by `wordpress/bin/fetch-site-kit` for local development, never committed.
- **Distribution:** ZIPs in `wordpress/dist` are local artifacts. Uploading or
  publishing one needs separate owner approval.

## Start checklist (before writing code)

- [ ] The GSWEB ticket exists in Jira, is assigned and moved to **W toku**, with
      the plan in a comment.
- [ ] Branch `feature/GSWEB-<n>` from the current `origin/main`.
- [ ] Decide theme vs plugin with the table above and name the files you will
      touch.
- [ ] Identify the narrowest existing contract test for the area
      (`wordpress/tests/*-contract.sh`, `wordpress/qa/e2e/specs/*`).
- [ ] Local WordPress runs: `wordpress/bin/start`, site on
      `http://localhost:8090`.

## Definition of Done

**Theme change**

- [ ] Editable in the Site Editor; no hard-coded content that editors need to
      change.
- [ ] Theme contract tests and relevant Playwright specs pass locally;
      responsive check at 320, 768 and 1440 px.
- [ ] Version, `CHANGELOG.md` and `languages/gama-software.pot` updated; new
      files added to the package allowlist.
- [ ] `wordpress/bin/package theme gama-software` and
      `wordpress/bin/test-package` pass on a clean ZIP.

**Plugin change or new plugin**

- [ ] Works with any theme (tested by switching Core themes in the ZIP
      lifecycle).
- [ ] Activation is idempotent; deactivation and default uninstall follow the
      documented data policy.
- [ ] Inputs sanitised and validated, outputs escaped, nonces and capability
      checks on every write path.
- [ ] Plugin contract, PHPCS and PHPStan pass; clean-ZIP lifecycle passes.
- [ ] Version, `CHANGELOG.md`, `readme.txt` and `.pot` updated; allowlist and
      read-only Compose mount added for a new plugin.

**Every change**

- [ ] Verified on local WordPress first, then the PR's four WordPress quality
      gates are green.
- [ ] Jira ticket has a progress comment with the PR link and moves to
      **Testowanie** after merge, **Gotowe** after production verification.
