# Repository Guidelines

## Project Structure & Module Organization

The React/Vite site lives in `src/`, with page composition in `src/app/`, reusable
site components in `src/app/components/site/`, and UI primitives in
`src/app/components/ui/`. Browser tests live in `tests/e2e/`. The Symfony 8
contact API and EasyAdmin panel are isolated in `backend/`; its PHP tests are in
`backend/tests/`. The in-progress WordPress migration is deliberately separate
under `wordpress/`: the block theme is `wordpress/theme/gama-software`,
first-party plugins are `wordpress/plugins/`, and package/runtime checks are
under `wordpress/tests/` and `wordpress/qa/`. The shared migration process and
ticket ordering are documented in `docs/agent-workflows/wordpress-migration/`.

## Build, Test, and Development Commands

Use Node 24.14.0 (`.nvmrc`) for the frontend. `bin/start` brings up the
React/Symfony development stack; `bin/frontend-check` runs frontend formatting,
linting, type checking, unit tests, and build checks, while `bin/e2e-check`
runs its Playwright suite. For the PHP application, the `backend-tools` Compose
service runs Composer quality commands defined by `backend/composer.json`.

Start the isolated WordPress environment with `wordpress/bin/start`. Package
the theme with `wordpress/bin/package theme gama-software`, validate its static
contract with `wordpress/tests/theme-contract.sh`, and run the ZIP-only
lifecycle with `wordpress/bin/test-package wordpress/dist/gama-software-0.3.0.zip`.
Do not distribute ignored files from `wordpress/dist` without owner approval.

## Coding Style & Naming Conventions

TypeScript is strict and uses the `@/*` alias for `src/*`. ESLint applies its
type-aware recommended rules to TypeScript; format frontend files with Prettier
(single quotes, semicolons, trailing commas). PHP uses four spaces and LF line
endings as set by `backend/.editorconfig`; Symfony quality checks use PHP-CS-
Fixer, PHPStan, PHPMD, and PHPUnit. Keep WordPress changes inside its isolated
area rather than coupling them to the existing React/Symfony stack.

## Testing Guidelines

Run the narrowest relevant test first, then the matching project gate. Browser
and package tests must use pinned, reproducible inputs and must not alter
unrelated Docker projects. `wordpress/bin/reset` is destructive and requires
its explicit `--confirm` argument; inspect targets first with `--list-targets`.

## Commit, Pull Request, and Migration Guidelines

Use the established Conventional Commit style, for example
`feat(GSWEB-14): ...`, `fix(GSWEB-14): ...`, or `docs(GSWEB-11): ...`.
Jira is the source of ticket requirements and status; Git is the technical
history. Production deployment or removal of the legacy stack requires explicit
owner approval after the stated gates and independent review.

## Chrome and Jira Profile Order

For any Jira work, use Google Chrome profiles in this exact preference order:
first `Grzegorz (gama-software.com)` (the Gama Software profile), then
`Grzegorz` only if needed. Never use `Grzegorz (satisfly.co)` or any
`satisfly` profile for this repository or its Jira work.
