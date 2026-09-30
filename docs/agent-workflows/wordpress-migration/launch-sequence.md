# Sekwencja uruchamiania zadań GSWEB-8

Ten dokument zawiera krótkie polecenia gotowe do wklejenia w osobnych zadaniach
Codex. Po każdym wykonawcy uruchom niezależnego recenzenta i scal zmianę dopiero
po usunięciu wszystkich blokujących uwag.

## Uniwersalna recenzja po każdym zgłoszeniu

Zastąp klucz oraz wskaż rzeczywistą gałąź bazową i wykonawczą:

```text
Zrecenzuj realizację GSWEB-XX zgodnie z
docs/agent-workflows/wordpress-migration/prompts/02-ticket-reviewer.md.
Porównaj gałąź wykonawczą z jej zatwierdzoną gałęzią bazową. Nie poprawiaj kodu.
```

## Faza 0 — bezpieczny start

### GSWEB-9

```text
Zrealizuj GSWEB-9. Pracuj zgodnie z
docs/agent-workflows/wordpress-migration/prompts/01-ticket-worker.md.
Szczególnie chroń istniejące niezacommitowane zmiany i nie wybieraj punktu
bazowego bez potwierdzenia właściciela.
```

Po scaleniu GSWEB-9 potwierdź Gate A0 opisany w `execution-plan.md`.

## Faza 1 — fundament techniczny

Uruchamiaj kolejno, zawsze po scaleniu i recenzji poprzednika:

### GSWEB-10

```text
Zrealizuj GSWEB-10. Pracuj zgodnie z
docs/agent-workflows/wordpress-migration/prompts/01-ticket-worker.md.
```

### GSWEB-11

```text
Zrealizuj GSWEB-11. Pracuj zgodnie z
docs/agent-workflows/wordpress-migration/prompts/01-ticket-worker.md.
```

Po recenzji GSWEB-11 zatrzymaj wykonanie i poproś właściciela o zatwierdzenie
Gate A. Dopiero potem uruchom:

### GSWEB-12

```text
Zrealizuj GSWEB-12. Pracuj zgodnie z
docs/agent-workflows/wordpress-migration/prompts/01-ticket-worker.md.
```

### GSWEB-13

```text
Zrealizuj GSWEB-13. Pracuj zgodnie z
docs/agent-workflows/wordpress-migration/prompts/01-ticket-worker.md.
```

## Faza 2 — edytowalna strona

Domyślnie realizuj tę fazę sekwencyjnie, ponieważ zadania mogą modyfikować te
same pliki motywu.

### GSWEB-14

```text
Zrealizuj GSWEB-14. Pracuj zgodnie z
docs/agent-workflows/wordpress-migration/prompts/01-ticket-worker.md.
```

### GSWEB-15

```text
Zrealizuj GSWEB-15. Pracuj zgodnie z
docs/agent-workflows/wordpress-migration/prompts/01-ticket-worker.md.
```

### GSWEB-16

```text
Zrealizuj GSWEB-16. Pracuj zgodnie z
docs/agent-workflows/wordpress-migration/prompts/01-ticket-worker.md.
```

### GSWEB-17

```text
Zrealizuj GSWEB-17. Pracuj zgodnie z
docs/agent-workflows/wordpress-migration/prompts/01-ticket-worker.md.
```

### GSWEB-18

```text
Zrealizuj GSWEB-18. Pracuj zgodnie z
docs/agent-workflows/wordpress-migration/prompts/01-ticket-worker.md.
```

### GSWEB-19

```text
Zrealizuj GSWEB-19. Pracuj zgodnie z
docs/agent-workflows/wordpress-migration/prompts/01-ticket-worker.md.
```

### GSWEB-20

```text
Zrealizuj GSWEB-20. Pracuj zgodnie z
docs/agent-workflows/wordpress-migration/prompts/01-ticket-worker.md.
```

### GSWEB-21

```text
Zrealizuj GSWEB-21. Pracuj zgodnie z
docs/agent-workflows/wordpress-migration/prompts/01-ticket-worker.md.
```

