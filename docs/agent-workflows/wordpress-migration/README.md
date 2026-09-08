# Obsługa epika migracji do WordPressa przez agentów

Ten katalog opisuje spójny sposób realizacji epika
[GSWEB-8](https://gamasoftware.atlassian.net/browse/GSWEB-8) w osobnych zadaniach
agentowych. Jira jest źródłem wymagań i statusu, a dokumenty w repozytorium
ustalają wspólne zasady architektoniczne oraz sposób pracy.

## Aktualizacja decyzji właściciela — 2026-09-06/08

Obowiązuje praca na jednej gałęzi `feature/GSWEB-9`, środowisko lokalne
i produkcja, **bez osobnego stagingu**. Kolejne standardowe wydania mają
być automatyczne po zatwierdzonym PR, merge do `main` i przejściu bramek.
Pierwszy cutover oraz usunięcie starego stosu nadal wymagają osobnych zgód.
Te decyzje zastępują sprzeczne wymagania stagingu, osobnych gałęzi i ręcznej
akceptacji każdego wydania w starszych dokumentach oraz poniższych pierwotnych
rekomendacjach organizacji pracy.

Kod w `19a348d` implementował poprzedni ręczny proces ze stagingiem.
[Nowa specyfikacja](../../superpowers/specs/2026-09-07-wordpress-no-staging-release-design.md)
została zaakceptowana przez właściciela 2026-09-07 odpowiedzią „Tak”.
[Plan implementacji](../../superpowers/plans/2026-09-07-wordpress-no-staging-release.md)
jest realizowany lokalnie, bez nowych commitów, pushowania ani worktree.
Akceptacja specyfikacji nie jest wdrożeniem nowego pipeline'u ani decyzją GO.
[Dokumentacja Confluence](confluence/README.md)
rozdziela aktualną politykę od historycznych dowodów implementacji; dział GSWEB
opublikowano w przestrzeni BP wskazanej przez właściciela.

Stan częściowy 2026-09-08: manifest, bezpieczny transport, jeden kandydat
dla dwóch prób, walidacja pochodzenia/publikator, transakcja hosta i workflow
przeszły przeglądy zadań 1–6. Świeża izolowana próba na Linuksie zakończyła
się wynikiem 170/170 testów jednostkowych. Powtórzono także obie rzeczywiste
próby lokalne, z 6 testami regresji, 13 akceptacyjnymi i zachowaniem danych
przy rollbacku. Każda próba wykryła pięć celowych uszkodzeń lub usunięć danych
testowych. Niezależna recenzja poprawek potwierdziła usunięcie wszystkich
11 usterek; w ich zakresie nie wykryto nowych problemów Critical/Important.
To nie jest nowy pełny CI,
publikacja obrazu ani wdrożenie produkcyjne; Gate C pozostaje NO-GO.

## Zawartość

- [`specification.md`](specification.md) — decyzje obowiązujące całą migrację.
- [`GSWEB-8-acceptance-audit.md`](GSWEB-8-acceptance-audit.md) — datowany audyt
  kryteriów i brakujących dowodów z 2026-09-06; zielony CI nie oznacza zakończenia epiki.
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
- [`prompts/03-gate-review.md`](prompts/03-gate-review.md) — pierwotny szablon
  odbioru etapu; jego wymagania stagingu zastępuje powyższa decyzja.

## Obowiązujący sposób realizacji

Całą zaakceptowaną migrację prowadzimy w rzeczywistym katalogu projektu,
na `feature/GSWEB-9`. Nie tworzymy dodatkowych worktree, commitów ani pushy.
Zakończenie zadania nie upoważnia do publikacji lub merge.

1. Wykonuj kolejny zależny etap zatwierdzonego planu, zachowując dotychczasowe
   lokalne zmiany i dowody ich pochodzenia.
2. Do każdego etapu dołącz testy zachowania oraz niezależny przegląd jego
   pełnego zakresu, także nowych niezacommitowanych plików.
3. Popraw istotne uwagi i zweryfikuj poprawkę przed rozpoczęciem zależnego etapu.
4. Na końcu przeprowadź wspólny przegląd całości oraz aktualizację Jira
   i Confluence zgodną z rzeczywistymi wynikami.

`launch-sequence.md` i pierwotne prompty pozostają materiałem historycznym
dotyczącym podziału zgłoszeń. Nie są zgodą na worktree, merge, staging,
produkcję ani zmianę obowiązujących ograniczeń właściciela.

## Wybór następnego zadania

Jeżeli nie jest jasne, co można bezpiecznie rozpocząć, użyj:

```text
Określ następne bezpieczne zadanie w epiku GSWEB-8. Pracuj zgodnie z
docs/agent-workflows/wordpress-migration/prompts/00-orchestrator.md.
Nie implementuj go, dopóki nie potwierdzę wyboru.
```

## Zasada kontrolowanego zakresu

Właściciel zlecił realizację całego epika w jednym ciągu. Poszczególne zadania
Jira nadal mają oddzielne kryteria i dowody; przegląd jednego etapu nie zamyka
automatycznie pozostałych. Nowy zakres poza zatwierdzoną migracją wymaga
osobnego ustalenia zamiast cichego rozszerzania prac.

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
