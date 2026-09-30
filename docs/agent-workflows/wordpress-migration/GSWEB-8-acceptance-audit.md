# Analiza odbioru GSWEB-8 — 2026-09-06

## 1. Status kompletności

**Częściowo kompletne. Epika nie jest zakończona.** To datowany przegląd
kryteriów z Jiry Gama Software, nie nowy zakres ani zgoda na wdrożenie.
Podstawą jest opublikowany commit
`1257d5337295941cca0c3c5e93182b5f55a43c5c` na `feature/GSWEB-9` oraz
[PR #8](https://github.com/grzegorzrzeznikiewicz/company-site/pull/8).
`main` pozostaje na `c26e19699c7a66a15e0854cf3bb4fce342bf2e2c`.

Opisy GSWEB-9–30 odczytano ponownie w
[Jirze Gama Software](https://gamasoftware.atlassian.net/browse/GSWEB-8),
w Chrome, na koncie Gama Software. GSWEB-9–13 otrzymały dodatkowy niezależny
audyt kryterium po kryterium. Dla GSWEB-14–30 poniżej zapisano przegląd
pozostałych warunków; nie zastępuje on niezależnego odbioru każdego zgłoszenia.

[WordPress CI 34025657625](https://github.com/grzegorzrzeznikiewicz/company-site/actions/runs/34025657625)
i [legacy CI 34025657624](https://github.com/grzegorzrzeznikiewicz/company-site/actions/runs/34025657624)
mają łącznie osiem wyników SUCCESS. Sprawdzony merge testowy to
`0180d5deb425965277720090e66d0761c0a2788c`, a nie merge wykonany do `main`.
Wynik obejmuje czysty runtime, cykle ZIP, pełne odtworzenie danych, dwa testy
regresji i trzynaście testów akceptacji. **Zielony zestaw istniejących testów
nie dowodzi pokrycia wszystkich kryteriów Jiry.**

## 2. Orientacja i podział prac

Orientacja: **Całościowa**.

- Front-end: zgodność treści i wyglądu, edytor, menu, Kontakt, responsywność,
  dostępność i wskaźniki wydajności.
- Back-end: formularz i transport poczty, role, bezpieczeństwo oraz trwałe dane.
- Wspólne: paczki, dokumentacja, niezależna weryfikacja, CI, staging,
  backup/rollback, akceptacja właściciela i produkcja.

Nie jest potrzebna nowa epika do uzupełnienia brakujących kryteriów istniejących
zgłoszeń. Nie wolno traktować prośby o dokończenie epiki jako zgody na
nieuzgodnioną zmianę ruchu produkcyjnego lub usuwanie danych.

## 3. Analiza kodu i modułów

### Odbiór GSWEB-9–13

| Zgłoszenie | Potwierdzone dowody                                                                                                                                                                                                                                 | Wynik audytu i pozostała praca                                                                                                                                                                              |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GSWEB-9    | [Baseline](GSWEB-9-baseline.md): pełny SHA, inwentarz, mapowanie funkcji, decyzja o zamrożeniu GSWEB-7, właściciele decyzji, referencyjne PNG i Gate A0. Kontroler potwierdził sumy PNG i istnienie obu obiektów stash bez czytania ich zawartości. | Kryteria spełnione; komentarz dowodowy zapisany i status **Gotowe** zweryfikowany w Jirze. Nie usunięto ani nie odtworzono WIP.                                                                             |
| GSWEB-10   | [Compose](../../../wordpress/compose.yaml), bootstrap i [test runtime](../../../wordpress/tests/runtime-smoke.sh), aktualny zielony job na czystym runnerze. Lokalnie HTTP 200, Core 7.1, aktywny motyw 0.4.1, formularz 0.3.2 i Mailpit.           | Kryteria środowiska lokalnego spełnione; komentarz dowodowy i **Gotowe** zweryfikowane. Podgląd nie był resetowany.                                                                                         |
| GSWEB-11   | Zatwierdzona architektura, własne przestrzenie nazw/licencje, pozytywna lista plików ZIP i działający cykl instalacji/aktywacji/zmiany motywu.                                                                                                      | Audyt wykrył brak użytecznej instrukcji i18n i aktywacji/dezaktywacji oraz stare opisy scaffold/0.1.0. Wymaga aktualizacji dokumentacji i sprawdzenia nowych ZIP-ów, ponieważ README jest częścią paczki.   |
| GSWEB-12   | Metadane, schema, osiem szablonów, header/footer, testy otwierania i zapisu w Site Editor, WPCS oraz cykl aktualnego ZIP-a.                                                                                                                         | Brak instrukcji aktywacji i bezpiecznego cofania zapisanych w bazie nadpisań szablonu/części. Zwykła aktualizacja motywu nie nadpisuje zmian redaktora. Dokumentację należy uzupełnić przed zamknięciem.    |
| GSWEB-13   | Kontrolowane Global Styles, systemowe fonty, brak Tailwind/MUI, testy front/edytor dla szerokości 320–1440 px, kontrast i klawiatura.                                                                                                               | **Testowanie**, komentarz i status zweryfikowane. Natywny Chrome 200% z 2026-09-03 dotyczy 0.2.0/a2392dc, nie obecnego ZIP-a 0.4.1. Potrzebny aktualny zapis frontu i Site Editor; DPR nie zastępuje zoomu. |

### Pozostałe warunki odbioru

| Zgłoszenie | Istniejąca implementacja / dowód                                                                                                             | Warunek, którego nie należy pominąć                                                                                                                                                                                               |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GSWEB-14   | Natywne Navigation i części szablonu; `header-footer-navigation.spec.ts` sprawdza trasy, klawiaturę, focus, overlay oraz zapis przez Editor. | Ręczny odbiór technologii wspomagającej; nie dopisywać linków do niezatwierdzonych stron prawnych.                                                                                                                                |
| GSWEB-15   | `hero.spec.ts`: pojedynczy H1, edycja tekstów/CTA, link bez JavaScriptu i responsywność.                                                     | Aktualny rzeczywisty zoom 200% i kompletność odbioru wzorca.                                                                                                                                                                      |
| GSWEB-16   | `services.spec.ts`: edycja, zmiana liczby i kolejności kart, długa treść, semantyka ikon i klawiatura.                                       | Końcowe porównanie edytor/front i właścicielski odbiór zgodności z baseline.                                                                                                                                                      |
| GSWEB-17   | `modules.spec.ts`: edytowalne karty/listy, zmiana kolejności, usunięcie CTA; zaakceptowany początkowy cel `/#contact`.                       | Aktualny zoom 200% i odbiór kompletnej sekcji, nie samo istnienie odnośnika.                                                                                                                                                      |
| GSWEB-18   | Query Loop, archiwum i single; `blog.spec.ts` sprawdza paginację, a release acceptance publikację i wycofanie wpisu.                         | W odczytanych testach nie ma pełnego scenariusza Editor: szkic → podgląd → zaplanowana publikacja. Brak dowodu nie jest dowodem błędu funkcji; należy uzupełnić test.                                                             |
| GSWEB-19   | [Poprawka Kontaktu](GSWEB-19-contact-parity-fix.md), test geometrii pięciu szerokości, aktywny formularz i wariant bez wtyczki.              | Pozostaje **Testowanie**: aktualny zoom/technologie wspomagające oraz odbiór poprawionego wyglądu przez właściciela. Stare GO nie zastępuje odbioru poprawki.                                                                     |
| GSWEB-20   | Własna wtyczka bez płatnych zależności; walidacja, nonce, honeypot, limiter i lokalne dostarczenie/błąd transportu.                          | Zatwierdzony test odbiorcy na właściwym stagingu; nie wysyłać do klientów. Treść/odnośnik prywatności tylko po właściwej decyzji właściciela.                                                                                     |
| GSWEB-21   | `content.spec.ts`: komplet sekcji, logo, brak Welcome/lorem ipsum, cele menu i szkice prawne.                                                | Odbiór obecnego zestawu treści i wyglądu. Publikacja szkiców prawnych nie jest częścią tej zgody.                                                                                                                                 |
| GSWEB-22   | [Mapa URL/SEO](GSWEB-22-seo-url-map.md), Core sitemap i `gama-seo`, testy canonical/robots/metadata.                                         | Crawl właściwego publicznego środowiska, TLS i rzeczywiste przekierowania; staging noindex, produkcja index.                                                                                                                      |
| GSWEB-23   | [Role i bezpieczeństwo](GSWEB-23-security-operations.md), allowlista rozszerzeń, kontrola uprawnień/logowania/nagłówków.                     | Konfiguracja i kontrola docelowego HTTPS/cookies/logów; aktualna instrukcja utrzymania. Audyt dokumentacji poprawia stare numery wersji i rozdziela rollback kodu od jawnie zatwierdzanego odtworzenia danych.                    |
| GSWEB-24   | [Backup/restore](GSWEB-24-backup-restore.md), pełny izolowany restore z dokładnym ID/tytułem/treścią i hashem uploadu w CI.                  | Automatyczny harmonogram, szyfrowany off-host, retencja, kontrola świeżości i działające powiadomienie o błędzie na wybranej infrastrukturze. Sama procedura przekazująca te obowiązki operatorowi nie dowodzi ich wykonania.     |
| GSWEB-25   | Cztery zielone joby, pełne lint/static/audit, negatywne fixtures, przypięte akcje i realne trafienie cache.                                  | GitHub nie ma skonfigurowanych nazw wymaganych status checks na `main`; działający job nie jest jeszcze wymuszonym warunkiem merge. Pozostaje **Testowanie**.                                                                     |
| GSWEB-26   | Niezmienne obrazy, trwałe wolumeny, test healthcheck/rollback, rozdzielone dane i kod.                                                       | Publiczny staging, zapisany registry digest i promocja tego samego artefaktu; nie utożsamiać lokalnego image ID z opublikowanym wydaniem. Pozostaje **Testowanie**.                                                               |
| GSWEB-27   | Dwa testy Chromium desktop/mobile, axe i budżety TTFB/ładowania/transferu.                                                                   | **W toku** po audycie: brak WebKit i tabletu w regresji wydania oraz LCP/CLS/INP, porównania i uzgodnionych budżetów/odstępstwa. Potrzebny też ręczny zoom i technologia wspomagająca.                                            |
| GSWEB-28   | Trzynaście testów akceptacji i [runbook](GSWEB-28-staging-acceptance.md), niezależna próba infrastruktury testowej.                          | Publiczny odbiór, samodzielne scenariusze właściciela i instrukcja ze screenami. Automatyczny zapis przez interfejs danych edytora nie dowodzi samodzielnej obsługi wszystkich ekranów przez człowieka. Pozostaje **Testowanie**. |
| GSWEB-29   | [Pipeline produkcyjny](GSWEB-29-production-pipeline.md) i izolowany test mechanizmu promocji/SMTP/rollback.                                  | Nadal **W toku** przygotowań: nie wykonano cutoveru ani stabilizacji. Potrzebne Gate C, okno, operatorzy, świeży backup i świeża zgoda.                                                                                           |
| GSWEB-30   | Dostępna historia legacy i dokumentacja granic rozszerzeń.                                                                                   | **Do zrobienia**. Nie rozpoczynać usuwania przed stabilizacją, Gate D, sprawdzeniem zasobów współdzielonych i zgodą na dokładne cele.                                                                                             |

Wersje ZIP-ów przetestowanych w powyższym CI:

- Motyw 0.4.1: `cd5bf95f680abf6ada77cffd2d2aa53d95fba5aaf45e83097482ce2a847cf6ad`.
- Kontakt 0.3.2: `da8975851aa4dcfc612f14406e72e3417377055553f9a63bafe2354fba250cb6`.

### Uzupełnienie dokumentacji GSWEB-11–12 po audycie

Commit `c63003220af8e32e2adf537856eff48afbd98220` uzupełnia wskazane wyżej
instrukcje aktywacji, i18n i cofania nadpisań oraz aktualizuje opis architektury.
Zmienia tylko cztery pliki dokumentacji, bez kodu aplikacji, danych i wersji
rozszerzeń. To odpowiedź na wykryte braki, nie nowe zatwierdzenie produkcji.

README wchodzi do paczki, więc te ZIP-y mają **nowe** sumy. Oba przeszły
deterministyczny kontrakt i oddzielny pełny cykl instalacji na czystym WordPressie:

- Kontakt 0.3.2: `7b150f168fce6053910d87ca81592c1175a9129e1b49ef6162fc13361ceb6b7e`.
- Motyw 0.4.1: `67caf7865fb19b0acdcef21e626c28116725eb55c52511501d6c6ee808747bef`.

Środowiska `gama-package-1788690336-93342-13310` oraz
`gama-theme-package-1788690374-93560-14470` usunięto po próbach; niezależna
kontrola kontrolera nie znalazła ich kontenerów, wolumenów ani sieci.
Podgląd użytkownika pozostał dostępny. Nowe paczki wymagają odrębnej recenzji
dokumentacji oraz zdalnego CI przed przypisaniem im pełnej akceptacji wydania.
Zapis bieżącego statusu zgłoszeń po tej recenzji należy do Jiry.

Nie wolno przypisywać nowym ZIP-om dawnych sum ani wyników CI 34025657625.

## 4. Pytania i blokery

- **BLOKER publicznego stagingu:** potwierdzony host/alias SSH, użytkownik i port
  oraz konfiguracja TLS/routingu i chronione środowisko GitHub. Pytanie zostało
  przekazane właścicielowi; haseł ani kluczy nie należy wklejać do rozmowy.
- **BLOKER odbioru operacyjnego:** miejsce off-host, szyfrowanie, harmonogram,
  alarm, operator i docelowy transport poczty.
- **BLOKER Gate C:** zamknięcie technicznych braków, aktualny odbiór Kontaktu,
  ręczny test dostępności, instrukcja edytora i decyzje właściciela.
- **DO DOPRECYZOWANIA:** budżety LCP/CLS/INP i warunki pomiaru. TTFB ani
  pojedynczy lokalny pomiar nie są zamiennikiem tych wskaźników.
- Merge do `main` może uruchomić legacy deploy; rejestracja nowych workflow
  wymaga uzgodnionej integracji, nie automatycznego merge „dla konfiguracji”.

Te blokery nie zatrzymują bezpiecznej pracy nad dokumentacją i brakującymi
testami w odizolowanym środowisku.

## 5. Mikro-zadania i estymacja

Poniższe szacunki z początku audytu dotyczą wyłącznie zidentyfikowanych
uzupełnień lokalnych, nie ponownego wykonania epiki ani czasu oczekiwania na
decyzje. Wykonanie dokumentacji w punkcie A opisano powyżej; tabela nie jest
bieżącym pomiarem pozostałego czasu.

| ID  | Obszar                    | Mikro-zadanie                                                                                                 | Estymacja                               | Zależności / założenia                                                                 |
| --- | ------------------------- | ------------------------------------------------------------------------------------------------------------- | --------------------------------------- | -------------------------------------------------------------------------------------- |
| A   | Wspólne / dokumentacja    | Instrukcje GSWEB-11–12, aktualne opisy, nowe sumy ZIP i niezależna weryfikacja.                               | 1–2 h                                   | Bez zmian funkcji; cykle ZIP w osobnych namespace.                                     |
| B   | Front-end / QA            | WebKit, tablet, pomiary LCP/CLS/INP i kontrola ich zawodności w GSWEB-27.                                     | 3–6 h                                   | Przypięty runtime; wyniki laboratoryjne jawnie odróżnione od danych terenowych.        |
| C   | Front-end / QA            | Aktualny native zoom 200%, próba technologii wspomagającej, scenariusz planowania wpisu i screeny instrukcji. | 2–4 h                                   | Dokładny artefakt, wyłącznie dane testowe; akceptację właściciela zapisuje się osobno. |
| D   | Back-end / infrastruktura | Właściwy staging, off-host backup/alerty, SMTP, chronione środowiska i status checks.                         | Do oszacowania po danych infrastruktury | Nie obejmuje nieautoryzowanej konfiguracji serwera ani produkcji.                      |

## 6. Estymacja łączna

- Front-end / QA uzupełnień lokalnych: **5–10 h**.
- Wspólna dokumentacja i odbiór paczek: **1–2 h**.
- Back-end / infrastruktura i release: **nieoszacowane do czasu danych wejściowych**.
- Razem znany zakres lokalny: **6–12 h**, estymacja wstępna, nie termin ukończenia epiki.

Najważniejsze ryzyko: mylenie istniejącego zielonego CI z kompletnym odbiorem
wymagań. Ograniczają je macierz kryteriów, niezależna recenzja oraz przypisywanie
dowodów do dokładnego artefaktu.

## 7. Podsumowanie do skopiowania do Jira

Wynik audytu:
GSWEB-9 i GSWEB-10 spełniają własne kryteria i mają zapisane dowody oraz status
Gotowe. Pozostałej epiki nie uznano za zakończoną. Instrukcje GSWEB-11–12
uzupełniono i przekazano do recenzji. GSWEB-13 wymaga aktualnego pomiaru
powiększenia, a GSWEB-27
uzupełnienia zakresu przeglądarek i wydajności. Prace pozostają w tej samej epice.

Dowody:
Osiem kontroli w aktualnym CI zakończyło się powodzeniem, lecz nie obejmują one
wszystkich warunków odbioru. Lokalny podgląd działa, a produkcja i stary stos nie
zostały zmienione.

Dalsze kroki:
Uzupełnić lokalne braki, zrecenzować je i uzyskać dane właściwego stagingu.
Następnie wykonać publiczny odbiór i uzgodnić okno produkcyjne. Publikacja brancha
nie oznacza zgody na przełączenie produkcji ani usunięcie starego systemu.
