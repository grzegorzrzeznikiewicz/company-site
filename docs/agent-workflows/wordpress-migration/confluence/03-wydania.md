# Wydania produkcyjne bez stagingu

Decyzja właściciela: 2026-09-06, potwierdzona w rozmowie i zapisana w
[GSWEB-8](https://gamasoftware.atlassian.net/browse/GSWEB-8).
Dokumentacja: 2026-09-08. Wyniki lokalne nie są potwierdzeniem nowego CI
ani uruchomienia produkcyjnego.

**Status: model i szczegółowa specyfikacja zaakceptowane; implementacja lokalna
i niezależna recenzja zakończone, pełny CI i uruchomienie operacyjne pozostają otwarte.**
Ten dokument zapisuje uzgodnione wymagania. Nie jest potwierdzeniem wdrożenia
ani zgodą na pierwsze przełączenie produkcji.

## Decyzja

Utrzymujemy środowisko lokalne i produkcję `gama-software.com`, bez stagingu.
Kolejne standardowe wydania WordPressa mają odbywać się automatycznie po
zatwierdzonym PR, scaleniu do `main` i spełnieniu bramek. Akceptacja zmiany
następuje w procesie PR, bez dodatkowego ręcznego klikania każdego wydania.

Automatyzacja i audyt nie są sprzeczne: audyt wymaga dowodu, co zostało
zatwierdzone, przetestowane i wdrożone, oraz możliwości bezpiecznego wycofania.
Nie wymaga sam w sobie osobnego serwera stagingowego.

## Wymagania standardowego wydania

1. Powiązanie zmiany z Jira, recenzja i zatwierdzenie PR.
2. Zielone wymagane kontrole dla wersji przeznaczonej do wydania; nie wolno
   przypisywać jej testów innego commita ani samego test-merge z wcześniejszego PR.
3. Jednoznacznie zidentyfikowany, niezmienny artefakt: commit, identyfikator
   przebiegu CI i digest obrazu. Wdrożenie używa przetestowanego artefaktu.
4. Weryfikacja gotowości produkcji i świeżego, możliwego do odtworzenia backupu.
5. Wdrożenie z zachowaniem produkcyjnych treści i uploads.
6. Kontrole po wdrożeniu: HTTPS, strona główna, menu, blog, Kontakt, stan usługi
   i logi; rzeczywista dostarczalność poczty wymaga uzgodnionej próby.
7. Zapis wyniku oraz przetestowana droga rollbacku. Błąd nie może być
   raportowany jako udane wydanie.

Jednorazowe próby lokalne/CI nadal są dozwolone. Brak stagingu nie usuwa
testów odtworzenia, regresji, ochrony sekretów ani recenzji.

## Pierwsza migracja jest osobną operacją

Przed pierwszym przełączeniem z React/Symfony właściciel zatwierdza konkretną
wersję i okno. Muszą być uzgodnieni operatorzy, dostęp do właściwego hosta,
konfiguracja domeny/TLS, poczta, backup, plan powrotu i okres stabilizacji.
Należy odebrać wygląd, treści, działanie Kontaktu, dostępność i treści prawne.

Samo zaakceptowanie tego modelu nie pozwala wykonać pierwszego cutoveru,
zmienić DNS/routingu, nadpisać bazy czy usunąć starego stosu.

## Historia i aktualna przebudowa

W historycznym commicie `19a348d` workflow produkcji uruchamiano ręcznie
z identyfikatorem udanego przebiegu stagingowego. Oddzielny staging dostarczał
metadane artefaktu, istniała też zdalna próba kandydata przed przełączeniem.
Nie jest to obowiązujący model wydań.

Lokalna przebudowa na `feature/GSWEB-9` zastępuje te zależności jednym
obrazem z CI, dwiema próbami tego samego obrazu i niezależną weryfikacją
jego pochodzenia. Walidator ma odczyt metadanych, publikator zapis do
rejestru bez SSH/SMTP, a osobne zadanie przekazuje żądanie do chronionego
koordynatora hosta. Pierwszy cutover i ręczne odzyskiwanie mają własne,
rzeczywiste bramki zgody. Tekst przygotowany do zatwierdzenia nie jest zgodą.

Kod i workflow pozostają niezacommitowane. Niezależna recenzja poprawek
końcowego przeglądu potwierdziła usunięcie wszystkich 11 usterek; w ich
zakresie nie wykryto nowych problemów Critical/Important.
Nie ma nowego pełnego CI, publikacji obrazu ani wdrożenia na produkcję.
Usunięcie lokalnego pliku dawnego workflow stagingowego nie oznacza
usunięcia jakichkolwiek serwerów, danych lub historycznych dowodów.

Opublikowany legacy workflow może uruchomić wdrożenie React/Symfony po
zielonym CI na `main`. Dlatego merge nie jest neutralnym zapisem nowych
workflow. Lokalna przebudowa dodaje tryby off/legacy/wordpress, wspólną
kolejkę i blokadę hosta. Konfiguracja repozytorium oraz hosta musi zostać
osobno zweryfikowana i zatwierdzona przed włączeniem automatyzacji.

## Prace do wykonania w epice

- GSWEB-25: wymagane kontrole i dowód zgodności testowanej oraz wdrażanej wersji.
- GSWEB-26: bezpośrednie przekazanie sprawdzonego artefaktu do produkcji,
  bez zależności od zdalnego stagingu; zachowanie backupu i rollbacku.
- GSWEB-28: odbiór lokalny/CI i instrukcje, bez wymagania hosta stagingowego.
- GSWEB-29: osobny pierwszy cutover oraz późniejsze automatyczne standardowe
  wydania; bezpieczne przejście z legacy CI/CD.
- GSWEB-30: usunięcie starego stosu dopiero po stabilizacji i osobnej zgodzie.

Szczegóły implementacji wymagają spójnej specyfikacji, planu zmian, testów
negatywnych i niezależnego przeglądu. Zmiana dokumentacji sama nie zamyka
tych zgłoszeń i nie nadaje Gate C statusu GO.

Właściciel zatwierdził szczegółową specyfikację 2026-09-07 odpowiedzią „Tak”:
`docs/superpowers/specs/2026-09-07-wordpress-no-staging-release-design.md`.
Realizacja planu została rozpoczęta na `feature/GSWEB-9`. Zmiany pozostają
lokalne i niezacommitowane, bez pushowania. Akceptacja specyfikacji nie oznacza
ukończenia implementacji, przejścia nowych testów CI ani zgody na pierwsze
przełączenie produkcji.

## Historyczna implementacja

[Pipeline w commicie 19a348d](https://github.com/grzegorzrzeznikiewicz/company-site/blob/19a348dea7451b1b9780e336724731a9155321fe/docs/agent-workflows/wordpress-migration/GSWEB-29-production-pipeline.md)
opisuje poprzedni proces, nie bieżący niezacommitowany kod ani docelową
politykę środowisk.
