# WordPress Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Zrealizować GSWEB-8 przez kontrolowaną migrację strony Gama Software
z React/Symfony do edytowalnego WordPressa.

**Architecture:** Klasyczny WordPress z własnym motywem blokowym, Site Editorem
i natywną nawigacją. Funkcje niezależne od prezentacji powstają jako osobne,
testowalne wtyczki, a aplikacja jest dostarczana jako powtarzalny artefakt
kontenerowy z trwałą bazą i mediami.

**Tech Stack:** WordPress, PHP, Gutenberg, block theme, `theme.json`, Docker,
MariaDB/MySQL, GitHub Actions, Playwright oraz narzędzia jakości WordPress/PHP.

**Spec:** `docs/agent-workflows/wordpress-migration/specification.md`

## Global Constraints

- Jira GSWEB-8–GSWEB-30 jest źródłem zakresu i kryteriów akceptacji.
- Jedno zadanie wykonawcze realizuje dokładnie jedno zgłoszenie Jira.
- Funkcje epika działają bez płatnych licencji.
- Nie używamy headless React ani page buildera zastępującego Gutenberg.
- Nie usuwamy starego stosu przed GSWEB-30 i jawną zgodą właściciela.
- Nie modyfikujemy niezwiązanych zmian użytkownika ani zasobów innych projektów.
- Każda gałąź zaczyna się z zatwierdzonego, aktualnego punktu bazowego.
- Każde zgłoszenie przechodzi implementację, niezależną recenzję i testy przed scaleniem.

---

## Faza 0 — kontrolowany punkt startowy

### Task 1: GSWEB-9 — stan bazowy i bezpieczny start

**Consumes:** aktualny kod React/Symfony, konfigurację Docker/CI/CD i niezacommitowane
zmiany użytkownika na `feature/7-improve-backend`.

**Produces:** zaakceptowany commit bazowy, inwentarz funkcji, URL-i, treści,
mediów, infrastruktury i mierzalny baseline jakości.

- [x] Przeczytaj GSWEB-9, specyfikację i aktualny `README.md`.
- [x] Zidentyfikuj oraz zachowaj wszystkie istniejące zmiany użytkownika.
- [x] Ustal z właścicielem gałąź/commit, od którego ma rozpocząć się migracja.
- [x] Wykonaj inwentarz i testy baseline wymagane przez GSWEB-9.
- [x] Zapisz dowody i poddaj zmianę niezależnej recenzji.
- [ ] Scal zaakceptowany rezultat do gałęzi bazowej.

**Gate A0:** Nie rozpoczynaj GSWEB-10, dopóki punkt bazowy nie jest jednoznaczny,
a istniejące zmiany użytkownika nie są bezpiecznie zapisane.

**Status 2026-09-03:** właściciel zatwierdził Gate A0; oczekuje scalenie
zaakceptowanych commitów GSWEB-9.

## Faza 1 — fundament techniczny

### Task 2: GSWEB-10 — lokalny WordPress w Dockerze

**Consumes:** zatwierdzony baseline GSWEB-9.

**Produces:** powtarzalne lokalne środowisko WordPress, bazy i poczty testowej
bez usuwania obecnego środowiska.

- [ ] Uruchom prompt wykonawczy dla GSWEB-10.
- [ ] Zweryfikuj start od czystych wolumenów, restart i dostęp do panelu.
- [ ] Wykonaj recenzję GSWEB-10 i scal wynik.

### Task 3: GSWEB-11 — granice repozytorium, motywu i wtyczek

**Consumes:** środowisko GSWEB-10 i zasady ze specyfikacji.

**Produces:** zatwierdzona struktura plików, odpowiedzialności komponentów,
narzędzia budowania oraz sposób pakowania rozszerzeń.

- [ ] Uruchom prompt wykonawczy dla GSWEB-11.
- [ ] Sprawdź, czy motyw nie przejmuje logiki należącej do wtyczek.
- [ ] Sprawdź instalację przykładowej paczki na czystym WordPressie.
- [ ] Wykonaj recenzję i przedstaw wynik właścicielowi.

**Gate A:** Właściciel akceptuje strukturę przed GSWEB-12. Zmiana tej decyzji
później wpłynęłaby na większość gałęzi.

### Task 4: GSWEB-12 — fundament motywu blokowego

**Consumes:** zatwierdzoną strukturę z GSWEB-11.

**Produces:** aktywowalny motyw blokowy z minimalnymi templates, parts i patterns.

