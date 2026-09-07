# Wydania produkcyjne bez stagingu

Decyzja właściciela: 2026-09-06, potwierdzona w rozmowie i zapisana w
[GSWEB-8](https://gamasoftware.atlassian.net/browse/GSWEB-8).
Dokumentacja: 2026-09-07.

**Status: model zaakceptowany; dostosowanie pipeline'u jeszcze niewykonane.**
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

## Różnica względem obecnego kodu

W commicie `19a348d` workflow WordPress produkcji jest uruchamiany ręcznie
i wymaga identyfikatora udanego przebiegu stagingowego. Oddzielny staging
dostarcza obecnie metadane artefaktu do produkcji. Istnieje też zdalna próba
kandydata przed przełączeniem. Te zależności wymagają ponownego zaprojektowania
w ramach nowego modelu; nie wolno przedstawiać ich jako gotowego procesu
bez stagingu.

Obecny legacy workflow może uruchomić wdrożenie React/Symfony po zielonym CI
na `main`. Dlatego merge nie jest neutralnym sposobem zarejestrowania nowych
workflow. Przełączenie automatyzacji musi zapobiec konkurującym wdrożeniom.

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

Lokalna specyfikacja szczegółowa jest przygotowana do przeglądu właściciela:
`docs/superpowers/specs/2026-09-07-wordpress-no-staging-release-design.md`.
Nie jest jeszcze zatwierdzeniem jej szczegółów ani implementacją workflow.

## Historyczna implementacja

[Pipeline w commicie 19a348d](https://github.com/grzegorzrzeznikiewicz/company-site/blob/19a348dea7451b1b9780e336724731a9155321fe/docs/agent-workflows/wordpress-migration/GSWEB-29-production-pipeline.md)
jest źródłem informacji o obecnym kodzie, nie docelową polityką środowisk.
