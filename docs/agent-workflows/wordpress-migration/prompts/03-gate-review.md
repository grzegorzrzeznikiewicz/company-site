# Prompt: recenzja bramki migracji

## Sposób uruchomienia

```text
Wykonaj recenzję Gate A, Gate B, Gate C albo Gate D dla epika GSWEB-8 zgodnie z
docs/agent-workflows/wordpress-migration/prompts/03-gate-review.md.
Przygotuj decyzję GO/NO-GO, ale nie wdrażaj i nie usuwaj infrastruktury.
```

## Instrukcja dla agenta

Oceniasz gotowość zakończonej fazy. Recenzja jest domyślnie tylko odczytowa.
Nie implementuj brakujących funkcji w ramach recenzji, nie zmieniaj ruchu
produkcyjnego i nie usuwaj zasobów.

### Wspólna procedura

1. Przeczytaj `AGENTS.md`, GSWEB-8, wszystkie zgłoszenia danej fazy,
   `specification.md` i `execution-plan.md`.
2. Sprawdź Git, CI, artefakty, Jira oraz dostępne środowiska. Oddziel deklaracje
   od dowodów, które udało się samodzielnie potwierdzić.
3. Zweryfikuj, że każde zgłoszenie fazy ma zaakceptowaną recenzję i nie posiada
   otwartego P0/P1.
4. Wykonaj testy bramki opisane poniżej.
5. Dla każdego braku zaproponuj konkretne istniejące lub nowe zgłoszenie.

### Gate A — architektura po GSWEB-11

- struktura repozytorium ma jednoznaczne odpowiedzialności;
- motyw odpowiada za prezentację, a logika przenośna za wtyczki;
- proces uruchamiania i pakowania jest powtarzalny;
- decyzje nie wymagają płatnego komponentu;
- istniejące zmiany użytkownika są zabezpieczone.

### Gate B — edytowalna strona po GSWEB-21

- wygląd i kompletność treści odpowiadają zatwierdzonemu baseline;
- Editor zmienia Hero, menu, stopkę, karty, CTA, media i wpisy bez kodu;
- formularz działa z walidacją i pocztą testową;
- nie ma martwych linków, niezatwierdzonych publikacji ani treści demonstracyjnych;
- scenariusze telefonu i desktopu są użyteczne.

### Gate C — gotowość produkcyjna po GSWEB-28

- staging używa tego samego artefaktu, który ma trafić na produkcję;
- staging ma `noindex` i pocztę bez rzeczywistych odbiorców;
- CI, bezpieczeństwo, role, SEO, backup, pełne odtworzenie i rollback mają dowody;
- pełny runbook migracji został wykonany przez osobę inną niż jego autor;
- regresja, dostępność i wydajność nie zawierają blokera;
- istnieje aktualny plan GO/NO-GO, okno wdrożenia i właściciel każdej czynności.

### Gate D — zgoda na wycofanie starego stosu

- okres stabilizacji po GSWEB-29 został zakończony;
- nie ma nierozwiązanego incydentu produkcyjnego;
- właściciel potwierdził edycję treści i działanie formularza;
- monitoring, backup i ostatni test odtworzenia są aktualne;
- ostatni release React/Symfony ma trwały tag i możliwą do wykonania instrukcję odtworzenia;
- lista zasobów do usunięcia nie zawiera elementów współdzielonych z innymi projektami;
- właściciel jawnie zgadza się utracić możliwość szybkiego przełączenia na stary stos.

### Format decyzji

```markdown
# Recenzja [nazwa bramki]

## Decyzja

- WERDYKT: GO / NO-GO
- Data i oceniana wersja:
- Oceniane środowisko:

## Dowody

- Wymaganie — dowód i wynik

## Blokery

- Priorytet — opis — odpowiedzialne zgłoszenie

## Ryzyka zaakceptowane świadomie

- Ryzyko — wpływ — właściciel decyzji

## Plan cofnięcia

- Punkt powrotu:
- Warunek uruchomienia:
- Osoba podejmująca decyzję:

## Czynność wymagająca zgody właściciela

- Dokładna decyzja, której nie może podjąć agent
```

Werdykt GO oznacza gotowość techniczną, a nie automatyczną zgodę na działanie.
Przełączenie produkcji i usunięcie starego stosu nadal wymagają osobnego,
jednoznacznego polecenia właściciela.
