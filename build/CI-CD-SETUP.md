# Konfiguracja Automatycznego Deploymentu (CI/CD)

## Porównanie Narzędzi

| Narzędzie | Zalety | Wady | Cena |
|-----------|--------|------|------|
| **GitHub Actions** | ✅ Najpopularniejsze<br>✅ Łatwa konfiguracja<br>✅ Świetna dokumentacja<br>✅ Darmowe 2000 min/mies | ⚠️ Wymaga GitHub | Darmowe (prywatne repo: 2000 min/mies) |
| **GitLab CI/CD** | ✅ Wszystko w jednym<br>✅ Darmowy runner<br>✅ Potężne funkcje | ⚠️ Bardziej skomplikowane | Darmowe (400 min/mies) |
| **Bitbucket Pipelines** | ✅ Integracja z Jira<br>✅ Dobra dla Atlassian | ⚠️ Najmniej popularne<br>⚠️ Słabsza społeczność | Darmowe (50 min/mies) |

**Rekomendacja: GitHub Actions** - najlepszy stosunek prostoty do funkcjonalności.

---

# GitHub Actions - Konfiguracja (REKOMENDOWANE)

## Krok 1: Przygotowanie Serwera

### 1.1 Utwórz użytkownika do deploymentu (opcjonalne, ale zalecane)

```bash
# Na serwerze
sudo adduser deployer
sudo usermod -aG docker deployer
sudo usermod -aG sudo deployer
```

### 1.2 Wygeneruj klucz SSH dla GitHub Actions

```bash
# Na serwerze (jako użytkownik deployer lub inny)
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_deploy

# Dodaj klucz publiczny do authorized_keys
cat ~/.ssh/github_deploy.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# Wyświetl klucz prywatny (skopiuj do schowka)
cat ~/.ssh/github_deploy
```

**WAŻNE:** Skopiuj cały klucz prywatny (włącznie z liniami `-----BEGIN` i `-----END`).

### 1.3 Przygotuj katalog projektu

```bash
# Na serwerze
sudo mkdir -p /var/www/gama-software
sudo chown deployer:deployer /var/www/gama-software
cd /var/www/gama-software

# Sklonuj repozytorium
git clone git@github.com:TWOJ-USERNAME/gama-software.git .

# Skopiuj skrypt deploy
chmod +x deploy.sh
```

## Krok 2: Konfiguracja GitHub Repository

### 2.1 Dodaj Secrets do repozytorium

Przejdź do: **Settings → Secrets and variables → Actions → New repository secret**

Dodaj następujące secrets:

| Nazwa | Wartość | Opis |
|-------|---------|------|
| `SERVER_HOST` | `123.45.67.89` | IP lub domena serwera |
| `SERVER_USER` | `deployer` | Nazwa użytkownika na serwerze |
| `SSH_PRIVATE_KEY` | `-----BEGIN OPENSSH PRIVATE KEY-----...` | Cały klucz prywatny SSH |
| `SSH_PORT` | `22` | Port SSH (domyślnie 22) |

### 2.2 Dodaj pliki do repozytorium

```bash
# Na lokalnym komputerze
git add .github/workflows/deploy.yml
git add deploy.sh
git add Dockerfile docker-compose -f build/docker-compose.yml.yml nginx.conf
git commit -m "Add CI/CD configuration"
git push origin main
```

### 2.3 Włącz GitHub Actions

1. Przejdź do zakładki **Actions** w repozytorium
2. Jeśli Actions są wyłączone, włącz je
3. Sprawdź czy workflow się uruchomił

## Krok 3: Test Deploymentu

### 3.1 Ręczny test

```bash
# Na serwerze
cd /var/www/gama-software
./deploy.sh
```

### 3.2 Test przez GitHub Actions

```bash
# Zrób jakąś zmianę
echo "# Test" >> README.md
git add README.md
git commit -m "Test deployment"
git push origin main
```

Sprawdź w zakładce **Actions** czy deployment się powiódł.

### 3.3 Ręczne uruchomienie workflow

W zakładce **Actions** → wybierz workflow **Deploy to Production** → **Run workflow**

## Krok 4: Monitoring i Logi

### Sprawdzanie logów GitHub Actions

1. Przejdź do **Actions** w repozytorium
2. Kliknij na konkretny workflow run
3. Zobacz szczegóły każdego kroku

### Sprawdzanie logów na serwerze

```bash
# Logi Dockera
cd /var/www/gama-software
docker-compose -f build/docker-compose.yml logs -f

# Logi Nginx
docker-compose -f build/docker-compose.yml logs -f web

# Status kontenerów
docker-compose -f build/docker-compose.yml ps
```

---

# GitLab CI/CD - Alternatywna Konfiguracja

Jeśli wolisz GitLab, używamy pliku `.gitlab-ci.yml` (już stworzony w projekcie).

## Krok 1: Konfiguracja GitLab

### 1.1 Dodaj zmienne w GitLab

