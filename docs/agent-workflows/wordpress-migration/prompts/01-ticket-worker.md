# Prompt: wykonawca pojedynczego zgłoszenia Jira

## Sposób uruchomienia

W poniższym poleceniu zastąp `GSWEB-XX` konkretnym kluczem z zakresu
GSWEB-9–GSWEB-30:

```text
Zrealizuj GSWEB-XX. Pracuj zgodnie z
docs/agent-workflows/wordpress-migration/prompts/01-ticket-worker.md.
```

## Instrukcja dla agenta

Realizujesz dokładnie jedno wskazane zgłoszenie należące do epika GSWEB-8.
Doprowadź je do kompletnego, przetestowanego rezultatu, ale nie scalaj zmian,
nie wdrażaj na produkcję i nie zamykaj zgłoszenia bez upoważnienia użytkownika.

### 1. Zbuduj kontekst

1. Przeczytaj wszystkie obowiązujące `AGENTS.md`.
2. Przeczytaj w całości:
   - wskazane zgłoszenie Jira wraz z załącznikami, komentarzami i relacjami;
   - GSWEB-8;
   - `docs/agent-workflows/wordpress-migration/specification.md`;
   - właściwą sekcję `docs/agent-workflows/wordpress-migration/execution-plan.md`.
3. Sprawdź aktualny kod, `git status`, historię oraz wynik CI. Nie zakładaj, że
   opis planu dokładnie odpowiada stanowi po ostatnich merge'ach.
4. Ustal i zapisz:
   - kryteria akceptacji;
   - zależności oraz dowody ich spełnienia;
   - pliki, interfejsy i dane, których dotknie zmiana;
   - właściwe testy;
   - operacje trudne do cofnięcia.
5. Jeżeli Jira jest niedostępna albo zależność nie jest spełniona, zatrzymaj się
   i poproś o brakujące dane lub decyzję. Nie rekonstruuj wymagań z tytułu.

### 2. Zabezpiecz pracę

1. Nie usuwaj, nie resetuj i nie nadpisuj zmian użytkownika.
2. Ustal zatwierdzoną gałąź bazową. Jeżeli nie da się jej jednoznacznie określić,
   zapytaj użytkownika przed utworzeniem gałęzi.
3. Pracuj w osobnym worktree lub na osobnej gałęzi nazwanej
   `feature/<klucz-małymi-literami>-<krótki-opis>`.
4. Przed pierwszą zmianą przedstaw krótki plan zawierający dokładne pliki,
   kolejność testów i ryzyka. Dla zadania wieloetapowego zapisz szczegółowy plan
   w repozytorium zgodnie z obowiązującą umiejętnością planowania.

### 3. Implementuj małymi krokami

Dla każdego niezależnego zachowania:

1. Dodaj lub zaktualizuj test, który przed implementacją wykazuje brak zachowania.
2. Uruchom ten test i potwierdź oczekiwaną przyczynę niepowodzenia.
3. Dodaj minimalną implementację spełniającą test i specyfikację.
4. Uruchom test ponownie.
5. Uruchom szerszy zestaw kontroli właściwy dla dotkniętego obszaru.
6. Zaktualizuj dokumentację i przykładową konfigurację w tym samym kroku, jeśli
   bez nich rezultat nie jest użyteczny.
7. Wykonaj mały commit z kluczem Jira, np.:

   ```text
   feat(GSWEB-12): add block theme foundation
   ```

Nie wprowadzaj nowych bibliotek bez sprawdzenia bieżącej dokumentacji,
kompatybilności, licencji, utrzymania i potrzeby wynikającej z kryteriów.

### 4. Zweryfikuj rezultat

1. Przeczytaj ponownie każde kryterium akceptacji i przypisz do niego dowód.
2. Uruchom pełny zestaw kontroli wymagany przez repozytorium dla zmienionych
   obszarów. Nie przedstawiaj wyniku jako poprawnego na podstawie wcześniejszego
   uruchomienia sprzed ostatniej zmiany.
3. Obejrzyj cały diff względem zatwierdzonej bazy i usuń przypadkowe zmiany.
4. Sprawdź bezpieczeństwo, dostępność, responsywność, SEO, logowanie i obsługę
   błędów w zakresie adekwatnym do zadania.
5. Dla UI pokaż dowody dla reprezentatywnego desktopu i telefonu. Dla operacji
   infrastrukturalnej pokaż wynik scenariusza sukcesu oraz kontrolowanej awarii.
6. Nie ujawniaj sekretów w raporcie, logach ani Jira.

### 5. Przekaż wynik

Zakończ raportem:

```markdown
## Wynik

- Zgłoszenie:
- Gałąź bazowa i gałąź robocza:
- Commity:
- Zmienione obszary:

## Kryteria akceptacji

- [x] Kryterium — dowód
- [ ] Kryterium — konkretny brak lub blocker

## Weryfikacja

- Komenda/test ręczny:
- Wynik i czas wykonania:

## Ryzyka i kroki operacyjne

- Ryzyko:
- Konfiguracja lub migracja:
- Sposób cofnięcia:

## Zakres odkryty poza zgłoszeniem

- Propozycja osobnego zgłoszenia albo „brak”
```

Jeżeli masz autoryzowany dostęp do Jira, możesz dodać raport jako komentarz i
przenieść zadanie do uzgodnionego statusu recenzji. Nie oznaczaj zadania jako
ukończone, dopóki niezależna recenzja nie potwierdzi rezultatu.
