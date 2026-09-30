# GSWEB-9 — stan bazowy i bezpieczny punkt startowy migracji

- Stan dokumentu: **Gate A0 zatwierdzona przez właściciela 2026-09-03**
- Data obserwacji produkcji: **2026-09-03, Europe/Warsaw**
- Zgłoszenie: [GSWEB-9](https://gamasoftware.atlassian.net/browse/GSWEB-9)
- Autor pomiaru i dokumentacji: **Codex, we współpracy z właścicielem
  repozytorium**
- Zakres: dokumentacja i pomiary bez zmian funkcjonalnych oraz bez operacji na
  produkcji

## 1. Jednoznaczny punkt startowy

| Element                                      | Ustalony stan                                                                     |
| -------------------------------------------- | --------------------------------------------------------------------------------- |
| Repozytorium bazowe                          | `main`                                                                            |
| Commit bazowy                                | `c26e19699c7a66a15e0854cf3bb4fce342bf2e2c` (`4 reorganise code (#6)`, 2026-03-22) |
| Zgodność z remote w chwili pomiaru           | `main`, `origin/main` i `origin/HEAD` wskazywały ten sam commit                   |
| Gałąź GSWEB-9                                | `feature/GSWEB-9`, utworzona bezpośrednio z powyższego commita                    |
| Publiczny adres kontrolny                    | `https://gama-software.com/`                                                      |
| Status GSWEB-7 / `feature/7-improve-backend` | **zamrożone**; nie wchodzi do baseline WordPressa                                 |
| Ostatni CI dla commita bazowego              | GitHub Actions `CI Quality Checks`, run `23412557880`, `success`, 2026-03-22      |
| Ostatni deploy dla commita bazowego          | GitHub Actions `Deploy to Production`, run `23412630819`, `success`, 2026-03-22   |

Zapis `main@c26e196` używany w komunikacji oznacza branch `main` wskazujący na
commit zaczynający się od `c26e196`. Pełny SHA powyżej jest wiążącym
identyfikatorem baseline; sama nazwa brancha może w przyszłości przesunąć się na
inny commit.

Stan produkcyjny i stan repozytorium są dwoma osobnymi źródłami dowodowymi:

- commit bazowy definiuje kod, z którego rozpoczyna się implementacja migracji;
- obserwacja produkcji definiuje aktualne zachowanie i wygląd widziane przez
  użytkownika;
- wykrytych różnic nie wolno automatycznie rozstrzygać na korzyść jednego z tych
  źródeł. Zostały wyszczególnione w sekcji 8.

README wskazuje również projekt Figma [„Firmowa Wizytówka
Strony”](https://www.figma.com/design/cxRnksVttQoJbK9Q3R2Bk2/Firmowa-Wizyt%C3%B3wka-Strony).
Jest on pomocniczym źródłem intencji wizualnej, a nie samodzielnym źródłem
treści ani zachowania. Domyślna hierarchia porównania to: screenshoty produkcji
dla wyglądu, `main@c26e196` dla poprawionych zachowań/semantyki, Figma do
wyjaśniania niejednoznaczności. Konflikt wymagający redesignu wraca do
właściciela i nie jest rozstrzygany automatycznie.

## 2. Ochrona pracy z `feature/7-improve-backend`

Przed przełączeniem na `main` cała niezacommitowana praca użytkownika została
zapisana z plikami nieśledzonymi. Nie wykonano resetu, usuwania ani częściowego
commita tej pracy.

| Referencja lokalna                                       | Zawartość                                              | Decyzja                                                                                    |
| -------------------------------------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| `stash@{1}` / `76947116c09f4b0bd3ac21fdba50b9d97c3f7d91` | backend, CI, Docker oraz dokumentacja procesu migracji | kod aplikacyjny pozostaje zamrożony; do GSWEB-9 odtworzono wyłącznie dokumentację migracji |
| `stash@{0}` / `e97d2f7092831c13bd19ff0d935ff6ef73214d36` | wygenerowana para plików JWT                           | pozostaje odseparowana; nie wolno jej commitować ani kopiować do dokumentacji              |

Numery `stash@{N}` są pozycjami lokalnymi i mogą zmienić się po utworzeniu
nowego stasha. Do identyfikacji należy używać podanych 40-znakowych hashy i
komunikatów:

- `WIP before GSWEB-9 baseline: feature/7 backend and WordPress workflow docs`;
- `WIP generated JWT files before GSWEB-9 baseline`.

Branch `feature/7-improve-backend` nie zawiera własnych commitów względem
`main`; oba wskazywały `c26e196`. Cała różnica była niezacommitowanym WIP-em.
Stash jest lokalnym zabezpieczeniem, a nie kopią zdalną. Do czasu jawnej decyzji
o odzyskaniu albo usunięciu tej pracy nie wolno wykonywać `stash drop`,
`stash clear` ani nadpisywać plików kluczy.

Bezpieczna inspekcja nie wymaga nakładania zmian:
`git stash show --stat --include-untracked <hash>`. Listę plików nieśledzonych
można dodatkowo odczytać przez `git ls-tree -r --name-only <hash>^3`.
Odzyskanie należy wykonywać dopiero na osobnym branchu/worktree przez
`git stash apply <hash>` (nie `pop`), po uprzednim potwierdzeniu czystego
worktree. Pliki JWT wymagają osobnej decyzji i rotacji; nie należy odzyskiwać ich
na gałęzi migracyjnej.

### Inwentarz zabezpieczonych zmian

Zmodyfikowane pliki:

- `.github/workflows/ci.yml`;
- `backend/.env`, `backend/.env.local.example`, `backend/.gitignore`;
- `backend/Dockerfile`, `backend/composer.json`, `backend/composer.lock`;
- `backend/config/bundles.php`, `backend/config/packages/security.yaml`,
  `backend/config/reference.php`, `backend/config/services.yaml`;
- `backend/phpmd.xml`, `backend/symfony.lock`;
- `backend/templates/admin/dashboard.html.twig`;
- `backend/tests/Controller/ContactControllerTest.php`;
- `docker-compose.symfony.yml`.

Nowe albo przeniesione pliki kodu:

- `backend/config/packages/lexik_jwt_authentication.yaml`;
- `backend/migrations/Version20260323180000.php`;
- `backend/src/Application/Contact/SubmitContactMessage.php`;
- `backend/src/Command/CreateStorefrontUserCommand.php`;
- `backend/src/Entity/StorefrontUser.php`;
- `backend/src/EventSubscriber/LogoutRedirectSubscriber.php`;
- `backend/src/Http/Controller/Admin/DashboardController.php`;
- `backend/src/Http/Controller/Api/ContactController.php`;
- `backend/src/Http/Controller/Api/HealthController.php`;
- `backend/src/Http/Controller/Api/LoginController.php`;
- `backend/src/Http/Controller/Api/MeController.php`;
- `backend/src/Http/Controller/Web/SecurityController.php`;
- `backend/src/Repository/StorefrontUserRepository.php`;
- `backend/templates/security/login.html.twig`.

Nieśledzone pliki procesu, które znajdowały się w trzecim rodzicu stasha i
zostały odtworzone na `feature/GSWEB-9` jako część dokumentacji migracji:

- `docs/agent-workflows/wordpress-migration/README.md`;
- `docs/agent-workflows/wordpress-migration/execution-plan.md`;
- `docs/agent-workflows/wordpress-migration/launch-sequence.md`;
- `docs/agent-workflows/wordpress-migration/specification.md`;
- `docs/agent-workflows/wordpress-migration/prompts/00-orchestrator.md`;
- `docs/agent-workflows/wordpress-migration/prompts/01-ticket-worker.md`;
- `docs/agent-workflows/wordpress-migration/prompts/02-ticket-reviewer.md`;
- `docs/agent-workflows/wordpress-migration/prompts/03-gate-review.md`.

Stare ścieżki usunięte w ramach reorganizacji/przeniesienia:

- `backend/src/Controller/Admin/DashboardController.php` →
  `backend/src/Http/Controller/Admin/DashboardController.php`;
- `backend/src/Controller/ContactController.php` →
  `backend/src/Http/Controller/Api/ContactController.php`.

Odseparowane pliki generowane:

- `backend/config/jwt/private.pem`;
- `backend/config/jwt/public.pem`.

### Decyzja dotycząca GSWEB-7

Zatwierdzona decyzja brzmi: GSWEB-7 jest **zamrożone i wyłączone z baseline
WordPressa**. Nie uznajemy go za zakończone ani formalnie zastąpione i nie
scalamy jego WIP-u. Przydatne zachowania są rozpatrywane ponownie jako wymagania
WordPressa, w szczególności: formularz i wysyłka w GSWEB-20, panel/role w
GSWEB-23 oraz healthcheck, deployment i rollback w GSWEB-25–GSWEB-26. WIP
pozostaje dostępny jako materiał referencyjny do czasu zakończenia stabilizacji
i osobnej decyzji właściciela o późniejszym zamknięciu zgłoszenia i losie
stasha.

Decyzję o zamrożeniu i odseparowaniu podjął właściciel repozytorium 2026-09-03
poleceniem: zachować zmiany w stashu, przełączyć się na `main` i prowadzić
migrację z nowej gałęzi `feature/GSWEB-9`. Klasyfikacja na potrzeby migracji to
„zamrożone”; nie przypisuje ona GSWEB-7 statusu „zakończone” ani „zastąpione”.
Ewentualna późniejsza zmiana statusu w Jira wymaga osobnego polecenia.

## 3. Inwentarz publicznej strony

### URL-e i punkty wejścia

| Adres                                                  | Stan 2026-09-03                                                                      | Znaczenie w migracji                                                                 |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ |
| `http://gama-software.com/`                            | `301` do `https://gama-software.com/`                                                | zachować wymuszenie HTTPS                                                            |
| `http://www.gama-software.com/`                        | `301` do `https://www.gama-software.com/`                                            | HTTPS działa, ale nie wybiera jednego hosta                                          |
| `/`                                                    | `200`, właściwa aplikacja SPA                                                        | zachować jako stronę główną WordPressa                                               |
| `https://www.gama-software.com/`                       | `200`, kopia strony bez przekierowania                                               | wybrać host kanoniczny i dodać pojedyncze `301`                                      |
| `/#home`                                               | sekcja Start; nawigacja używa przycisku i płynnego scrollowania bez aktualizacji URL | zachować kotwicę lub uzgodnić kanoniczne `/#...`                                     |
| `/#services`                                           | sekcja Usługi                                                                        | zachować                                                                             |
| `/#modules`                                            | sekcja Moduły                                                                        | zachować                                                                             |
| `/#blog`                                               | sekcja Blog                                                                          | zastąpić wejściem do rzeczywistych wpisów/archiwum                                   |
| `/#contact`                                            | sekcja Kontakt                                                                       | zachować                                                                             |
| `/api/contact`                                         | `POST`/`OPTIONS`; kontrolny `GET` zwraca `405` i `Allow: POST, OPTIONS`              | zastąpić funkcją własnej wtyczki WordPress                                           |
| `/admin`                                               | publiczna domena zwraca fallback strony głównej SPA (`200`), a nie panel Symfony     | panel EasyAdmin nie jest publicznie osiągalny pod tym adresem; zastąpić `/wp-admin/` |
| `/robots.txt`                                          | `200 text/html`, w rzeczywistości fallback SPA                                       | zastąpić prawidłowym robots.txt                                                      |
| `/sitemap.xml`                                         | `200 text/html`, w rzeczywistości fallback SPA                                       | zastąpić prawidłową sitemapą XML                                                     |
| `/favicon.ico`                                         | `404`                                                                                | dodać ikonę witryny w WordPressie                                                    |
| `/__gsweb9_missing_path__`                             | `200 text/html`, fallback SPA                                                        | wyeliminować miękkie 404; WordPress ma zwracać prawidłowe `404`                      |
| `https://api.gama-software.com/api/contact` i `/admin` | `404`                                                                                | nie traktować subdomeny `api` jako aktywnego punktu wejścia                          |

Nie wykryto innych publicznych podstron treściowych. Linki „Polityka
prywatności” i „Regulamin” są placeholderami, a nie działającymi URL-ami.

### Widoczne sekcje i treści

1. **Stały nagłówek / nawigacja**
   - logo „Gama Software”;
   - pozycje: Start, Usługi, Moduły, Blog, Kontakt;
   - desktop: menu poziome;
   - telefon: przycisk hamburger i rozwijane menu.
2. **Hero (`home`)**
   - H1: „Gama Software”;
   - lead: „Specjalizujemy się w wdrożeniach e-commerce, konsultacjach oraz
     budowaniu agentów AI dla Twojego biznesu”;
   - CTA „Poznaj nasze usługi” przewija do sekcji Usługi.
3. **Nasze Usługi (`services`)**
   - „Wdrożenia E-commerce” — „Kompleksowe wdrożenia platform e-commerce, w tym
     Magento 2, dostosowane do potrzeb Twojego biznesu. Od analizy wymagań po
     uruchomienie sklepu.”;
   - „Konsultacje E-commerce” — „Profesjonalne doradztwo w zakresie strategii
     e-commerce, optymalizacji procesów sprzedażowych oraz wyboru najlepszych
     rozwiązań technologicznych.”;
   - „Agenci AI” — „Budujemy inteligentnych asystentów AI, którzy automatyzują
     obsługę klienta, wspierają sprzedaż i podnoszą efektywność Twojego biznesu
     online.”.
4. **Moduły Magento 2 (`modules`)**
   - nagłówek pomocniczy: „Profesjonalne rozszerzenia dostępne w modelu
     subskrypcji”;
   - Advanced SEO Suite — „Kompleksowe narzędzie do optymalizacji SEO”:
     Automatyczne generowanie meta tagów, Optymalizacja URL, Rich snippets,
     Sitemap XML, Analiza SEO on-page;
   - Smart Product Recommendations — „AI-powered rekomendacje produktów”:
     Algorytmy uczenia maszynowego, Personalizacja dla użytkownika,
     Cross-selling i up-selling, Analityka skuteczności, A/B testing;
   - Enhanced Checkout — „Zoptymalizowany proces zakupowy”: One-step checkout,
     Autouzupełnianie adresów, Integracje z kurierami, Płatności Express,
     Optymalizacja konwersji;
   - Inventory Management Pro — „Zaawansowane zarządzanie magazynem”:
     Multi-warehouse support, Automatyczne powiadomienia, Prognozowanie zapasów,
     Integracja z ERP, Raporty i analityka;
   - Customer Loyalty Program — „Program lojalnościowy dla klientów”: System
     punktów i nagród, Poziomy lojalnościowe, Spersonalizowane promocje,
     Gamifikacja, Integracja z newsletter;
   - Performance Optimizer — „Optymalizacja wydajności sklepu”: Lazy loading
     obrazów, Optymalizacja bazy danych, Cache management, CDN integration,
     Monitoring wydajności;
   - informacja „Wkrótce dostępne w formie subskrypcji” oraz CTA „Zapisz się na
     listę oczekujących”. CTA nie ma podłączonej akcji.
5. **Blog (`blog`)**
   - statyczny placeholder „🚧 / W budowie”;
   - tekst: „Nasz blog jest obecnie w przygotowaniu. Wkrótce znajdziesz tutaj
     cenne artykuły o e-commerce, technologiach AI i najlepszych praktykach w
     branży.”;
   - brak listy wpisów, routingu wpisu i procesu publikacji.
6. **Kontakt (`contact`)**
   - formularz: Imię i nazwisko, E-mail, Telefon, Wiadomość;
   - wszystkie cztery pola są wymagane;
   - przycisk ma stan „Wysyłanie...”, a odpowiedź sukces/błąd jest ogłaszana
     przez `aria-live`;
   - po sukcesie pola są czyszczone.
7. **Stopka**
   - wariant logo na ciemnym tle;
   - „© 2026 Gama Software. Wszystkie prawa zastrzeżone.”;
   - Polityka prywatności, Regulamin, Kontakt. W publicznie wdrożonym bundlu
     wszystkie trzy odsyłacze mają `href="#"`; kod baseline naprawia jedynie
     Kontakt do `#contact`.

### Media i ikony

- Jedyny własny plik graficzny to
  `src/assets/606550a668ee67574ee51adad0d7a231ffcce05b.png`: PNG RGBA,
  1024×1024, 236 789 B, SHA-256
  `f47de0880b5526c7c82f1f4355574b8396d071a34e9c127a362944066b287786`.
- Logo jest używane w nagłówku i stopce z tekstem alternatywnym „Gama Software”.
- Ikony usług i modułów pochodzą z `lucide-react`; nie są osobnymi mediami.
- Placeholder bloga używa emoji drogowego, ukrytego przed technologiami
  asystującymi.
- Nie ma galerii, obrazów wpisów, filmów ani pobieralnych materiałów.
- Na produkcyjnych screenshotach wariant logo w stopce renderuje się jak biały
  kwadrat. To znany defekt baseline, a nie element identyfikacji do odtworzenia.

### Zachowanie responsywne i interakcje

- Główny breakpoint układu to `md` (Tailwind, 768 px): menu poziome przechodzi
  w hamburger, usługi z jednej kolumny w trzy, moduły z jednej w dwie kolumny,
  a pola imię/e-mail z jednej w dwie kolumny.
- Przy `lg` moduły przechodzą w trzy kolumny.
- Kontener treści ma maksymalną szerokość `max-w-7xl`, formularz `max-w-2xl`.
- Nawigacja jest przyklejona do góry; CTA i pozycje menu wykonują płynne
  przewijanie.
- Hero, usługi, moduły i kontakt pojawiają się animacją przy wejściu do
  viewportu. Screenshoty wykonano po przewinięciu, aby aktywować pełny stan.
- Karty reagują cieniem na hover. Brak osobnych zachowań dotykowych poza
  nawigacją mobilną i naturalnym układem jednokolumnowym.

## 4. Formularz i funkcje Symfony

### Formularz kontaktowy

Frontend wysyła JSON do `/api/contact`. Backend:

- przyjmuje `POST` i `OPTIONS`; zwykłe `OPTIONS` bez nagłówków CORS zwraca
  `204`, a rzeczywisty preflight z `Origin` i
  `Access-Control-Request-Method: POST` jest obsługiwany przez Nelmio i zwraca
  `200`;
- odrzuca niepoprawny JSON statusem `400`;
- waliduje nazwę (maks. 120), e-mail (maks. 180 i format), telefon (maks. 40)
  oraz wiadomość (maks. 1000), zwracając błędy pól jako `422`;
- tworzy e-mail tekstowy i HTML, ustawia `replyTo` na adres nadawcy, a dane HTML
  escapuje;
- zwraca `201` po wysłaniu lub `502` przy błędzie transportu;
- nie zapisuje zgłoszenia w bazie danych.

Nie wykonano testowej wysyłki z produkcji, aby nie generować prawdziwego leada.
Produkcję zweryfikowano bezinwazyjnie: `GET` zwrócił oczekiwane `405`, preflight
dla dozwolonego originu zwrócił `200` i `Access-Control-Allow-Origin`, a
statyczna inspekcja faktycznie serwowanego bundla `index-BXL7kNeH.js`
o SHA-256 `e90790d992805eeffa14e348c3ed10cee20c3ddab761c0962256658c095b0263`
potwierdziła `fetch(.../api/contact)`, JSON `POST`, stan „Wysyłanie...” oraz
komunikaty `aria-live`. Nie potwierdzono na produkcji finalnego `201`, dostawy
poczty ani czyszczenia pól; te zachowania wynikają z bundla, kodu `main` i testów
automatycznych, a nie z wysłania rzeczywistego formularza.

### Panel i pozostały backend

- Symfony 8 / PHP 8.4 udostępnia trasę EasyAdmin `/admin`, zabezpieczoną HTTP
  Basic i rolą `ROLE_ADMIN` z użytkownikiem z konfiguracji środowiska.
- Dashboard jest makietą przyszłych modułów „Strony CMS”, „Blog / Wiedza” i
  „Leady kontaktowe”. Odsyłacze modułów prowadzą do `#`; nie istnieją encje CMS,
  wpisów ani leadów.
- Doctrine/PostgreSQL i migracje są przygotowane infrastrukturalnie, ale kod
  baseline nie przechowuje treści strony ani leadów w bazie.
- Nelmio CORS obsługuje `/api/*`; Symfony Mailer realizuje wysyłkę.

## 5. Mapowanie React/Symfony → WordPress

| Obecny element/funkcja                                         | Decyzja                                              | Docelowy mechanizm                                                                                 | Zadanie            |
| -------------------------------------------------------------- | ---------------------------------------------------- | -------------------------------------------------------------------------------------------------- | ------------------ |
| React SPA i root Vite                                          | migracja                                             | klasyczny WordPress renderowany po stronie serwera                                                 | GSWEB-10–GSWEB-12  |
| Globalne kolory, spacing, typografia i breakpointy             | migracja                                             | `theme.json` oraz ograniczone style motywu                                                         | GSWEB-13           |
| Nagłówek, logo, desktop/mobile menu, stopka                    | zastąpienie równoważne                               | template parts i blok Navigation                                                                   | GSWEB-14           |
| Hero i CTA scrollujące do Usług                                | migracja                                             | edytowalny pattern z linkiem do kotwicy                                                            | GSWEB-15           |
| Trzy karty usług                                               | migracja                                             | edytowalne bloki/pattern bez treści zaszytej wyłącznie w kodzie                                    | GSWEB-16           |
| Sześć kart modułów                                             | migracja                                             | edytowalne bloki/pattern; decyzja o CTA oczekujących pozostaje otwarta                             | GSWEB-17           |
| Placeholder bloga                                              | zastąpienie                                          | natywne wpisy, archiwum i szablon single                                                           | GSWEB-18           |
| Sekcja Kontakt                                                 | migracja                                             | edytowalny pattern/template content                                                                | GSWEB-19           |
| React Hook Form i `/api/contact`                               | zastąpienie                                          | własna wtyczka formularza, walidacja serwerowa, CSRF, antyspam i wysyłka WordPress                 | GSWEB-20           |
| Symfony Mailer                                                 | zastąpienie                                          | WordPress mail transport z testem lokalnym i monitoringiem błędów                                  | GSWEB-20, GSWEB-27 |
| EasyAdmin i HTTP Basic                                         | usunięcie po zastąpieniu                             | `/wp-admin/`, role Administrator/Editor i najmniejsze uprawnienia                                  | GSWEB-23, GSWEB-30 |
| WIP `/api/login`, `/api/me` i LexikJWT                         | nie scalać; usunąć po potwierdzeniu braku konsumenta | natywna sesja/logowanie WordPressa; bez publicznego JWT API, o ile nie pojawi się osobne wymaganie | GSWEB-23, GSWEB-30 |
| WIP `StorefrontUser`, migracja i komenda tworzenia użytkownika | nie scalać; zastąpić                                 | natywni użytkownicy i role WordPress Administrator/Editor                                          | GSWEB-23           |
| WIP `/login` i redirect po logout                              | nie scalać; zastąpić                                 | `wp-login.php`, `/wp-admin/` i natywny logout WordPressa                                           | GSWEB-23           |
| WIP endpoint healthcheck                                       | przenieść wymaganie, nie implementację               | healthcheck docelowego artefaktu WordPress i zależności                                            | GSWEB-26           |
| Symfony CORS                                                   | usunięcie, jeśli formularz jest same-origin          | brak osobnej warstwy CORS; wyjątki tylko na podstawie udokumentowanej potrzeby                     | GSWEB-20, GSWEB-30 |
| Doctrine/PostgreSQL starego backendu                           | usunięcie po kontroli danych                         | trwała baza WordPress MariaDB/MySQL                                                                | GSWEB-24, GSWEB-30 |
| Animacje `motion/react`                                        | zastąpienie progresywne                              | CSS/JS tylko gdy potrzebne, z obsługą `prefers-reduced-motion`                                     | GSWEB-13–GSWEB-21  |
| Obecne obrazy GHCR frontend/backend                            | zastąpienie po stabilizacji                          | niezmienny artefakt WordPress; stary release pozostaje dostępny do Gate D                          | GSWEB-25–GSWEB-30  |
| Obecny deploy SSH i rollback po tagu obrazu                    | przebudowa z zachowaniem idei                        | pipeline WordPress: ten sam artefakt staging→produkcja, trwałe dane, healthcheck i test rollbacku  | GSWEB-25–GSWEB-26  |

Nie ma funkcji biznesowej Symfony, która ma zostać przeniesiona bezpośrednio
„as is”. Prezentacja i treści są migrowane, a funkcje panelu, formularza,
bezpieczeństwa, poczty, danych i deploymentu otrzymują natywne odpowiedniki
WordPressa. Stary stos pozostaje działający i możliwy do cofnięcia aż do Gate D.

## 6. Obecny CI/CD i infrastruktura

- CI obejmuje frontend Node/Vite, backend PHP/Symfony oraz testy E2E Playwright.
- Po udanym workflow CI na `main` workflow produkcyjny buduje dwa obrazy GHCR:
  frontend `company-site` i backend `company-site-backend`.
- Obrazy otrzymują tag niezmienny `sha-<pełny-sha>` oraz ruchomy
  `main-latest`.
- Deploy przez SSH uruchamia na współdzielonym hoście usługi `personal-site`,
  `company-api` i `company-db` z konfiguracji `/srv/magento-devops`.
- Workflow rollbacku przyjmuje tag obrazu i ponownie uruchamia wskazaną parę
  frontend/backend.
- Kontrola po deployu wypisuje stan i obraz kontenerów przez `docker ps`; nie
  wykonuje HTTP healthchecku aplikacji.
- Repozytorium nie ma aktywnego workflow GitHub wdrażającego staging.
- Aktywny compose produkcyjny znajduje się poza repozytorium pod
  `/srv/magento-devops/vm2/docker-compose.yml`, dlatego z samego kodu nie da się
  potwierdzić routingu, wolumenów ani współdzielenia wszystkich zasobów.
- `build/nginx.conf` deklaruje HTTPS, fallback SPA, cache statyczny, gzip oraz
  podstawowe nagłówki bezpieczeństwa, jednak odpowiedź publicznej strony nie
  zawiera tych nagłówków i używa siedmiodniowego cache assetów zamiast roku.
- W repozytorium pozostaje również `.gitlab-ci.yml` jako starszy, alternatywny
  model CI. Nie należy usuwać go przed inwentaryzacją w GSWEB-25.
- `build/deploy.sh`, `build/docker-compose.yml` i `build/Dockerfile` opisują
  drugi, legacy tor budowania/deployu samego frontendu. Nie potwierdzono, że jest
  aktywny. `build/README.md` i główny README linkują przy tym do nieistniejącego
  `build/CI-CD-SETUP.md`. Cały ten tor wymaga klasyfikacji w GSWEB-25 i może być
  usunięty dopiero w GSWEB-30.

Wyniki dla commita bazowego: [CI Quality Checks run
23412557880](https://github.com/grzegorzrzeznikiewicz/company-site/actions/runs/23412557880)
i [Deploy to Production run
23412630819](https://github.com/grzegorzrzeznikiewicz/company-site/actions/runs/23412630819)
zakończyły się statusem `success`. Sukces workflow nie rozstrzyga rozbieżności
publicznego bundla opisanej w sekcji 8, ponieważ krok weryfikacji nie sprawdza
HTTP ani SHA serwowanego frontendu.

Plan WordPressa obejmuje nowy pipeline: GSWEB-25 definiuje CI i bramki jakości,
a GSWEB-26 niezmienny artefakt, staging, trwałość bazy/mediów, healthcheck i
sprawdzony rollback. GSWEB-29 wykonuje produkcyjny cutover dopiero po Gate C i
osobnej zgodzie właściciela. GSWEB-30 usuwa stary stos dopiero po stabilizacji,
Gate D i sprawdzeniu, że zasoby nie są współdzielone.

## 7. Nazwy konfiguracji i sekretów

Poniżej znajdują się **wyłącznie nazwy**. Dokument nie przechowuje wartości,
tokenów, haseł, kluczy, DSN-ów ani zawartości plików PEM.
Lista obejmuje konfigurację aplikacji, testów i deployu zarządzaną przez projekt;
nie próbuje katalogować wszystkich standardowych, chwilowych zmiennych runnera
GitHub/GitLab ani systemu operacyjnego.

### Runtime / lokalne środowisko

- Symfony: `APP_ENV`, `APP_DEBUG`, `APP_SECRET`, `DATABASE_URL`, `MAILER_DSN`,
  `KERNEL_CLASS`, `DEFAULT_URI`, `CORS_ALLOW_ORIGIN`, `CONTACT_RECIPIENT`,
  `CONTACT_SENDER`, `ADMIN_USERNAME`, `ADMIN_PASSWORD_HASH`,
  `ADMIN_PANEL_TITLE`;
- frontend: `FRONTEND_NODE_VERSION`, `VITE_DEV_HOST`, `VITE_DEV_PORT`,
  `VITE_API_BASE_URL`, `VITE_API_PROXY_TARGET`, `VITE_USE_POLLING`;
- Docker/testy: `SYMFONY_HTTP_PORT`, `SYMFONY_DB_VERSION`, `SYMFONY_DB_NAME`,
  `SYMFONY_DB_USER`, `SYMFONY_DB_PASSWORD`, `SYMFONY_DB_PORT`,
  `SYMFONY_MAILHOG_HTTP_PORT`, `HOST_UID`, `HOST_GID`, `CI`,
  `PLAYWRIGHT_FRONTEND_URL`, `PLAYWRIGHT_BACKEND_URL`,
  `PLAYWRIGHT_ADMIN_URL`, `PLAYWRIGHT_MAILHOG_URL`, `E2E_ADMIN_USERNAME`,
  `E2E_ADMIN_PASSWORD`;
- Symfony pomocnicze: `SYMFONY_TRUSTED_PROXIES`,
  `SYMFONY_TRUST_X_SENDFILE_TYPE_HEADER`, `SYMFONY_IDE`, `TEST_TOKEN`;
- wdrożenie: `PERSONAL_APP_IMAGE`, `COMPANY_API_IMAGE`,
  `COMPANY_API_APP_SECRET`, `COMPANY_DB_PASSWORD`, `APP_IMAGE`, `API_IMAGE`,
  `DEPLOY_GIT_SHA`, `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24`, `DOCKER_HOST`,
  `DOCKER_TLS_CERTDIR`.

Zamrożony WIP GSWEB-7 wprowadza dodatkowo nazwy `PUBLIC_FRONTEND_URL`,
`JWT_SECRET_KEY`, `JWT_PUBLIC_KEY` i `JWT_PASSPHRASE`. Są referencją historyczną,
nie wymaganiami docelowego WordPressa.

### GitHub Actions secrets

- `GITHUB_TOKEN`;
- `GHCR_USERNAME`, `GHCR_TOKEN`;
- `SERVER_HOST`, `SERVER_USER`, `SSH_PRIVATE_KEY`, `SSH_PORT`;
- `PROD_MAILER_DSN`, `PROD_CONTACT_RECIPIENT`, `PROD_CONTACT_SENDER`;
- `PROD_COMPANY_API_APP_SECRET`, `PROD_COMPANY_DB_PASSWORD`;
- `PROD_ADMIN_PASSWORD_HASH`.

Nazwy wymagane przez docelowy WordPress zostaną ustalone w GSWEB-10,
GSWEB-24–GSWEB-26. Nie należy bezrefleksyjnie kopiować starych nazw ani wartości;
sekrety mają zostać zmapowane i zrotowane zgodnie z docelową architekturą.

## 8. Baseline jakości i różnice produkcja ↔ `main`

### Dowody wizualne

- [desktop, viewport 1440×900, obraz 1440×3212](evidence/GSWEB-9/desktop.png), SHA-256
  `45b2d809180fb64f48d0961e5f980820c03e9541d2e589c3760fb7fe7409f45d`;
- [telefon, viewport 390×844, obraz 390×5190](evidence/GSWEB-9/mobile.png), SHA-256
  `f783d29082cc7cf9ebdd7bfbf9197e0c31abbcfd9b7356f7a1b6c81499122e9e`.

Screenshoty wykonano 2026-09-03 z `https://gama-software.com/` przez osobny od
zależności projektu runtime umiejętności Playwright 1.59.1 i Chromium
147.0.7727.15, po jednokrotnym przewinięciu strony w celu aktywowania animowanych
sekcji. Formularza nie wysłano. Publicznego SHA nie udało się potwierdzić; HTML
wskazywał assety z 2026-02-26. Maszynowy zapis parametrów i wyników znajduje się
w [`quality-report.json`](evidence/GSWEB-9/quality-report.json).
Wersję Playwright odczytano z
`~/.agents/skills/playwright/node_modules/playwright/package.json`, a wersję
Chromium przez `browser.version()` w tym samym uruchomieniu. Zależność projektu
(`package-lock.json`) nie była runtime’em pomiaru.

### Podstawowa dostępność

Automatyczna inspekcja DOM i kontrola kodu wykazały:

- jedna H1 i logiczna kolejność H1 → H2 → H3;
- wszystkie pola formularza mają widoczne etykiety i prawidłowe typy;
- oba obrazy logo mają tekst alternatywny; brak zduplikowanych `id`;
- produkcja ma landmarki `nav` i `footer`, ale nie ma `<main>`;
- język dokumentu produkcyjnego to `en` mimo polskiej treści;
- produkcyjny przycisk menu mobilnego nie ma dostępnej nazwy;
- przycisk menu można aktywować klawiszem Enter, lecz po otwarciu nadal nie ma
  `aria-expanded`, `aria-controls` ani etykiety;
- pierwszy Tab na desktopie przechodzi do „Start”, a na telefonie do
  bezimiennego hamburgera; brak skip linku;
- fokus korzysta z natywnego obrysu przeglądarki (`outline: auto 1px`);
- próbki kontrastu tekstu wyniosły: H1 17,75:1, lead 7,56:1, biały tekst CTA
  5,26:1, opis usługi 4,79:1 oraz stopka 6,82:1;
- kod `main@c26e196` zawiera już `<main>`, `lang="pl"`, `aria-label`,
  `aria-controls` i `aria-expanded`; te poprawki nie są widoczne w publicznym
  bundlu;
- nie przeprowadzono pełnego audytu kontrastu, klawiatury ani czytnika ekranu;
  są one zakresem GSWEB-27.

### Podstawowa wydajność

Pojedyncze pomiary Playwright 1.59.1 / Chromium 147.0.7727.15 z sieci użytej
przez wykonawcę, bez throttlingu (diagnostyczne, nie stanowiące laboratoryjnego
Lighthouse):

| Widok            |   TTFB |    FCP |      LCP |   CLS | DOMContentLoaded |   Load | Transfer zasobów |
| ---------------- | -----: | -----: | -------: | ----: | ---------------: | -----: | ---------------: |
| Desktop 1440×900 | 118 ms | 492 ms | 1 092 ms | 0,000 |           392 ms | 393 ms |       ok. 648 kB |
| Mobile 390×844   | 116 ms | 412 ms | 1 032 ms | 0,000 |           365 ms | 365 ms |       ok. 648 kB |

Surowy HTML ma 440 B, główny JS 315 789 B, CSS 94 155 B, a logo 236 789 B.
Nagłówki nie wskazywały kompresji JS/CSS. INP nie został zebrany, ponieważ
pojedyncza kontrola nie reprezentuje rzeczywistej sesji użytkownika.
Powtarzalny pomiar Lighthouse/Playwright z throttlingiem na docelowym artefakcie
należy wykonać w GSWEB-27.

### SEO i wykryte różnice

| Obszar                       | Produkcja 2026-09-03                                                               | `main@c26e196`                                     | Wniosek                                               |
| ---------------------------- | ---------------------------------------------------------------------------------- | -------------------------------------------------- | ----------------------------------------------------- |
| `<html lang>`                | `en`                                                                               | `pl`                                               | WordPress ma publikować `pl`                          |
| Tytuł                        | „Firmowa Wizytówka Strony”                                                         | taki sam                                           | wymaga decyzji i opisowego tytułu w GSWEB-22          |
| Meta description             | brak                                                                               | brak                                               | dodać w GSWEB-22                                      |
| Canonical                    | brak                                                                               | brak                                               | dodać w GSWEB-22                                      |
| Open Graph / structured data | brak                                                                               | brak                                               | ustalić w GSWEB-22                                    |
| host kanoniczny              | `www` i bez `www` zwracają `200`                                                   | brak reguły wyboru hosta                           | wybrać host i dodać `301` w GSWEB-22/GSWEB-26         |
| robots/sitemap               | fallback HTML ze statusem 200                                                      | konfiguracja SPA nie dostarcza prawidłowych plików | zastąpić w GSWEB-22                                   |
| nieznana ścieżka             | fallback HTML `200`                                                                | wynika z `try_files ... /index.html`               | zapewnić prawdziwe `404`                              |
| favicon                      | `404`                                                                              | brak jawnej ikony w `index.html`                   | dodać Site Icon                                       |
| `<main>`                     | brak                                                                               | obecny                                             | zachować semantykę z `main`                           |
| menu mobilne                 | przycisk bez dostępnej nazwy                                                       | dostępna nazwa i stan rozwinięcia                  | zachować poprawkę z `main`                            |
| link Kontakt w stopce        | `#`                                                                                | `#contact`                                         | docelowo prawidłowa kotwica                           |
| nagłówki ochronne            | brak deklarowanych `X-Frame-Options`, `X-Content-Type-Options` i HSTS w odpowiedzi | obecne w `build/nginx.conf`                        | zweryfikować realną warstwę proxy w GSWEB-23/GSWEB-26 |

HTML produkcji wskazuje bundel `/assets/index-BXL7kNeH.js` oraz datę
`Last-Modified: 2026-02-26`, wcześniejszą niż commit bazowy z 2026-03-22. Świeży
build commita bazowego tworzy inny bundel `index-CzbzKZHb.js`, co potwierdza
drift. Z zewnątrz nie da się wiarygodnie potwierdzić SHA uruchomionego obrazu.
Przed porównaniem pixel-perfect w GSWEB-13/GSWEB-21 trzeba zaakceptować zasadę:
zachowujemy wygląd i treści z produkcji, ale uwzględniamy poprawki semantyczne z
zatwierdzonego `main`.

## 9. Otwarte decyzje i właściciele

| Decyzja                                                                                                           | Właściciel                                       | Termin / blokuje                                  |
| ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ | ------------------------------------------------- |
| Host kanoniczny (`gama-software.com` czy `www.gama-software.com`) i zachowanie kotwic w adresie                   | właściciel produktu + wykonawca techniczny       | przed GSWEB-22; założenie robocze: host bez `www` |
| Docelowe URL-e i zatwierdzona treść Polityki prywatności oraz Regulaminu                                          | właściciel produktu / prawny                     | przed GSWEB-21 i GSWEB-22                         |
| Czy CTA „Zapisz się na listę oczekujących” ma działać, zostać usunięte czy pozostać informacyjne                  | właściciel produktu                              | przed GSWEB-17                                    |
| Czy start bloga ma zawierać wpisy początkowe, czy kontrolowany empty state                                        | właściciel produktu                              | przed GSWEB-18/GSWEB-21                           |
| Retencja zgłoszeń, obowiązkowość telefonu, zgoda/obowiązek informacyjny i preferowana darmowa ochrona antyspamowa | właściciel produktu + wykonawca techniczny       | przed GSWEB-20; założenie: brak zapisu do DB      |
| Czy istnieje zewnętrzny konsument wymagający kompatybilności `/api/contact`                                       | właściciel produktu + wykonawca techniczny       | przed GSWEB-20; założenie: brak                   |
| Potwierdzenie, że produkcyjny PostgreSQL nie zawiera danych wymagających migracji                                 | właściciel infrastruktury + wykonawca techniczny | przed GSWEB-24, obowiązkowo przed GSWEB-30        |
| Docelowa topologia WordPressa, wersje Core/PHP/DB i zestaw nazw sekretów                                          | wykonawca techniczny, akceptuje właściciel       | GSWEB-10–GSWEB-11, Gate A                         |
| Okno cutoveru, czas stabilizacji i warunki GO/NO-GO                                                               | właściciel produktu/infrastruktury               | Gate C, GSWEB-29                                  |

## 10. Weryfikacja

Wszystkie kontrole wykonano 2026-09-03. Żadna z nich nie wysłała formularza ani
nie zmieniła produkcji.

| Kontrola                                                                                     | Wynik                                                                                           |
| -------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `git rev-parse`, relacja branchy i `git stash show`                                          | commit bazowy i dwa stałe hashe stash potwierdzone; WIP odzyskiwalny                            |
| HTTP HEAD/GET dla hostów, URL-i technicznych i nieznanej ścieżki                             | statusy oraz fallbacki zgodne z inwentarzem w sekcji 3                                          |
| Playwright 1.59.1 / Chromium 147: desktop, mobile, DOM, klawiatura, focus, kontrast, LCP/CLS | wykonane; wyniki w sekcji 8                                                                     |
| Frontend w kontenerze: Prettier, ESLint, TypeScript, Vitest, Vite build                      | PASS; 2 pliki testowe, 4 testy; build zakończony                                                |
| Backend w kontenerze: PHP-CS-Fixer, PHPStan, PHPMD, PHPUnit                                  | PASS; 6 testów, 22 asercje                                                                      |
| Prettier dla całego katalogu migracji i `git diff --check`                                   | PASS                                                                                            |
| Kontrola istnienia i sum kontrolnych PNG                                                     | PASS                                                                                            |
| Wyszukanie sygnatur kluczy prywatnych, tokenów GitHub i JWT w Markdown/metadata PNG          | brak dopasowań                                                                                  |
| Kontrola bieżącego worktree                                                                  | tylko katalog dokumentacji GSWEB-9; brak plików JWT i zmian aplikacyjnych                       |
| Niezależna recenzja `main..cd3cb87`                                                          | PASS; brak P0/P1/P2/P3, werdykt „zaakceptować”, Gate A0 review `GO`                             |
| Akceptacja właściciela                                                                       | 2026-09-03; Gate A0 zatwierdzona wraz z regułą „wygląd produkcji + poprawki semantyczne z main” |

Pierwsza próba lokalnego `npm run build` na hoście nie wystartowała z powodu
brakującej opcjonalnej paczki natywnej Rollupa w istniejącym `node_modules` i
Node 25 zamiast przypiętego Node 24.14.0. Powtórzenie całego zestawu frontendowego
w przeznaczonym do tego kontenerze Node 24.14.0 zakończyło się powodzeniem;
problem hosta nie jest regresją kodu.

Cofnięcie GSWEB-9 polega wyłącznie na odwróceniu commita dokumentacyjnego lub
usunięciu gałęzi przed scaleniem. Nie wymaga zmian runtime. Nie wolno w ramach
cofania usuwać dwóch stashy WIP opisanych w sekcji 2.

## 11. Kryteria odbioru GSWEB-9

- [x] Punkt startowy ma pełny SHA, branch i relację do `origin/main`.
- [x] Niezacommitowany WIP z `feature/7-improve-backend` jest odseparowany i
      zinwentaryzowany.
- [x] GSWEB-7 ma jawną decyzję techniczną: zamrożone i wyłączone z baseline;
      nie jest oznaczane jako zakończone ani zastąpione.
- [x] Widoczne sekcje, treści, media, URL-e, formularz, interakcje i
      responsywność są zinwentaryzowane.
- [x] Każda funkcja React/Symfony ma decyzję: migracja, równoważne zastąpienie
      albo usunięcie po stabilizacji.
- [x] Zapisano dowody desktop/mobile oraz podstawowy baseline
      dostępności/wydajności/SEO.
- [x] Wymieniono nazwy konfiguracji i sekretów bez ich wartości.
- [x] Zapisano otwarte decyzje, właścicieli i terminy.
- [x] Niezależna recenzja nie ma otwartych uwag P0/P1/P2/P3.
- [x] Właściciel zatwierdził Gate A0 2026-09-03.

Warunki Gate A0 są spełnione. Przed rozpoczęciem GSWEB-10 zatwierdzony commit
GSWEB-9 musi jeszcze zostać scalony do gałęzi bazowej zgodnie z procesem.
