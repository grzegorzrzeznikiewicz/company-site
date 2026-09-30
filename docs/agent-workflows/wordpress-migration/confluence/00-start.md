# GSWEB — strona firmowa Gama Software

Dokumentacja migracji strony firmowej do WordPressa oraz jej późniejszego
utrzymania. Aktualizacja: 2026-09-07. Dział GSWEB znajduje się w przestrzeni
BP wskazanej przez właściciela; nie dotyczy aplikacji Budget Planner.

**Migracja nie jest jeszcze zakończona produkcyjnie.** WordPress jest
przygotowany do dalszego odbioru lokalnie i w CI. Nowy model automatycznych
wydań bez stagingu został zaakceptowany, ale workflow wymaga dostosowania.
Pierwszy cutover i usunięcie starego stosu wymagają osobnych zgód.

## Dokumentacja

1. [Projekt, zakres i aktualny stan](01-projekt.md).
2. [Architektura i środowiska](02-architektura.md).
3. [Wydania produkcyjne bez stagingu](03-wydania.md).
4. [Testy, audyt i odbiór migracji](04-jakosc-i-odbior.md).
5. [Utrzymanie, bezpieczeństwo, backup i rollback](05-utrzymanie.md).
6. [Instrukcja redaktora — strona i blog](06-instrukcja-redaktora.md).

Dokumenty rozróżniają uzgodnione wymagania, stan implementacji i rzeczywiste
wdrożenie. Zielone testy nie oznaczają automatycznie produkcyjnego odbioru.

## Najważniejsze odnośniki

- [Epika GSWEB-8](https://gamasoftware.atlassian.net/browse/GSWEB-8).
- [Tablica GSWEB](https://gamasoftware.atlassian.net/jira/software/projects/GSWEB/boards/1?groupBy=epic).
- [PR #8 — migracja do WordPressa](https://github.com/grzegorzrzeznikiewicz/company-site/pull/8).
- [Podgląd lokalny](http://localhost:8090/) — na komputerze z uruchomionym środowiskiem.
- [Publiczna produkcja](https://gama-software.com) — nie staging.

W Jira zapisujemy wymagania i statusy, w Git kod oraz wersjonowane dowody,
a w Confluence przystępny opis projektu i procedur. Nie zamieszczamy tutaj
sekretów, danych formularzy, prywatnych podglądów ani kopii baz danych.
