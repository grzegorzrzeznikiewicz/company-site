# Gama Software Website

[![CI Quality Checks](https://github.com/grzegorzrzeznikiewicz/company-site/actions/workflows/ci.yml/badge.svg)](https://github.com/grzegorzrzeznikiewicz/company-site/actions/workflows/ci.yml)
[![Deploy to Production](https://github.com/grzegorzrzeznikiewicz/company-site/actions/workflows/deploy.yml/badge.svg)](https://github.com/grzegorzrzeznikiewicz/company-site/actions/workflows/deploy.yml)

Company website for Gama Software.

Figma source:
[Firmowa Wizytówka Strony](https://www.figma.com/design/cxRnksVttQoJbK9Q3R2Bk2/Firmowa-Wizyt%C3%B3wka-Strony)

Release history:
[CHANGELOG.md](/Users/grzegorzrzeznikiewicz/Programowanie/PHP/Projekty/GamaSoftware/web/CHANGELOG.md)

## Requirements

- Docker
- Docker Compose
- Optional: `nvm` or `Volta` if you want the same local Node version as CI (`24.14.0`)

Local system `php` and `node` are not required for development.

## Local Development

### Start the full stack

```bash
cp .env.example .env
cp backend/.env.local.example backend/.env.local

bin/start
```

`bin/start` and `bin/restart` safely remove orphaned containers that belong to this Docker Compose project, including legacy service names from older local stack revisions.

### Endpoints

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8080/api/contact`
- Admin panel: `http://localhost:8080/admin`
- MailHog: `http://localhost:8026`

## Environment Commands

```bash
bin/start
bin/stop
bin/restart
bin/backend-start
bin/backend-stop
bin/frontend-start
bin/frontend-stop
bin/logs-frontend
bin/logs-backend
bin/backend-check
bin/frontend-check
bin/e2e-check
```

## Local WordPress

The WordPress runtime is separate from the existing React/Symfony Compose
project. It uses only the fixed `gama-wordpress` Compose project name, a MariaDB
volume, an uploads volume, and localhost-only WordPress/Mailpit ports.

```bash
cp wordpress/.env.example wordpress/.env
wordpress/bin/start
```

- Site: `http://localhost:8090`
- WordPress admin: `http://localhost:8090/wp-admin/`
- Test email inbox: `http://localhost:8027`
- SMTP sink: `127.0.0.1:1027` (Mailpit only; never a real recipient)

The example local administrator is `admin / ChangeMe-WordPress-Only`. Change
these values in your untracked `wordpress/.env` when needed.

```bash
wordpress/bin/start       # start and idempotently bootstrap WordPress
wordpress/bin/stop        # stop only gama-wordpress containers
wordpress/bin/restart     # recreate containers without deleting data
wordpress/bin/logs        # follow WordPress-project logs
wordpress/bin/wp core version
wordpress/bin/test-mail   # prove outbound local mail reaches Mailpit
wordpress/tests/mount-contract.sh        # validate safe theme/plugin bind mounts
wordpress/tests/runtime-smoke.sh           # non-destructive runtime smoke check
wordpress/tests/runtime-smoke.sh --clean   # explicit clean-volume bootstrap check
wordpress/bin/reset --list-targets         # inspect targets before a reset
wordpress/bin/validate-extensions-lock     # validate the empty external-extension inventory
wordpress/bin/package plugin gama-contact  # build the local reproducible plugin ZIP
wordpress/tests/plugin-package-contract.sh # verify contents and two byte-identical builds
wordpress/tests/package-compose-contract.sh # verify isolated image/mount parity
wordpress/tests/test-package-input-contract.sh # reject non-canonical ZIP inputs before Docker
wordpress/tests/test-package-isolation-contract.sh # verify exact-label preflight and cleanup semantics
wordpress/bin/test-package wordpress/dist/gama-contact-0.1.0.zip # clean ZIP-only lifecycle
```

`wordpress/bin/reset` refuses to run without `--confirm`; with that explicit
flag it removes only the `gama-wordpress` Compose project's local database,
uploads, and WordPress volumes. It never targets the React/Symfony project.

The WordPress package architecture, code/runtime classification, lifecycle,
dependency-lock policy, and exact next-plugin procedure are recorded in
[`GSWEB-11-architecture.md`](docs/agent-workflows/wordpress-migration/GSWEB-11-architecture.md).
The current `gama-software` theme is only the GSWEB-10 runtime scaffold;
GSWEB-12 owns its production implementation and packaging. Files in
`wordpress/dist` are ignored local artifacts and must not be uploaded,
released, or otherwise distributed without separate approval.

## Frontend

The `frontend` service runs the Vite development server inside Docker.

Requests to `/api/*` are proxied to the `backend` service. `VITE_API_BASE_URL` can stay empty in Docker-based development.

### Frontend environment variables

- `FRONTEND_NODE_VERSION`: Node version used by Docker and GitHub Actions (`24.14.0`)
- `VITE_DEV_PORT`: frontend port exposed on the host (`5173`)
- `VITE_API_BASE_URL`: optional explicit API URL
- `VITE_API_PROXY_TARGET`: proxy target used outside Docker; the container overrides it to `http://backend:8080`

### Frontend quality checks

```bash
bin/frontend-check
```

### Frontend end-to-end checks

```bash
bin/e2e-check
```

## Backend

The backend lives in [backend/](/Users/grzegorzrzeznikiewicz/Programowanie/PHP/Projekty/GamaSoftware/web/backend) and is a Symfony 8 application serving:

- the contact form API at `/api/contact`
- the admin panel at `/admin`

The stack includes:

- `backend`: Symfony runtime container
- `backend-tools`: one-off backend tooling container
- `symfony-db`: PostgreSQL exposed on host port `5433`
- `mailhog`: local SMTP sink and UI

### Backend environment variables

Copy [backend/.env.local.example](/Users/grzegorzrzeznikiewicz/Programowanie/PHP/Projekty/GamaSoftware/web/backend/.env.local.example) to `backend/.env.local` and configure:

- `DATABASE_URL`
- `MAILER_DSN`
- `CONTACT_RECIPIENT`
- `CONTACT_SENDER`
- `CORS_ALLOW_ORIGIN`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD_HASH`
- `ADMIN_PANEL_TITLE`

In local development, `MAILER_DSN="smtp://mailhog:1025"` sends email to MailHog.
The example local admin credentials are `admin / Admin123!`.

### Useful backend commands

Generate an admin password hash:

```bash
HOST_UID=$(id -u) HOST_GID=$(id -g) docker compose -f docker-compose.symfony.yml exec backend php -r "echo password_hash('YourPassword', PASSWORD_BCRYPT), PHP_EOL;"
```

Run Doctrine migrations:

```bash
HOST_UID=$(id -u) HOST_GID=$(id -g) docker compose -f docker-compose.symfony.yml exec backend php bin/console doctrine:migrations:migrate
```

Run backend quality checks and tests:

```bash
bin/backend-check
```

## Local `company.test` Domain

1. Add host entries:

   ```bash
   echo "127.0.0.1 company.test api.company.test" | sudo tee -a /etc/hosts
   ```

2. Ensure `.env` contains:

   ```dotenv
   VITE_API_BASE_URL=
   VITE_DEV_HOST=0.0.0.0
   VITE_DEV_PORT=5173
   ```

3. Start the stack:

   ```bash
   bin/start
   ```

4. Access:
   - frontend: `http://company.test:5173`
   - backend/admin: `http://api.company.test:8080`

## Deployment

Deployment-related files are in [build/](/Users/grzegorzrzeznikiewicz/Programowanie/PHP/Projekty/GamaSoftware/web/build):

- [DEPLOYMENT.md](/Users/grzegorzrzeznikiewicz/Programowanie/PHP/Projekty/GamaSoftware/web/build/DEPLOYMENT.md)
- [CI-CD-SETUP.md](/Users/grzegorzrzeznikiewicz/Programowanie/PHP/Projekty/GamaSoftware/web/build/CI-CD-SETUP.md)
- [README.md](/Users/grzegorzrzeznikiewicz/Programowanie/PHP/Projekty/GamaSoftware/web/build/README.md)

### GitHub Actions

- [ci.yml](/Users/grzegorzrzeznikiewicz/Programowanie/PHP/Projekty/GamaSoftware/web/.github/workflows/ci.yml)
- [deploy.yml](/Users/grzegorzrzeznikiewicz/Programowanie/PHP/Projekty/GamaSoftware/web/.github/workflows/deploy.yml)
- [rollback.yml](/Users/grzegorzrzeznikiewicz/Programowanie/PHP/Projekty/GamaSoftware/web/.github/workflows/rollback.yml)

### Required GitHub Secrets

- `SERVER_HOST`
- `SERVER_USER`
- `SSH_PRIVATE_KEY`
- `SSH_PORT`
- `GHCR_USERNAME`
- `GHCR_TOKEN`
- `PROD_MAILER_DSN`
- `PROD_CONTACT_RECIPIENT`
- `PROD_CONTACT_SENDER`
- `PROD_COMPANY_API_APP_SECRET`
- `PROD_COMPANY_DB_PASSWORD`
- `PROD_ADMIN_PASSWORD_HASH`

## Project Structure

```text
.
├── src/                  # React application source
├── tests/e2e/            # Playwright end-to-end tests
├── backend/              # Symfony 8 API and admin panel
├── bin/                  # Local environment command wrappers
├── docker/               # Local Docker helper scripts
├── build/                # Build and deployment files
├── .github/workflows/    # GitHub Actions workflows
├── .nvmrc                # Project Node version
└── package.json
```

## Tech Stack

- React 18
- TypeScript
- Vite 6
- Tailwind CSS 4
- shadcn/ui
- Material UI
- Motion
- Symfony 8
- PostgreSQL 16
- Docker

## License

Copyright © 2026 Gama Software. All rights reserved.
