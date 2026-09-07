# Projekt, zakres i aktualny stan

Aktualizacja: 2026-09-07. Dokumentacja migracji i późniejszego utrzymania
strony firmowej. **Migracja nie została jeszcze zakończona produkcyjnie.**

## Najważniejsze odnośniki

- [Epika GSWEB-8](https://gamasoftware.atlassian.net/browse/GSWEB-8).
- [Tablica projektu](https://gamasoftware.atlassian.net/jira/software/projects/GSWEB/boards/1?groupBy=epic).
- [PR #8 — implementacja migracji](https://github.com/grzegorzrzeznikiewicz/company-site/pull/8).
- [Lokalny podgląd](http://localhost:8090/), dostępny na komputerze z uruchomionym środowiskiem.
- [Produkcja](https://gama-software.com), której nie należy traktować jako stagingu.

## Cel i zakres

Zastępujemy React/Vite oraz kontaktowy backend Symfony klasycznym WordPressem.
Właściciel ma edytować treści, menu, sekcje, nagłówek, stopkę i blog bez zmian
w kodzie. Migracja zachowuje wygląd, treści i funkcje obecnej strony; nie jest
redesignem.

Zakres obejmuje logo, menu Start / Usługi / Moduły / Blog / Kontakt, przyciski
prowadzące do właściwych sekcji, formularz kontaktowy z rzeczywistą wysyłką,
blog, SEO, bezpieczeństwo, backup, odtworzenie i proces wydań. Kontakt ma
szczególne znaczenie: samo wyświetlenie formularza nie potwierdza dostarczenia
wiadomości.

Używamy WordPress Core i darmowych, odpowiednio licencjonowanych rozszerzeń.
Nowa zewnętrzna wtyczka wymaga osobnego zadania w ramach epiki oraz oceny
licencji, bezpieczeństwa, danych i utrzymania. Sklep internetowy, płatne
rozszerzenia, pełny redesign i publikacja naszych wtyczek w WordPress.org
nie należą do obecnego zakresu.

## Przyjęte decyzje

- Baseline to gałąź `main` w commicie `c26e196`; pełny identyfikator:
  `c26e19699c7a66a15e0854cf3bb4fce342bf2e2c`.
- Cała migracja powstaje na `feature/GSWEB-9`. Wcześniejszy pomysł osobnej
  gałęzi dla każdego podzadania został zastąpiony decyzją właściciela.
- Niezacommitowana praca z `feature/7-improve-backend` została odseparowana
  w stashach; nie wchodzi do baseline i nie wolno jej usuwać ani przywracać
  przy okazji migracji.
- Są dwa środowiska: lokalne i produkcyjne. Nie tworzymy osobnego stagingu.
- Docelowo zatwierdzony PR i merge do `main` uruchamiają automatyczne wydanie
  po spełnieniu bramek jakości i bezpieczeństwa.
- Pierwsze przełączenie na WordPress oraz późniejsze usunięcie React/Symfony
  nadal wymagają osobnych, wyraźnych decyzji właściciela.

## Stan realizacji

PR #8 sprawdzony 2026-09-07 pozostaje otwarty i niescalony. Jego HEAD to
`19a348dea7451b1b9780e336724731a9155321fe`; `main` nie został zmieniony.
Ostatnie potwierdzone CI tej wersji z 2026-09-06: cztery zadania WordPressa
i cztery zadania React/Symfony zakończone sukcesem.

Zestawienie z Jira odczytane 2026-09-06:

| Status | Zgłoszenia | Liczba |
| --- | --- | ---: |
| Gotowe | GSWEB-9–13 | 5 |
| Testowanie | GSWEB-14–23, 25, 26, 28 | 13 |
| W toku | GSWEB-24, 27, 29 | 3 |
| Do zrobienia | GSWEB-30 | 1 |

Wszystkie 22 zadania podrzędne zostały przeniesione na tablicę. Bieżący status
należy odczytać w Jira; powyższe zestawienie jest datowanym punktem odniesienia.

Do zakończenia pozostają dostosowanie pipeline'u do decyzji bez stagingu,
odbiór właścicielski, konfiguracja i weryfikacja produkcyjna, pierwsze
przełączenie, stabilizacja oraz dopiero potem wycofanie starego stosu.
Zielone testy lokalne lub CI nie są potwierdzeniem wykonania tych działań.

## Jak czytać dokumentację

Architektura opisuje granice kodu i danych. Dokument wydań rozróżnia zatwierdzony
model od obecnej konfiguracji. Audyt wskazuje dowody i warunki odbioru.
Procedury utrzymania opisują backup, bezpieczeństwo i rollback. Instrukcja
redaktora pokazuje edycję strony i bloga bez kodowania.
