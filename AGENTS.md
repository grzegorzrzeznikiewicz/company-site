# Repository Guidelines

## Project Structure & Module Organization

The site is WordPress only. The block theme is `wordpress/theme/gama-software`
(templates, parts, patterns, `theme.json`); first-party plugins live in
`wordpress/plugins/<slug>`, one durable capability each. Package, runtime and
release tooling is under `wordpress/bin`, `wordpress/release`,
`wordpress/routing`, `wordpress/runtime` and `wordpress/deploy`; tests and QA
toolchains are in `wordpress/tests/` and `wordpress/qa/`. Migration records,
editor guides and the extension guide are in `docs/`.

The former React/Symfony stack was retired in GSWEB-30. Its source is only in
the Git tag `legacy-react-symfony-final`; do not reintroduce it.

## Build, Test, and Development Commands

Start the isolated WordPress environment with `wordpress/bin/start`
(`http://localhost:8090`, Mailpit on `8027`). Package the theme with
`wordpress/bin/package theme gama-software`, validate it with
`wordpress/tests/theme-contract.sh`, and run the ZIP-only lifecycle with
`wordpress/bin/test-package wordpress/dist/gama-software-<version>.zip`.
Plugins follow the same pattern (`wordpress/bin/package plugin <slug>`).
Release tooling tests run with `wordpress/tests/production-workflow-boundary-contract.sh`.
Do not distribute ignored files from `wordpress/dist` without owner approval.

## Coding Style & Naming Conventions

PHP follows the WordPress Coding Standards enforced by
`wordpress/qa/phpcs*.xml.dist` and PHPStan (`wordpress/qa/phpstan.neon.dist`).
Use the theme's and plugins' own text domains for every user-facing string.
Prefer native blocks, patterns and `theme.json` over custom JavaScript.

## Testing Guidelines

Run the narrowest relevant test first, then the matching project gate. Browser
and package tests must use pinned, reproducible inputs and must not alter
unrelated Docker projects. `wordpress/bin/reset` is destructive and requires
its explicit `--confirm` argument; inspect targets first with `--list-targets`.

## Work Tracking, Commits and Releases

All work goes through Jira project GSWEB (gamasoftware.atlassian.net): create
or update the ticket before starting, keep status and progress comments
current. Jira is the source of requirements and status; Git is the technical
history. Use Conventional Commits with the ticket key, for example
`feat(GSWEB-32): ...` or `fix(GSWEB-30): ...`.

Apply and verify every change locally first (local WordPress on port 8090),
then release it to production through the WordPress pipeline. After the four WordPress quality gates on `main`, the production workflow
releases automatically only while the repository variable
`GAMA_DEPLOYMENT_MODE` is `wordpress`; with `off` the guard skips deployment.
Promotion also refuses a merged PR unless, before the merge, the owner account
submitted a COMMENTED review on the exact PR head SHA whose body starts with
`GAMA-SOLO-AI-REVIEW-V1` followed by the JSON report
(`{"head_sha","result","report"}`). It cannot be added after the merge; see
[GSWEB-29 production pipeline](docs/agent-workflows/wordpress-migration/GSWEB-29-production-pipeline.md).
The `AI Code Review` and `AI Review Gate` workflows record that report
automatically from the Open Mercato `om-code-review` verdict and, only on
Approve, merge that exact head once the quality gates pass (PRs touching the
review machinery stay manual); see [AI code review](docs/agent-workflows/ai-code-review.md) and
`CODE_REVIEW.md` for the review rules.
Server-side changes outside the pipeline need explicit owner approval.

## Chrome and Jira Profile Order

For any Jira work, use Google Chrome profiles in this exact preference order:
first `Grzegorz (gama-software.com)` (the Gama Software profile), then
`Grzegorz` only if needed. Never use `Grzegorz (satisfly.co)` or any
`satisfly` profile for this repository or its Jira work.
