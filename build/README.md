# Build & Deployment Configuration

Ten katalog zawiera wszystkie pliki związane z Dockerem, deploymentem i CI/CD.

## Struktura Plików

```
build/
├── Dockerfile              # Konfiguracja budowania obrazu Docker
├── docker-compose.yml      # Orkiestracja kontenerów
├── nginx.conf             # Konfiguracja serwera Nginx
├── deploy.sh              # Skrypt automatycznego deploymentu
├── DEPLOYMENT.md          # Szczegółowy przewodnik wdrożenia
├── CI-CD-SETUP.md         # Konfiguracja automatycznych deploymentów
└── README.md              # Ten plik
```

## Szybki Start - Lokalnie

### Uruchomienie lokalne (development)

Z katalogu głównego projektu:

```bash
# Build i start
docker-compose -f build/docker-compose.yml up -d

# Logi
docker-compose -f build/docker-compose.yml logs -f

# Stop
docker-compose -f build/docker-compose.yml down
```

### Build bez Dockera

```bash
npm install
npm run dev    # Development
npm run build  # Production
```

## Deployment na Serwer

### Metoda 1: Automatyczny (CI/CD)

1. **GitHub Actions** (rekomendowane)
   - Skonfiguruj według `CI-CD-SETUP.md`
   - Push do brancha `main` automatycznie deployuje

2. **GitLab CI/CD** (alternatywa)
   - Użyj pliku `.gitlab-ci.yml` w głównym katalogu
   - Skonfiguruj zmienne w GitLab

### Metoda 2: Ręczny Deployment

Na serwerze:

```bash
cd /var/www/gama-software
./build/deploy.sh
```

Lub z poziomu głównego katalogu:

```bash
bash build/deploy.sh
```

## Dokumentacja

- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Kompletny przewodnik wdrożenia od zera
  - Instalacja Dockera na Ubuntu
  - Konfiguracja DNS i SSL
  - Pierwsze uruchomienie
  - Zarządzanie i monitoring

- **[CI-CD-SETUP.md](./CI-CD-SETUP.md)** - Konfiguracja automatycznych deploymentów
  - GitHub Actions (rekomendowane)
  - GitLab CI/CD
  - Bitbucket Pipelines
  - Rozwiązywanie problemów

## Ważne Uwagi

### Context Budowania Docker

Dockerfile znajduje się w `build/`, ale context budowania to katalog główny projektu:

```yaml
build:
  context: ..              # Katalog główny projektu
  dockerfile: build/Dockerfile
```

To pozwala na dostęp do całego projektu (package.json, src/, etc.) podczas budowania obrazu.

### Nginx Configuration

Nginx jest skonfigurowany z:
- ✅ Automatyczne przekierowanie HTTP → HTTPS
- ✅ SSL/TLS (Let's Encrypt)
- ✅ Gzip compression
- ✅ Cache headers dla statycznych assetów
- ✅ Security headers (XSS, CSRF, etc.)

### Certbot (SSL)

Automatyczne odnowienie certyfikatu SSL co 12h przez kontener certbot.

## Komendy Pomocnicze

### Docker

```bash
# Rebuild bez cache
docker-compose -f build/docker-compose.yml build --no-cache

# Restart konkretnego serwisu
docker-compose -f build/docker-compose.yml restart web

# Sprawdzenie statusu
docker-compose -f build/docker-compose.yml ps

# Czyszczenie
docker system prune -a
```

### Logi

```bash
# Wszystkie logi
docker-compose -f build/docker-compose.yml logs -f

# Tylko web
docker-compose -f build/docker-compose.yml logs -f web

# Tylko certbot
docker-compose -f build/docker-compose.yml logs -f certbot
```

### Debugging

```bash
# Wejście do kontenera
docker-compose -f build/docker-compose.yml exec web sh

# Sprawdzenie konfiguracji nginx
docker-compose -f build/docker-compose.yml exec web nginx -t

# Reload nginx bez restartu
docker-compose -f build/docker-compose.yml exec web nginx -s reload
```

## Środowiska

### Production
- Branch: `main`
- URL: https://gama-software.com
- Auto-deploy: ✅ (przez CI/CD)

### Staging (opcjonalnie)
- Branch: `develop`
- URL: https://staging.gama-software.com
- Auto-deploy: ✅ (przez CI/CD)

## Troubleshooting

### Problem: Strona nie działa po deploymencie

```bash
# Sprawdź logi
docker-compose -f build/docker-compose.yml logs web

# Sprawdź status
docker-compose -f build/docker-compose.yml ps

# Restart
docker-compose -f build/docker-compose.yml restart
```

### Problem: SSL nie działa

Sprawdź czy certyfikat istnieje:

```bash
ls -la /etc/letsencrypt/live/gama-software.com/
```

Jeśli nie, zobacz `DEPLOYMENT.md` sekcja "Konfiguracja SSL".

### Problem: Port zajęty

```bash
# Sprawdź co używa portów 80/443
sudo netstat -tlnp | grep -E ':80|:443'

# Zatrzymaj konfliktujący proces
docker ps
docker stop <container_id>
```

## Bezpieczeństwo

- 🔒 Nigdy nie commituj kluczy SSH, tokenów, haseł
- 🔒 Używaj GitHub/GitLab Secrets dla wrażliwych danych
- 🔒 Regularnie aktualizuj obrazy Docker
- 🔒 Monitoruj logi pod kątem podejrzanej aktywności

## Wsparcie

Pełna dokumentacja znajduje się w:
- `DEPLOYMENT.md` - deployment i infrastruktura
- `CI-CD-SETUP.md` - automatyzacja