Przejdź do: **Settings → CI/CD → Variables**

Dodaj:
- `SERVER_HOST` - IP serwera
- `SERVER_USER` - użytkownik SSH
- `SSH_PRIVATE_KEY` - klucz prywatny SSH (zaznacz: masked, protected)
- `SSH_PORT` - port SSH (22)

### 1.2 Włącz GitLab Runner

GitLab automatycznie zapewnia runnery dla publicznych projektów. Dla prywatnych możesz użyć shared runnerów lub zainstalować własny.

## Krok 2: Test

```bash
git add .gitlab-ci.yml
git commit -m "Add GitLab CI/CD"
git push origin main
```

Sprawdź w **CI/CD → Pipelines** czy deployment działa.

---

# Rozwiązywanie Problemów

## Problem: SSH Connection Failed

**Przyczyna:** Błędny klucz SSH lub brak dostępu.

**Rozwiązanie:**
```bash
# Na serwerze sprawdź czy klucz jest w authorized_keys
cat ~/.ssh/authorized_keys

# Sprawdź uprawnienia
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys

# Testuj połączenie lokalnie
ssh -i ~/.ssh/github_deploy deployer@SERVER_IP
```

## Problem: Permission Denied na Docker

**Przyczyna:** Użytkownik nie ma dostępu do Dockera.

**Rozwiązanie:**
```bash
# Dodaj użytkownika do grupy docker
sudo usermod -aG docker $USER

# Wyloguj i zaloguj ponownie lub:
newgrp docker
```

## Problem: Git Pull Failed

**Przyczyna:** Konflikt lub brak uprawnień.

**Rozwiązanie:**
```bash
# Na serwerze
cd /var/www/gama-software
git status
git reset --hard origin/main
git pull origin main
```

## Problem: Docker Build Failed

**Przyczyna:** Błąd w kodzie lub brak pamięci.

**Rozwiązanie:**
```bash
# Sprawdź logi
docker-compose -f build/docker-compose.yml logs

# Wyczyść cache
docker system prune -a

# Sprawdź miejsce na dysku
df -h
```

## Problem: Port 80/443 Already in Use

**Przyczyna:** Inny proces używa portów.

**Rozwiązanie:**
```bash
# Sprawdź co używa portów
sudo netstat -tlnp | grep -E ':80|:443'

# Zatrzymaj stary kontener
docker ps
docker stop <container_id>
```

---

# Zaawansowane Konfiguracje

## 1. Deployment tylko po tagach (wydania produkcyjne)

Zmodyfikuj `.github/workflows/deploy.yml`:

```yaml
on:
  push:
    tags:
      - 'v*'
```

Teraz deployment uruchomi się tylko gdy pushujemy tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

## 2. Multi-environment deployment (staging + production)

Utwórz osobne workflow dla staging:

`.github/workflows/deploy-staging.yml`:

```yaml
on:
  push:
    branches:
      - develop

jobs:
  deploy:
    # ... (podobnie jak production, ale inne secrets)
```

## 3. Rollback w razie błędu

Dodaj do `deploy.sh`:

```bash
# Backup przed deploymentem
docker tag gama-software-web:latest gama-software-web:backup

# W razie błędu:
docker tag gama-software-web:backup gama-software-web:latest
docker-compose -f build/docker-compose.yml up -d
```

## 4. Slack/Discord Notifications

Dodaj do workflow po `Notify success`:

```yaml
- name: Notify Slack
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

---

# Najlepsze Praktyki

## ✅ DO:

1. **Zawsze testuj lokalnie** przed pushem
2. **Używaj tagów** dla wersji produkcyjnych
3. **Monitoruj logi** po każdym deploymencie
4. **Rób backupy** przed dużymi zmianami
5. **Używaj secrets** dla wrażliwych danych

## ❌ NIE:

1. **Nie commituj** kluczy SSH, haseł, tokenów
2. **Nie deployuj** bez testów
3. **Nie ignoruj** błędów w logach
4. **Nie używaj** `--force` w produkcji
5. **Nie modyfikuj** kodu bezpośrednio na serwerze

---

# Quick Reference

## Ręczny deployment na serwerze

```bash
cd /var/www/gama-software
./deploy.sh
```

## Restart bez rebuildu

```bash
cd /var/www/gama-software
docker-compose -f build/docker-compose.yml restart
```

## Sprawdzenie statusu

```bash
docker-compose -f build/docker-compose.yml ps
docker-compose -f build/docker-compose.yml logs -f
```

## Rollback do poprzedniej wersji

```bash
git reset --hard HEAD~1
./deploy.sh
```

---

# Kontakt i Wsparcie

W razie problemów:
1. Sprawdź logi: `docker-compose -f build/docker-compose.yml logs -f`
2. Sprawdź status: `docker-compose -f build/docker-compose.yml ps`
3. Sprawdź GitHub Actions logs w zakładce Actions

Powodzenia! 🚀
