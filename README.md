# Gama Software - Firmowa Strona

[![CI Quality Checks](https://github.com/grzegorzrzeznikiewicz/company-site/actions/workflows/ci.yml/badge.svg)](https://github.com/grzegorzrzeznikiewicz/company-site/actions/workflows/ci.yml)
[![Deploy to Production](https://github.com/grzegorzrzeznikiewicz/company-site/actions/workflows/deploy.yml/badge.svg)](https://github.com/grzegorzrzeznikiewicz/company-site/actions/workflows/deploy.yml)

Strona wizytówka dla Gama Software - specjalizujemy się w wdrożeniach e-commerce, konsultacjach oraz budowaniu agentów AI.

Oryginalny projekt Figma: https://www.figma.com/design/cxRnksVttQoJbK9Q3R2Bk2/Firmowa-Wizyt%C3%B3wka-Strony

## Development

### Wymagania

- Docker + Docker Compose
- opcjonalnie `nvm` lub `Volta`, jeśli chcesz lokalnie używać tej samej wersji Node co CI (`24.14.0`)

Lokalny systemowy `php` i `node` nie są wymagane do developmentu. Frontend i backend uruchamiają się w całości w Dockerze.

### Uruchomienie całego stacku

```bash
cp .env.example .env
cp backend/.env.local.example backend/.env.local

HOST_UID=$(id -u) HOST_GID=$(id -g) docker compose -f docker-compose.symfony.yml up -d
```

Jeśli aktualizujesz starszy lokalny stack ze starymi nazwami usług (`symfony`, `symfony-composer`, `frontend-npm`), uruchom jednorazowo:

```bash
HOST_UID=$(id -u) HOST_GID=$(id -g) docker compose -f docker-compose.symfony.yml up -d --remove-orphans
```

Po starcie dostępne są:

- frontend: `http://localhost:5173`
- backend API: `http://localhost:8080/api/contact`
- panel administracyjny: `http://localhost:8080/admin`
- MailHog: `http://localhost:8026`

### Frontend (Docker)

Serwis `frontend` uruchamia Vite dev server w Dockerze. Domyślnie frontend korzysta z proxy Vite, więc wywołania `/api/*` są przekazywane do backendu `backend` bez potrzeby ustawiania `VITE_API_BASE_URL`.

Najważniejsze zmienne z `.env`:

- `FRONTEND_NODE_VERSION` – wspólna wersja Node dla Dockera i GitHub Actions (`24.14.0`)
- `VITE_DEV_PORT` – port frontendu na hoście (`5173`)
- `VITE_API_BASE_URL` – opcjonalny jawny adres API; zostaw pusty, aby używać proxy Vite
- `VITE_API_PROXY_TARGET` – target proxy dla środowiska uruchamianego poza Dockerem; kontener `frontend` nadpisuje go na `http://backend:8080`

#### Frontend quality gates w modelu Plan B

Jednorazowe komendy frontendowe uruchamiaj przez serwis `frontend-tools`:

```bash
HOST_UID=$(id -u) HOST_GID=$(id -g) docker compose -f docker-compose.symfony.yml --profile tools run --rm frontend-tools npm run format:check
HOST_UID=$(id -u) HOST_GID=$(id -g) docker compose -f docker-compose.symfony.yml --profile tools run --rm frontend-tools npm run lint
HOST_UID=$(id -u) HOST_GID=$(id -g) docker compose -f docker-compose.symfony.yml --profile tools run --rm frontend-tools npm run typecheck
HOST_UID=$(id -u) HOST_GID=$(id -g) docker compose -f docker-compose.symfony.yml --profile tools run --rm frontend-tools npm run test:ci
HOST_UID=$(id -u) HOST_GID=$(id -g) docker compose -f docker-compose.symfony.yml --profile tools run --rm frontend-tools npm run build
```

### Backend (Symfony 8 API + Admin)

Backend znajduje się w katalogu `backend/` i jest uruchamiany w kontenerach, aby nie kolidować z istniejącym środowiskiem Warden. Ta sama aplikacja Symfony obsługuje:

- API formularza (`/api/contact`)
- panel administracyjny (EasyAdmin 4 + Twig + Doctrine) pod `/admin`, przygotowany pod CMS/blog/leady

W kontenerze działa Postgres (`symfony-db`) – domyślnie nasłuchuje na porcie hosta `5433` i trzyma dane w wolumenie `symfony-db-data`. Konfigurację połączenia zmienisz zmiennymi `SYMFONY_DB_*` lub bezpośrednio w `backend/.env.local`.
Obok wystartuje MailHog (`mailhog`) – interfejs webowy pod `http://localhost:${SYMFONY_MAILHOG_HTTP_PORT:-8026}`.

Kluczowe zmienne środowiskowe backendu (patrz `backend/.env.local.example`, skopiuj do `backend/.env.local`):

- `DATABASE_URL` – połączenie z bazą danych (domyślnie Postgres w kontenerze).
- `MAILER_DSN` – połączenie SMTP (np. `smtp://login:haslo@smtp.server:587`).
- (`dev`) Po default `MAILER_DSN"smtp://mailhog:1025"` kieruje wysyłkę do lokalnego MailHoga.
- `CONTACT_RECIPIENT` – adres odbiorcy formularza kontaktowego.
- `CONTACT_SENDER` – wymagany, stały i zweryfikowany adres nadawcy zgodny z polityką SMTP/SPF/DMARC.
- `CORS_ALLOW_ORIGIN` – regex akceptowanych originów (localhost + `company.test`).
- `ADMIN_USERNAME` / `ADMIN_PASSWORD_HASH` – dane HTTP Basic chroniące `/admin` (zmień hasło i hash!).
- `ADMIN_PANEL_TITLE` – podpis widoczny w nagłówku panelu.

Hash hasła admina wygenerujesz przez:

```bash
HOST_UID=$(id -u) HOST_GID=$(id -g) docker compose -f docker-compose.symfony.yml exec backend php -r "echo password_hash('TwojeHaslo', PASSWORD_BCRYPT), PHP_EOL;"
```

Wynik umieść w `backend/.env.local` jako `ADMIN_PASSWORD_HASH`.
MailHog przechwytuje wszystkie wiadomości – podgląd pod `http://localhost:8026` (lub port ustawiony w `SYMFONY_MAILHOG_HTTP_PORT`).

#### EasyAdmin – szybki start

- Dashboard i menu znajdują się w `backend/src/Controller/Admin/DashboardController.php` i `backend/templates/admin/`.
- Aby dodać nowe sekcje CRUD, skorzystaj z generatora `php bin/console make:entity` + `php bin/console make:crud`, a następnie zarejestruj kontrolery w menu (`configureMenuItems`).
- Motyw i wygląd możesz dostosować nadpisując szablony EasyAdmin lub obecny `admin/layout.html.twig` (custom hero + roadmapa).

Doctrine/ORM jest gotowe na kolejne encje (`backend/src/Entity`). Po utworzeniu modeli uruchom migracje:

```bash
HOST_UID=$(id -u) HOST_GID=$(id -g) docker compose -f docker-compose.symfony.yml exec backend php bin/console doctrine:migrations:migrate
```

### Backend quality gates

```bash
# Uruchomienie quality gates i testów
HOST_UID=$(id -u) HOST_GID=$(id -g) docker compose -f docker-compose.symfony.yml run --rm backend-tools qa
```

### Lokalna domena `company.test`

1. Dodaj wpisy do `/etc/hosts` (wymaga `sudo`):
   ```bash
   echo "127.0.0.1 company.test api.company.test" | sudo tee -a /etc/hosts
   ```
2. Skopiuj `.env.example` → `.env` i ustaw:
   ```dotenv
   VITE_API_BASE_URL=
   VITE_DEV_HOST=0.0.0.0
   VITE_DEV_PORT=5173
   ```
3. Uruchom stack Dockera:
   ```bash
   HOST_UID=$(id -u) HOST_GID=$(id -g) docker compose -f docker-compose.symfony.yml up -d
   ```
4. Frontend będzie dostępny pod `http://company.test:5173`, a backend i panel admina pod `http://api.company.test:8080`.

## Docker

### Szybkie komendy (używając helpera)

```bash
# Uruchomienie
./docker.sh up

# Logi
./docker.sh logs

# Stop
./docker.sh down

# Wszystkie komendy
./docker.sh
```

### Standardowe komendy Docker Compose

```bash
# Start
docker-compose -f build/docker-compose.yml up -d

# Stop
docker-compose -f build/docker-compose.yml down

# Logi
docker-compose -f build/docker-compose.yml logs -f
```

## Deployment

Wszystkie pliki związane z deploymentem znajdują się w katalogu `build/`:

- **[build/DEPLOYMENT.md](build/DEPLOYMENT.md)** - Kompletny przewodnik wdrożenia na serwer
- **[build/CI-CD-SETUP.md](build/CI-CD-SETUP.md)** - Konfiguracja automatycznych deploymentów
- **[build/README.md](build/README.md)** - Dokumentacja plików build

### Automatyczny deployment (CI/CD)

Projekt używa GitHub Actions do quality gates i deploymentu:

- `.github/workflows/ci.yml` uruchamia frontendowy format/lint/typecheck/test/build oraz backendowe linty i testy przy każdym `push` i `pull_request`, używając Node `24.14.0`.
- `.github/workflows/deploy.yml` odpowiada za automatyczny deployment po pushu do `main`.

Push do brancha `main` automatycznie deployuje na produkcję.

W trybie produkcyjnym VM2 nie buduje już aplikacji z lokalnego repo. Workflow buduje obraz Docker, publikuje go do GHCR i VM2 wykonuje tylko `pull + up` po tagu commita.
To samo dotyczy backendu Symfony API (`company-site-backend`) - jest publikowany jako osobny obraz i wdrażany na VM2 jako usługa `company-api`.

### Rollback (1 klik)

Dostępny jest ręczny workflow `.github/workflows/rollback.yml`.
Uruchamiasz go z `Actions -> Rollback Production -> Run workflow` i podajesz `image_tag` (np. `sha-...`).
Workflow cofa jednocześnie frontend i backend do wskazanego taga obrazu.

Wymagane sekrety GitHub Actions:

- `SERVER_HOST`
- `SERVER_USER`
- `SSH_PRIVATE_KEY`
- `SSH_PORT`
- `GHCR_USERNAME` (opcjonalnie; wymagane tylko gdy obraz GHCR jest prywatny)
- `GHCR_TOKEN` (opcjonalnie; wymagane tylko gdy obraz GHCR jest prywatny)
- `PROD_MAILER_DSN`
- `PROD_CONTACT_RECIPIENT`
- `PROD_CONTACT_SENDER`
- `PROD_COMPANY_API_APP_SECRET`
- `PROD_COMPANY_DB_PASSWORD`
- `PROD_ADMIN_PASSWORD_HASH`

Nawet dla publicznych obrazów warto ustawić `GHCR_USERNAME`/`GHCR_TOKEN`, bo pull na serwerze bywa wtedy szybszy i bardziej stabilny (mniej ryzyka limitów anonimowych).

### SMTP i sekrety backendu na VM2

Sekrety backendu Symfony (w tym `MAILER_DSN`) są wstrzykiwane z GitHub Secrets podczas deploy/rollback i nadpisują wartości z `vm2/.env`.
Najważniejsze zmienne:

- `MAILER_DSN`
- `CONTACT_RECIPIENT`
- `CONTACT_SENDER`
- `COMPANY_API_APP_SECRET`
- `COMPANY_DB_PASSWORD`
- `ADMIN_PASSWORD_HASH`

## Struktura Projektu

```
.
├── src/                    # Kod źródłowy aplikacji
│   ├── app/               # Komponenty React
│   ├── assets/            # Obrazy i statyczne pliki
│   └── styles/            # Style CSS
├── build/                 # Konfiguracja Docker i deployment
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── nginx.conf
│   ├── deploy.sh
│   ├── DEPLOYMENT.md
│   └── CI-CD-SETUP.md
├── docker/                # Skrypty pomocnicze dla lokalnego środowiska Docker
├── backend/               # Symfony 8 (API + panel administracyjny)
├── .github/workflows/     # GitHub Actions CI/CD
├── docker.sh              # Helper script dla Docker
├── .nvmrc                 # Wspólna wersja Node dla dev/CI
└── package.json
```

## Technologie

- React 18.3
- TypeScript
- Vite 6
- Tailwind CSS 4
- shadcn/ui
- Material-UI
- Motion (Framer Motion)
- Node 24.14.0
- Docker + Nginx

## Licencja

© 2026 Gama Software. Wszystkie prawa zastrzeżone.