Po recenzji GSWEB-21 zatrzymaj wykonanie i przeprowadź Gate B:

```text
Wykonaj recenzję Gate B dla epika GSWEB-8 zgodnie z
docs/agent-workflows/wordpress-migration/prompts/03-gate-review.md.
Przygotuj decyzję GO/NO-GO, ale nie rozpoczynaj kolejnej fazy.
```

## Faza 3 — gotowość operacyjna

### GSWEB-22

```text
Zrealizuj GSWEB-22. Pracuj zgodnie z
docs/agent-workflows/wordpress-migration/prompts/01-ticket-worker.md.
```

### GSWEB-23

```text
Zrealizuj GSWEB-23. Pracuj zgodnie z
docs/agent-workflows/wordpress-migration/prompts/01-ticket-worker.md.
```

### GSWEB-24

```text
Zrealizuj GSWEB-24. Pracuj zgodnie z
docs/agent-workflows/wordpress-migration/prompts/01-ticket-worker.md.
```

### GSWEB-25

```text
Zrealizuj GSWEB-25. Pracuj zgodnie z
docs/agent-workflows/wordpress-migration/prompts/01-ticket-worker.md.
```

## Faza 4 — staging i produkcja

### GSWEB-26

```text
Zrealizuj GSWEB-26. Pracuj zgodnie z
docs/agent-workflows/wordpress-migration/prompts/01-ticket-worker.md.
Nie przełączaj ruchu produkcyjnego.
```

### GSWEB-27

```text
Zrealizuj GSWEB-27. Pracuj zgodnie z
docs/agent-workflows/wordpress-migration/prompts/01-ticket-worker.md.
```

### GSWEB-28

```text
Zrealizuj GSWEB-28. Pracuj zgodnie z
docs/agent-workflows/wordpress-migration/prompts/01-ticket-worker.md.
Nie przełączaj ruchu produkcyjnego.
```

Po recenzji GSWEB-28 przeprowadź Gate C:

```text
Wykonaj recenzję Gate C dla epika GSWEB-8 zgodnie z
docs/agent-workflows/wordpress-migration/prompts/03-gate-review.md.
Przygotuj decyzję GO/NO-GO, ale nie wdrażaj na produkcję.
```

### GSWEB-29

Uruchom tylko po werdykcie GO z Gate C i osobnej zgodzie właściciela na
konkretne okno wdrożenia:

```text
Zrealizuj GSWEB-29. Pracuj zgodnie z
docs/agent-workflows/wordpress-migration/prompts/01-ticket-worker.md oraz
zaakceptowanym raportem Gate C. Zanim zmienisz ruch produkcyjny, ponownie
przedstaw checklistę GO/NO-GO i zaczekaj na moją jednoznaczną zgodę.
```

Po wdrożeniu pozostaw stary stos dostępny przez uzgodniony okres stabilizacji.
Następnie przeprowadź Gate D:

```text
Wykonaj recenzję Gate D dla epika GSWEB-8 zgodnie z
docs/agent-workflows/wordpress-migration/prompts/03-gate-review.md.
Nie usuwaj starego stosu ani infrastruktury.
```

### GSWEB-30

Uruchom tylko po zakończeniu okresu stabilizacji, werdykcie GO z Gate D i
jednoznacznej zgodzie właściciela:

```text
Zrealizuj GSWEB-30. Pracuj zgodnie z
docs/agent-workflows/wordpress-migration/prompts/01-ticket-worker.md oraz
zaakceptowanym raportem Gate D. Przed usunięciem każdego zasobu potwierdź jego
dokładny cel i brak użycia przez inne projekty. Operacje niejednoznaczne
przedstaw właścicielowi do decyzji.
```

## Zamknięcie epika

```text
Wykonaj końcową recenzję GSWEB-8 zgodnie z
docs/agent-workflows/wordpress-migration/prompts/03-gate-review.md. Sprawdź
Definition of Done epika w specification.md i dowody ze wszystkich zgłoszeń
GSWEB-9–GSWEB-30. Nie zamykaj epika bez mojego potwierdzenia.
```
