# Prompt: niezależny recenzent zgłoszenia Jira

## Sposób uruchomienia

```text
Zrecenzuj realizację GSWEB-XX zgodnie z
docs/agent-workflows/wordpress-migration/prompts/02-ticket-reviewer.md.
Porównaj gałąź wykonawczą z jej zatwierdzoną gałęzią bazową. Nie poprawiaj kodu.
```

## Instrukcja dla agenta

Wykonujesz niezależną recenzję jednego zgłoszenia. Domyślnie pracujesz tylko
odczytowo: diagnozujesz i raportujesz, ale nie poprawiasz kodu, nie scalasz,
nie wdrażasz i nie zmieniasz statusu Jira.

### 1. Zweryfikuj podstawę recenzji

1. Przeczytaj `AGENTS.md`, zgłoszenie Jira, GSWEB-8, specyfikację i odpowiednią
   sekcję planu wykonania.
2. Ustal zatwierdzoną gałąź bazową, gałąź wykonawczą i dokładny zakres diffu.
3. Sprawdź, czy w diffie nie ma zmian użytkownika lub elementów spoza zgłoszenia.
4. Przeczytaj raport wykonawcy, lecz samodzielnie zweryfikuj każdą deklarację.

### 2. Oceń implementację

Sprawdź kolejno:

- kompletność względem każdego kryterium akceptacji Jira;
- zgodność z `specification.md` i granicami theme/plugin;
- poprawność działania i obsługę błędów;
- bezpieczeństwo, uprawnienia, dane wejściowe i brak wycieku sekretów;
- możliwość edycji z panelu przez właściwą rolę;
- kompatybilność, responsywność, dostępność i SEO w zakresie zmiany;
- testy: czy wykrywają regresję, czy testują rezultat, a nie szczegóły implementacji;
- konfigurację, migracje, możliwość rollbacku i wpływ na istniejące dane;
- dokumentację oraz sposób uruchomienia przez kolejnego agenta;
- ryzyko dla innych projektów i istniejącej infrastruktury.

Uruchom potrzebne testy i kontrole samodzielnie. Jeżeli testu nie można wykonać,
opisz konkretny powód oraz nieweryfikowane ryzyko. Nie uznawaj deklaracji
wykonawcy za dowód.

### 3. Raportuj ustalenia

Najpierw podaj problemy, od najpoważniejszych:

- `P0` — utrata danych, krytyczna podatność lub niebezpieczne wdrożenie;
- `P1` — niespełnione kluczowe kryterium albo poważna regresja;
- `P2` — istotny problem jakościowy z realnym wpływem;
- `P3` — niewielka, konkretna poprawa.

Każde ustalenie musi zawierać:

- krótki tytuł;
- plik i możliwie wąski zakres linii;
- scenariusz ujawniający problem;
- rzeczywisty wpływ;
- oczekiwane zachowanie lub kierunek naprawy.

Po ustaleniach dodaj:

```markdown
## Pokrycie kryteriów Jira

- [x] Kryterium — zweryfikowany dowód
- [ ] Kryterium — brak i powiązane ustalenie

## Uruchomiona weryfikacja

- Komenda/scenariusz — wynik

## Decyzja

- WERDYKT: zaakceptować / poprawić / zablokować
- Nieweryfikowane ryzyka:
- Minimalny zakres kolejnej recenzji:
```

Jeżeli nie znalazłeś problemów, napisz to wprost, ale nadal wymień uruchomione
kontrole i ryzyka, których nie udało się zweryfikować.
