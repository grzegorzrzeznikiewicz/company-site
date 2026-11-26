# Code review rules

Review rules for this repository, applied by `om-code-review` and `om-auto-review-pr` in addition to their built-in checklists. The structure follows [open-mercato/skills CODE_REVIEW.md](https://github.com/open-mercato/skills/blob/main/CODE_REVIEW.md); the priorities are this repository's own. This is the Gama Software company site: a WordPress block theme, first-party plugins and a fail-closed release pipeline. **Every approved PR that merges to `main` is deployed to production automatically**, so an approval is a production release decision, not a style opinion.

## Review priorities

1. **Production safety** — a merge to `main` goes live. Flag anything that can take the site down, lose content or leak data: destructive migrations or `wp` commands without a guard, unbounded queries in templates, fatal-prone PHP (undefined functions or classes outside their plugin, missing `function_exists`/`class_exists` guards across plugins), changes that assume state only present on a developer machine.
2. **Release pipeline integrity** — `.github/workflows/**`, `wordpress/release/**`, `wordpress/deploy/**`, `wordpress/runtime/**`, `wordpress/routing/**` and `wordpress/bin/**` are the fail-closed deployment boundary. Any change that relaxes a check, broadens a token permission, unpins an action or image digest, adds a network path, weakens the owner/AI review proof (`GAMA-SOLO-AI-REVIEW-V1`, `wordpress/release/ai_review_gate.py`) or skips a quality gate is a **Blocker** unless the PR states it explicitly and the matching contract test is updated in the same PR.
3. **WordPress security** — escape on output (`esc_html`, `esc_attr`, `esc_url`, `wp_kses_post`), sanitize and validate on input, nonces plus capability checks (`current_user_can`) on every state-changing request, `$wpdb->prepare` for every query with variables, no direct file access without `defined( 'ABSPATH' )`. A missing check on a public endpoint (REST route, `admin-post`, AJAX, the contact form) is a **Blocker**.
4. **Privacy and legal (RODO)** — no new cookies, trackers, third-party scripts, fonts or embeds without consent handling and a matching update of the privacy policy content. Personal data from forms must not reach logs, error messages or analytics.
5. **Secrets hygiene** — no tokens, passwords, `.env` content, SMTP or server credentials in code, fixtures, logs or docs. Only `wordpress/.env.example` with placeholders is committed.
6. **Reproducibility** — third-party plugins and images are pinned by version and SHA-256 and baked into the image (`DISALLOW_FILE_MODS` is on in production). A dependency added without a pin, a lock update or the extensions lock entry is a **Major** finding; installing anything through wp-admin is not a supported path.
7. **Editor experience and content contracts** — prefer native blocks, patterns and `theme.json` over custom JavaScript and hard-coded markup. Changes to patterns, templates or block attributes must not break content already stored in production (block validation errors in the editor are a **Major** finding).
8. **Accessibility and performance** — semantic headings and landmarks, labels for form fields, visible focus, colour contrast from `theme.json` tokens, `alt` text, no layout-shifting or render-blocking assets added without reason.

## Repo-specific checks

- Coding standards: PHP follows WordPress Coding Standards (`wordpress/qa/phpcs*.xml.dist`) and PHPStan (`wordpress/qa/phpstan.neon.dist`); JS/CSS follow the asset lint in `wordpress/tests/wordpress-assets-quality.sh`.
- Every user-facing string goes through the theme's or plugin's own text domain; Polish copy is correct and consistent with existing pages.
- Version bumps: a changed theme or plugin bumps its version and the package references in `.github/workflows/wordpress-ci.yml` and the release manifests stay consistent.
- Tests: behaviour changes come with the narrowest matching contract or runtime test under `wordpress/tests/`; release tooling changes come with unit tests in `wordpress/tests/release/`.
- Do not reintroduce the retired React/Symfony stack (only the tag `legacy-react-symfony-final` holds it).
- Work tracking: the PR title or branch carries the Jira key (`GSWEB-<n>`) and Conventional Commit prefix (`feat(GSWEB-32): ...`).
- Docs: changes to deployment, rollback or editor workflows update the matching page under `docs/` in the same PR.
- `.claude/skills/**` and `skills-lock.json` are vendored Open Mercato skills; they change only through `npx skills update -p`, never by hand edits.

## Severity guidance

- **Blocker** — unsafe or broken in production: a security hole, data loss, a fatal error path, a relaxed release or review gate, a leaked secret, a broken build or failing required check.
- **Major** — likely user-visible breakage or a policy violation: unpinned dependency, missing escaping on trusted-but-editable data, block validation breakage, privacy policy drift, missing tests for changed behaviour.
- **Minor** — wording, structure or consistency drift that does not change behaviour.
- **Nit** — optional polish.

Verdict rule (from `om-code-review`): any Blocker, or any Major without a documented waiver in the PR description, means **request changes** and the PR is not merged. Only Minor and Nit findings mean **approve**, which triggers the automatic merge and production deployment.