- [ ] Uruchom prompt wykonawczy dla GSWEB-12.
- [ ] Zweryfikuj aktywację na czystej instalacji i brak błędów edytora.
- [ ] Wykonaj recenzję i scal wynik.

### Task 5: GSWEB-13 — style globalne i responsywność

**Consumes:** motyw GSWEB-12 oraz baseline wizualny GSWEB-9.

**Produces:** tokeny `theme.json`, typografię, kolory, spacing i zachowanie
responsywne zgodne z istniejącą identyfikacją.

- [ ] Uruchom prompt wykonawczy dla GSWEB-13.
- [ ] Porównaj frontend i edytor dla desktopu, tabletu i telefonu.
- [ ] Wykonaj recenzję i scal wynik.

## Faza 2 — edytowalna strona

Zadania GSWEB-14–GSWEB-19 powinny być domyślnie wykonywane sekwencyjnie, ponieważ
mogą zmieniać te same pliki motywu. Równoległość jest dopuszczalna dopiero wtedy,
gdy GSWEB-11 określił rozłączne pliki i interfejsy.

### Task 6: GSWEB-14 — nagłówek, menu mobilne i stopka

**Produces:** natywna, edytowalna nawigacja i template parts.

- [ ] Zrealizuj i zrecenzuj GSWEB-14.
- [ ] Potwierdź edycję menu przez rolę Editor i obsługę klawiaturą.

### Task 7: GSWEB-15 — Hero

**Produces:** edytowalny wzorzec Hero zgodny z baseline.

- [ ] Zrealizuj i zrecenzuj GSWEB-15.
- [ ] Potwierdź zmianę treści i CTA bez kodu.

### Task 8: GSWEB-16 — Usługi

**Produces:** edytowalną listę usług z bezpiecznym dodawaniem, usuwaniem i zmianą kolejności.

- [ ] Zrealizuj i zrecenzuj GSWEB-16.
- [ ] Potwierdź scenariusze redaktora i responsywność kart.

### Task 9: GSWEB-17 — Moduły i rozszerzenia

**Produces:** edytowalną sekcję modułów z poprawnymi linkami i mediami.

- [ ] Zrealizuj i zrecenzuj GSWEB-17.
- [ ] Potwierdź brak treści zaszytej wyłącznie w kodzie motywu.

### Task 10: GSWEB-18 — blog

**Produces:** listę wpisów, szablon pojedynczego wpisu, archiwa i proces publikacji.

- [ ] Zrealizuj i zrecenzuj GSWEB-18.
- [ ] Potwierdź publikację oraz wycofanie wpisu rolą Editor.

### Task 11: GSWEB-19 — sekcja Kontakt

**Produces:** edytowalną prezentację danych kontaktowych oraz miejsce osadzenia formularza.

- [ ] Zrealizuj i zrecenzuj GSWEB-19.
- [ ] Potwierdź dostępność, linki i edycję danych kontaktowych.

### Task 12: GSWEB-20 — formularz, wysyłka i antyspam

**Consumes:** punkt osadzenia z GSWEB-19 oraz standard granic plugin/theme z GSWEB-11.

**Produces:** formularz działający niezależnie od motywu, lokalną wysyłkę do
odbiornika testowego, walidację i ochronę antyspamową.

- [ ] Zrealizuj i zrecenzuj GSWEB-20.
- [ ] Zweryfikuj poprawne i błędne dane, CSRF, antyspam, logi oraz brak trwałego
      zapisywania treści bez zatwierdzonej decyzji.

### Task 13: GSWEB-21 — migracja treści, mediów i złożenie strony

**Consumes:** GSWEB-14–GSWEB-20 i inwentarz GSWEB-9.

**Produces:** kompletną stronę główną bez tekstów demonstracyjnych i bez martwych linków.

- [ ] Zrealizuj i zrecenzuj GSWEB-21.
- [ ] Porównaj każdy tekst, obraz, link, kotwicę i nagłówek z inwentarzem.
- [ ] Przeprowadź ręczne scenariusze edycji właściciela.

**Gate B:** Właściciel akceptuje wygląd, kompletność treści i wygodę edycji.
Nie rozpoczynaj optymalizacji wdrożenia, jeżeli podstawowy model edycji wymaga
przebudowy.

## Faza 3 — gotowość operacyjna

### Task 14: GSWEB-22 — SEO i przekierowania

- [ ] Zrealizuj i zrecenzuj GSWEB-22 na ustalonej strukturze URL.
- [ ] Wykonaj crawl, test sitemap, canonical, robots i wszystkich przekierowań.

