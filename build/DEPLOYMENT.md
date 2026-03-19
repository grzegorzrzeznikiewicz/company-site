# Przewodnik Wdrożenia - gama-software.com

## Wymagania Wstępne

- Serwer dedykowany z Ubuntu (20.04 lub nowszy)
- Dostęp root lub sudo
- Domena gama-software.com skierowana na IP serwera (rekordy A)

## Krok 1: Przygotowanie Serwera

### 1.1 Aktualizacja Systemu

```bash
sudo apt update && sudo apt upgrade -y
```

### 1.2 Instalacja Docker

```bash
# Instalacja wymaganych pakietów
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# Dodanie klucza GPG Dockera
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Dodanie repozytorium Docker
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalacja Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Sprawdzenie instalacji
sudo docker --version
```

### 1.3 Instalacja Docker Compose

```bash
# Pobranie Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Nadanie uprawnień
sudo chmod +x /usr/local/bin/docker-compose

# Sprawdzenie instalacji
docker-compose --version
```

### 1.4 Konfiguracja Firewall

```bash
# Instalacja UFW (jeśli nie jest zainstalowana)
sudo apt install -y ufw

# Konfiguracja podstawowych reguł
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Włączenie firewall
sudo ufw enable
sudo ufw status
```

## Krok 2: Konfiguracja DNS

Upewnij się, że Twoja domena wskazuje na serwer:

```bash
# Sprawdź, czy domena wskazuje na właściwy IP
dig gama-software.com +short
dig www.gama-software.com +short
```

Jeśli nie, skonfiguruj rekordy DNS u swojego rejestratora domen:

```
Typ: A
Nazwa: @
Wartość: [IP TWOJEGO SERWERA]
TTL: 3600

Typ: A
Nazwa: www
Wartość: [IP TWOJEGO SERWERA]
TTL: 3600
```

## Krok 3: Przesłanie Kodu na Serwer

### 3.1 Zainstaluj Git (jeśli nie jest zainstalowany)

```bash
sudo apt install -y git
```

### 3.2 Metoda A: Używając Git (Zalecane)

```bash
# Utwórz katalog dla projektu
sudo mkdir -p /var/www/gama-software
sudo chown $USER:$USER /var/www/gama-software
cd /var/www/gama-software

# Sklonuj repozytorium (zastąp URL swoim repo)
git clone [URL_TWOJEGO_REPO] .
```

### 3.2 Metoda B: Ręczne przesłanie przez SCP

Z lokalnego komputera:

```bash
# Utwórz archiwum projektu (z katalogu projektu)
tar -czf gama-software.tar.gz .

# Prześlij na serwer
scp gama-software.tar.gz user@[IP_SERWERA]:/tmp/

# Na serwerze:
sudo mkdir -p /var/www/gama-software
sudo chown $USER:$USER /var/www/gama-software
cd /var/www/gama-software
tar -xzf /tmp/gama-software.tar.gz
rm /tmp/gama-software.tar.gz
```

## Krok 4: Konfiguracja SSL - WAŻNE!

### 4.1 Modyfikacja nginx.conf przed pierwszym uruchomieniem

Przed pierwszym uruchomieniem musisz **tymczasowo wyłączyć** konfigurację SSL w nginx.conf:

```bash
cd /var/www/gama-software
nano nginx.conf
```

Zakomentuj lub usuń całą sekcję `server` dla portu 443 (linijki z `listen 443` do końca pliku). Zostaw tylko sekcję dla portu 80. Powinno wyglądać tak:

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name gama-software.com www.gama-software.com;

    # Certbot challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

### 4.2 Pierwsze uruchomienie bez SSL

```bash
cd /var/www/gama-software
sudo docker-compose -f build/docker-compose.yml -f build/docker-compose.yml up -d web
```

### 4.3 Uzyskanie Certyfikatu SSL

```bash
# Utwórz katalogi dla certbot
sudo mkdir -p /var/www/certbot
sudo mkdir -p /etc/letsencrypt

# Uzyskaj certyfikat
sudo docker run -it --rm \
  -v /etc/letsencrypt:/etc/letsencrypt \
  -v /var/www/certbot:/var/www/certbot \
  certbot/certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email twoj-email@example.com \
  --agree-tos \
  --no-eff-email \
  -d gama-software.com \
  -d www.gama-software.com
```

### 4.4 Przywrócenie pełnej konfiguracji nginx

Po uzyskaniu certyfikatu, przywróć oryginalną konfigurację nginx.conf z całą sekcją SSL:

```bash
nano nginx.conf
```

Odkomentuj lub przywróć sekcję HTTPS (całą oryginalną zawartość pliku nginx.conf).

