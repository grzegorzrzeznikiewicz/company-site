
# Gama Software - Firmowa Strona

Strona wizytówka dla Gama Software - specjalizujemy się w wdrożeniach e-commerce, konsultacjach oraz budowaniu agentów AI.

Oryginalny projekt Figma: https://www.figma.com/design/cxRnksVttQoJbK9Q3R2Bk2/Firmowa-Wizyt%C3%B3wka-Strony

## Development

### Wymagania

- Node.js 20+
- npm
- Docker + Docker Compose (Symfony API)

### Uruchomienie lokalne (frontend)

```bash
# Instalacja zależności
npm install

# Uruchomienie serwera deweloperskiego
npm run dev

# Build produkcyjny
npm run build
```

Ustaw adres API w pliku `.env` (skopiuj z `.env.example`). Domyślnie `VITE_API_BASE_URL` wskazuje na `http://localhost:8080`.

### Backend (Symfony 8 API + Admin)

Backend znajduje się w katalogu `backend/` i jest uruchamiany w kontenerach, aby nie kolidować z istniejącym środowiskiem Warden. Ta sama aplikacja Symfony obsługuje:

- API formularza (`/api/contact`).
- Panel administracyjny (EasyAdmin 4 + Twig + Doctrine) pod `/admin`, przygotowany pod CMS/blog/leady.

```bash
# (jednorazowo) instalacja zależności backendu
HOST_UID=$(id -u) HOST_GID=$(id -g) docker compose -f docker-compose.symfony.yml run --rm symfony-composer install

# start API + Postgres + MailHog
HOST_UID=$(id -u) HOST_GID=$(id -g) docker compose -f docker-compose.symfony.yml up symfony symfony-db mailhog
```

W kontenerze działa Postgres (`symfony-db`) – domyślnie nasłuchuje na porcie hosta `5433` i trzyma dane w wolumenie `symfony-db-data`. Konfigurację połączenia zmienisz zmiennymi `SYMFONY_DB_*` lub bezpośrednio w `backend/.env.local`.
Obok wystartuje MailHog (`mailhog`) – interfejs webowy pod `http://localhost:${SYMFONY_MAILHOG_HTTP_PORT:-8026}`.

Kluczowe zmienne środowiskowe backendu (patrz `backend/.env.local.example`, skopiuj do `backend/.env.local`):

- `DATABASE_URL` – połączenie z bazą danych (domyślnie Postgres w kontenerze).
- `MAILER_DSN` – połączenie SMTP (np. `smtp://login:haslo@smtp.server:587`).
- (`dev`) Po default `MAILER_DSN"smtp://mailhog:1025"` kieruje wysyłkę do lokalnego MailHoga.
- `CONTACT_RECIPIENT` / `CONTACT_SENDER` – adresy formularza kontaktowego.
- `CORS_ALLOW_ORIGIN` – regex akceptowanych originów (localhost + `company.test`).
- `ADMIN_USERNAME` / `ADMIN_PASSWORD_HASH` – dane HTTP Basic chroniące `/admin` (zmień hasło i hash!).
- `ADMIN_PANEL_TITLE` – podpis widoczny w nagłówku panelu.

Panel administracyjny (http://api.company.test:8080/admin) domyślnie zabezpieczony jest HTTP Basic (`admin` / `admin123`). Hash wygenerujesz przez `php -r "echo password_hash('TwojeHaslo', PASSWORD_BCRYPT);"` i umieścisz w `.env.local`.
MailHog przechwytuje wszystkie wiadomości – podgląd pod `http://localhost:8026` (lub port ustawiony w `SYMFONY_MAILHOG_HTTP_PORT`).

#### EasyAdmin – szybki start

- Dashboard i menu znajdują się w `backend/src/Controller/Admin/DashboardController.php` i `backend/templates/admin/`.
- Aby dodać nowe sekcje CRUD, skorzystaj z generatora `php bin/console make:entity` + `php bin/console make:crud`, a następnie zarejestruj kontrolery w menu (`configureMenuItems`).
- Motyw i wygląd możesz dostosować nadpisując szablony EasyAdmin lub obecny `admin/layout.html.twig` (custom hero + roadmapa).

Doctrine/ORM jest gotowe na kolejne encje (`backend/src/Entity`). Po utworzeniu modeli uruchom migracje:

```bash
HOST_UID=$(id -u) HOST_GID=$(id -g) docker compose -f docker-compose.symfony.yml exec symfony php bin/console doctrine:migrations:migrate
```

### Lokalna domena `company.test`

1. Dodaj wpisy do `/etc/hosts` (wymaga `sudo`):
   ```bash
   echo "127.0.0.1 company.test api.company.test" | sudo tee -a /etc/hosts
   ```
2. Skopiuj `.env.example` → `.env` i ustaw:
   ```dotenv
   VITE_API_BASE_URL=http://api.company.test:8080
   VITE_DEV_HOST=company.test
   VITE_DEV_PORT=5173
   ```
3. Backend uruchom z mapowaniem portu (domyślnie 8080/5433/8026) i ewentualnie zmień `SYMFONY_HTTP_PORT`/`SYMFONY_DB_PORT`/`SYMFONY_MAILHOG_HTTP_PORT` gdy port zajęty:
   ```bash
   HOST_UID=$(id -u) HOST_GID=$(id -g) docker compose -f docker-compose.symfony.yml up symfony symfony-db mailhog
   ```
4. Frontend startuje nadal przez `npm run dev`, ale będzie serwowany pod `http://company.test:5173` i łączył się z API/Adminem pod `http://api.company.test:8080`.

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

Projekt jest skonfigurowany dla automatycznych deploymentów przez:
- **GitHub Actions** (rekomendowane) - `.github/workflows/deploy.yml`
- **GitLab CI/CD** (alternatywa) - `.gitlab-ci.yml`

Push do brancha `main` automatycznie deployuje na produkcję.

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
├── backend/               # Symfony 8 (API + panel administracyjny)
├── .github/workflows/     # GitHub Actions CI/CD
├── docker.sh              # Helper script dla Docker
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
- Docker + Nginx

## Licencja

© 2026 Gama Software. Wszystkie prawa zastrzeżone.
  