### Task 15: GSWEB-23 — darmowe wtyczki, role i bezpieczeństwo

- [ ] Zrealizuj i zrecenzuj GSWEB-23 po poznaniu decyzji formularza i SEO.
- [ ] Zweryfikuj macierz uprawnień Administrator/Editor/gość.
- [ ] Potwierdź, że żadna funkcja epika nie wymaga płatnej licencji.

### Task 16: GSWEB-24 — backup i pełne odtworzenie

- [ ] Zrealizuj i zrecenzuj GSWEB-24 dla docelowego modelu danych.
- [ ] Wykonaj pełne odtworzenie w odizolowanym środowisku i zapisz wynik oraz czas.

### Task 17: GSWEB-25 — CI i bramki jakości

- [ ] Zrealizuj i zrecenzuj GSWEB-25 bez przedwczesnego usunięcia kontroli starego stosu.
- [ ] Zweryfikuj zarówno zielony pipeline, jak i kontrolowane przykłady awarii
      lint, testu, budowania oraz wykrycia sekretu.

## Faza 4 — droga na produkcję

### Task 18: GSWEB-26 — deployment i rollback

**Consumes:** GSWEB-23–GSWEB-25.

**Produces:** niezmienny artefakt, trwałe dane, healthcheck, wdrożenie stagingowe
i przetestowany rollback kodu.

- [ ] Zrealizuj i zrecenzuj GSWEB-26 bez zmiany produkcyjnego ruchu.
- [ ] Potwierdź zachowanie bazy i mediów po restarcie oraz wymianie obrazu.
- [ ] Wykonaj rollback na stagingu.

### Task 19: GSWEB-27 — regresja, dostępność i wydajność

- [ ] Zrealizuj i zrecenzuj GSWEB-27 na artefakcie przeznaczonym do wdrożenia.
- [ ] Zapisz wersję artefaktu, środowisko, wyniki i dowody testów.

### Task 20: GSWEB-28 — próbna migracja i odbiór stagingu

- [ ] Zrealizuj pełną próbę GSWEB-28 od czystego, zatwierdzonego punktu startowego.
- [ ] Poproś niezależnego agenta o recenzję bramki za pomocą `03-gate-review.md`.
- [ ] Przeprowadź scenariusze Editor i Administrator z opisu Jira.

**Gate C:** Właściciel zatwierdza staging, instrukcję edycji, runbook migracji,
backup, rollback i listę znanych odchyleń. Bez tej zgody nie wolno uruchamiać
GSWEB-29.

### Task 21: GSWEB-29 — przełączenie produkcji

- [ ] Przygotuj ocenę GO/NO-GO przez `03-gate-review.md`.
- [ ] Uzyskaj jawną zgodę właściciela na okno wdrożenia.
- [ ] Zrealizuj kroki GSWEB-29, zapisując czas i wynik każdego punktu kontrolnego.
- [ ] Monitoruj uzgodnione wskaźniki przez cały okres stabilizacji.
- [ ] Nie usuwaj starego stosu podczas stabilizacji.

**Gate D:** Właściciel potwierdza zakończenie okresu stabilizacji i rezygnację
z szybkiego powrotu do starego stosu.

### Task 22: GSWEB-30 — wycofanie React/Symfony

- [ ] Przed rozpoczęciem potwierdź Gate D oraz aktualny, możliwy do odtworzenia backup.
- [ ] Zrealizuj GSWEB-30 z dokładnym inwentarzem usuwanych zasobów.
- [ ] Zweryfikuj, że żaden zasób nie jest współdzielony z innym projektem.
- [ ] Zrecenzuj dokumentację uruchomienia oraz budowania motywu i wtyczek.
- [ ] Potwierdź kompletność GSWEB-8 za pomocą `03-gate-review.md`.

## Końcowy audyt epika

- [ ] Wszystkie GSWEB-9–GSWEB-30 są zakończone i mają dowody.
- [ ] Kryteria GSWEB-8 są pokryte przez zaakceptowane wyniki zgłoszeń podrzędnych.
- [ ] Produkcja, poczta, monitoring, backup i odtworzenie mają aktualne dowody.
- [ ] Editor samodzielnie wykonuje podstawowe zmiany treści i menu.
- [ ] Repozytorium nie zawiera sekretów ani nieużywanych zależności starego stosu.
- [ ] Ostatni działający stary release ma trwały tag i instrukcję odtworzenia.