### 4.5 Restart z pełną konfiguracją

```bash
sudo docker-compose -f build/docker-compose.yml down
sudo docker-compose -f build/docker-compose.yml -f build/docker-compose.yml up -d
```

## Krok 5: Uruchomienie Aplikacji

### 5.1 Build i Start Kontenerów

```bash
cd /var/www/gama-software

# Build obrazu Docker
sudo docker-compose -f build/docker-compose.yml build

# Uruchomienie w tle
sudo docker-compose -f build/docker-compose.yml -f build/docker-compose.yml up -d

# Sprawdzenie statusu
sudo docker-compose -f build/docker-compose.yml ps
```

### 5.2 Sprawdzenie Logów

```bash
# Logi wszystkich kontenerów
sudo docker-compose -f build/docker-compose.yml logs -f

# Logi konkretnego kontenera
sudo docker-compose -f build/docker-compose.yml logs -f web
```

### 5.3 Testowanie

Otwórz przeglądarkę i przejdź do:
- http://gama-software.com (powinno przekierować na HTTPS)
- https://gama-software.com (powinna załadować się strona)

## Krok 6: Automatyczne Odnowienie Certyfikatu

Certyfikat SSL jest już automatycznie odnawiany przez kontener certbot w docker-compose.yml.

Możesz dodatkowo ustawić cron job dla pewności:

```bash
sudo crontab -e
```

Dodaj linię:

```
0 3 * * * /usr/local/bin/docker-compose -f /var/www/gama-software/docker-compose.yml restart certbot
```

## Zarządzanie Aplikacją

### Podstawowe Komendy

```bash
# Start
sudo docker-compose -f build/docker-compose.yml -f build/docker-compose.yml up -d

# Stop
sudo docker-compose -f build/docker-compose.yml down

# Restart
sudo docker-compose -f build/docker-compose.yml restart

# Rebuild po zmianach w kodzie
sudo docker-compose -f build/docker-compose.yml down
sudo docker-compose -f build/docker-compose.yml build --no-cache
sudo docker-compose -f build/docker-compose.yml -f build/docker-compose.yml up -d

# Sprawdzenie statusu
sudo docker-compose -f build/docker-compose.yml ps

# Logi
sudo docker-compose -f build/docker-compose.yml logs -f
```

### Aktualizacja Aplikacji

```bash
cd /var/www/gama-software

# Pobierz najnowszy kod (jeśli używasz Git)
git pull

# Rebuild i restart
sudo docker-compose -f build/docker-compose.yml down
sudo docker-compose -f build/docker-compose.yml build --no-cache
sudo docker-compose -f build/docker-compose.yml -f build/docker-compose.yml up -d
```

## Monitoring i Utrzymanie

### Sprawdzanie Zasobów

```bash
# Wykorzystanie dysków przez Docker
sudo docker system df

# Czyszczenie nieużywanych obrazów
sudo docker system prune -a

# Sprawdzanie wykorzystania zasobów
sudo docker stats
```

### Backup

```bash
# Backup certyfikatów SSL
sudo tar -czf ssl-backup-$(date +%Y%m%d).tar.gz /etc/letsencrypt

# Backup aplikacji
sudo tar -czf app-backup-$(date +%Y%m%d).tar.gz /var/www/gama-software
```

## Rozwiązywanie Problemów

### Problem: Strona nie ładuje się

```bash
# Sprawdź status kontenerów
sudo docker-compose -f build/docker-compose.yml ps

# Sprawdź logi
sudo docker-compose -f build/docker-compose.yml logs web

# Sprawdź czy porty są otwarte
sudo netstat -tlnp | grep -E '80|443'
```

### Problem: Błąd SSL

```bash
# Sprawdź certyfikaty
sudo ls -la /etc/letsencrypt/live/gama-software.com/

# Sprawdź logi nginx
sudo docker-compose -f build/docker-compose.yml logs web | grep -i ssl
```

### Problem: Docker nie startuje

```bash
# Sprawdź status Docker
sudo systemctl status docker

# Restart Docker
sudo systemctl restart docker
```

## Bezpieczeństwo

### Rekomendacje

1. Regularnie aktualizuj system:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. Monitoruj logi:
   ```bash
   sudo docker-compose -f build/docker-compose.yml logs -f
   ```

3. Używaj fail2ban dla ochrony SSH:
   ```bash
   sudo apt install -y fail2ban
   sudo systemctl enable fail2ban
   sudo systemctl start fail2ban
   ```

4. Regularnie twórz backupy

## Kontakt

W razie problemów sprawdź logi lub skontaktuj się z administratorem.
