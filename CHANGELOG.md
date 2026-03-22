# Changelog

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
