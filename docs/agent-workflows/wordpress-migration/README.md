# Obsługa epika migracji do WordPressa przez agentów

Ten katalog opisuje spójny sposób realizacji epika
[GSWEB-8](https://gamasoftware.atlassian.net/browse/GSWEB-8) w osobnych zadaniach
agentowych. Jira jest źródłem wymagań i statusu, a dokumenty w repozytorium
ustalają wspólne zasady architektoniczne oraz sposób pracy.

## Zawartość

- [`specification.md`](specification.md) — decyzje obowiązujące całą migrację.
- [`GSWEB-9-baseline.md`](GSWEB-9-baseline.md) — zatwierdzany punkt startowy,
  inwentarz obecnej strony i dowody jakości.
- [`execution-plan.md`](execution-plan.md) — kolejność GSWEB-9–GSWEB-30,
  zależności i bramki akceptacji.
- [`launch-sequence.md`](launch-sequence.md) — gotowe polecenia do kopiowania
  w kolejności realizacji.
- [`prompts/00-orchestrator.md`](prompts/00-orchestrator.md) — wybór następnego
  bezpiecznego zadania i kontrola postępu epika.
- [`prompts/01-ticket-worker.md`](prompts/01-ticket-worker.md) — realizacja jednego
  zgłoszenia Jira.
- [`prompts/02-ticket-reviewer.md`](prompts/02-ticket-reviewer.md) — niezależna
  recenzja wykonanej pracy.
- [`prompts/03-gate-review.md`](prompts/03-gate-review.md) — odbiór etapu,
  stagingu lub przełączenia produkcyjnego.

## Rekomendowane użycie

Każde zgłoszenie powinno być realizowane w osobnym zadaniu Codex, na osobnej
gałęzi lub w osobnym worktree. Nie uruchamiaj od razu wszystkich zgłoszeń.
Zadanie zależne powinno wystartować dopiero po scaleniu i zweryfikowaniu zmian,
na których się opiera.

1. Otwórz nowe zadanie Codex w tym projekcie.
2. Wklej prompt uruchamiający z kluczem Jira:

   ```text
   Zrealizuj GSWEB-9. Pracuj zgodnie z
   docs/agent-workflows/wordpress-migration/prompts/01-ticket-worker.md.
   ```

3. Po zakończeniu otwórz osobne zadanie recenzenckie:

   ```text
   Zrecenzuj realizację GSWEB-9 zgodnie z
   docs/agent-workflows/wordpress-migration/prompts/02-ticket-reviewer.md.
   Porównaj gałąź wykonawczą z jej zatwierdzoną gałęzią bazową.
   ```

4. Popraw wykryte problemy w zadaniu wykonawczym, ponów recenzję i dopiero
   potem scal zmianę.
5. Upewnij się, że Jira odzwierciedla rzeczywisty stan oraz dowody wykonania.
6. Uruchom następne zgłoszenie według `execution-plan.md`.

Jeżeli chcesz prowadzić epik ręcznie krok po kroku, korzystaj bezpośrednio z
`launch-sequence.md`. Każde polecenie wskazuje właściwy prompt procesowy, więc
agent otrzymuje pełną procedurę bez kopiowania jej do rozmowy.

## Wybór następnego zadania

Jeżeli nie jest jasne, co można bezpiecznie rozpocząć, użyj:

```text
Określ następne bezpieczne zadanie w epiku GSWEB-8. Pracuj zgodnie z
docs/agent-workflows/wordpress-migration/prompts/00-orchestrator.md.
Nie implementuj go, dopóki nie potwierdzę wyboru.
```

## Zasada jednego zgłoszenia

Jedno zadanie Codex realizuje jedno zgłoszenie Jira. Wyjątkiem jest recenzja
bramki, która sprawdza cały zakończony etap, ale nie implementuje nowych funkcji.
Jeżeli podczas pracy zostanie odkryty nowy zakres, agent opisuje go i proponuje
osobne zgłoszenie zamiast rozszerzać bieżące zadanie.

## Bezpieczny start

GSWEB-9 wybrało `main@c26e19699c7a66a15e0854cf3bb4fce342bf2e2c` jako punkt
bazowy. Niezacommitowane zmiany z `feature/7-improve-backend` pozostają
odseparowane w lokalnych stashach i nie wchodzą do baseline. Pełny inwentarz,
reguły odzyskania oraz różnice między kodem a produkcją opisuje
[`GSWEB-9-baseline.md`](GSWEB-9-baseline.md). GSWEB-10 wolno rozpocząć dopiero po
niezależnej recenzji i zatwierdzeniu Gate A0 przez właściciela.

## Odpowiedzialność za status

- Jira przechowuje zakres, kryteria akceptacji, status i dowody wykonania.
- Git przechowuje implementację oraz historię techniczną.
- Ten katalog przechowuje proces i decyzje wspólne dla epika.
- Zamknięcie zgłoszenia wymaga działających testów i niezależnej recenzji.
- Wdrożenie na produkcję i usunięcie starego stosu zawsze wymagają jawnej zgody
  właściciela, nawet jeśli wszystkie automatyczne kontrole są zielone.
