
# Gama Software - Firmowa Strona

Strona wizytówka dla Gama Software - specjalizujemy się w wdrożeniach e-commerce, konsultacjach oraz budowaniu agentów AI.

Oryginalny projekt Figma: https://www.figma.com/design/cxRnksVttQoJbK9Q3R2Bk2/Firmowa-Wizyt%C3%B3wka-Strony

## Development

### Wymagania

- Node.js 20+
- npm

### Uruchomienie lokalne

```bash
# Instalacja zależności
npm install

# Uruchomienie serwera deweloperskiego
npm run dev

# Build produkcyjny
npm run build
```

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
  