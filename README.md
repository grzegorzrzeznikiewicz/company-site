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
