# Changelog

## 2.0.0 — WordPress only (GSWEB-30)

- Retired the React/Vite frontend, the Symfony 8 contact API and EasyAdmin
  panel, their Docker, `bin/*` and `build/` files, and the legacy GitHub/GitLab
  CI, deploy and rollback workflows. The last full legacy source is the Git tag
  `legacy-react-symfony-final`.
- Production release verification now requires only the four WordPress quality
  gates; the legacy CI workflow is no longer trusted or consulted.
- Removed the one-shot read-only server audit (pinned to a retired branch and
  deployment mode) and the legacy release transaction.
- Rewrote README and AGENTS for the WordPress-only repository and added
  `docs/EXTENDING.md` with the extension rules, start checklist and
  Definition of Done.

The 1.x entries below describe the retired React/Symfony site.

## 1.1.0

- Refactored the React frontend into smaller site components and moved the contact form to `react-hook-form`.
- Added field-level handling for backend validation errors in the contact form.
- Extracted backend mail delivery into a dedicated Symfony service and enforced a fixed sender address.
- Added frontend and backend tests plus local quality commands for both stacks.
- Added Playwright end-to-end coverage for the public site, admin panel, and contact email delivery.
- Dockerized frontend development and aligned the local environment with CI.
- Renamed Docker services to `backend`, `backend-tools`, `frontend`, and `frontend-tools`.
- Aligned local and deployment container names under the `gama-*` prefix.
- Added `bin/*` commands for environment control, service-specific start/stop, logs, quality checks, and E2E execution.
- Updated GitHub Actions to current action versions and removed Node 20 deprecation warnings.
- Simplified the README and switched project documentation to English.

## 1.0.0

- Initial release of the company website project.
- React/Vite frontend with a landing page, services/modules sections, blog placeholder, and contact form.
- Symfony 8 backend with the contact API and an initial admin panel.
- Docker-based production build and deployment setup.
- GitHub Actions workflows for CI, deployment, and rollback.
