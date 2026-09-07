# Testy, audyt i odbiór migracji

Dokumentacja: 2026-09-07. Wyniki poniżej dotyczą konkretnych prób z
2026-09-06, a nie ponownego wykonania testów podczas pisania tej strony.

## Potwierdzone dowody

HEAD PR: `19a348dea7451b1b9780e336724731a9155321fe`.

- [WordPress CI — 4/4 zadania zakończone sukcesem](https://github.com/grzegorzrzeznikiewicz/company-site/actions/runs/34043794458).
- [Legacy CI — 4/4 zadania zakończone sukcesem](https://github.com/grzegorzrzeznikiewicz/company-site/actions/runs/34043794462).
- [PR #8: wyniki i niezależne przeglądy](https://github.com/grzegorzrzeznikiewicz/company-site/pull/8).

WordPress CI obejmuje jakość źródeł, instalację dokładnych paczek ZIP,
działanie runtime i odtworzenie danych oraz próbę wydania z regresją.
Kontrole obejmują PHP, JS/CSS, zależności, sekrety, powtarzalność paczek
i przypadki celowych błędów potwierdzające blokowanie wadliwych zmian.

| Próba | Potwierdzony wynik | Ograniczenie dowodu |
| --- | --- | --- |
| Instalacja ZIP motywu 0.4.1 i formularza 0.3.2 | PASS | Instalacja testowa, nie produkcja |
| Kontakt: walidacja, antyspam, wysyłka i błędy | PASS | Kontrolowane skrzynki i transport testowy |
| Chromium/WebKit × desktop/tablet/telefon | 6/6 PASS | Nie zastępuje odbioru właściciela |
| Akceptacja funkcjonalna | 13/13 PASS | Dokładny kandydat CI, nie publiczne wydanie |
| Odtworzenie DB/uploads | PASS, 14 s w tej próbie | Nie jest gwarancją czasu odtworzenia rzeczywistej produkcji |
| Cofnięcie kodu | PASS, dane zachowane | Izolowany model wydania |
| TLS | Poprawny certyfikat akceptowany; błędna nazwa i niezaufany CA odrzucone | Nie potwierdza konfiguracji publicznego hosta |

Próba CI używała test-merge `bd3e4b4a6939dfa3b3c0160e8cb7c0f90c26fb7c`.
To nie jest merge do `main` ani dowód publikacji obrazu produkcyjnego.

## Identyfikacja paczek

Paczki z CI z ustalonym `SOURCE_DATE_EPOCH=1767225600`:

- Motyw 0.4.1 SHA-256:
  `2a921df6330cc45b2f53eaaf044b71c70ea7bf647cc1b1f601c5f83679fd238b`.
- Kontakt 0.3.2 SHA-256:
  `d0800517e14e399f0b603ad3077f64e01c95346d34ebaac62ef889c590db46d7`.

Inny timestamp archiwum może zmienić jego hash mimo identycznych plików.
Nie wolno mieszać lokalnych i CI-owych sum ani używać numeru wersji zamiast
identyfikatora faktycznie sprawdzonej paczki.

## Wygląd, dostępność i redaktor

Udokumentowano poprawę Kontaktu, logo i nawigacji, pięć szerokości formularza,
próbę Chrome z powiększeniem 200%, edycję Site Editor oraz pełny cykl bloga:
szkic, podgląd, planowanie, publikacja, aktualizacja i wycofanie.

Porównanie wydajności obejmowało 40 lokalnych próbek w ośmiu grupach.
Są to pomiary laboratoryjne, nie dane rzeczywistych użytkowników ani
zaakceptowane przez właściciela budżety. Automatyczne kontrole dostępności
nie zastępują odbioru z technologią asystującą i na rzeczywistym urządzeniu.

## Co nadal blokuje zamknięcie migracji

- Implementacja i weryfikacja nowego modelu wydań bez stagingu.
- Odbiór właściciela: Kontakt, treści, wygląd, dostępność i treści prawne.
- Uzgodnione budżety wydajności i ich ocena we właściwym środowisku.
- Potwierdzone wejścia i operatorzy produkcji, TLS, routing i poczta.
- Działające szyfrowane backupy poza hostem, harmonogram, retencja,
  alarmy oraz realna próba odtworzenia.
- Osobna zgoda na pierwszy cutover, weryfikacja po nim i stabilizacja.
- Dopiero potem zgoda na dokładny zakres wycofania legacy.

**Brak stagingu nie jest już brakującym wymaganiem.** Starszy Gate C pozostaje
historycznym raportem z poprzedniego modelu. Jego warunki trzeba uzgodnić
z nową decyzją, zachowując bramki jakości i operacyjne. Nie ogłoszono GO.

## Dowody szczegółowe

- [Regresja i dostępność](https://github.com/grzegorzrzeznikiewicz/company-site/blob/19a348dea7451b1b9780e336724731a9155321fe/docs/agent-workflows/wordpress-migration/GSWEB-27-regression.md).
- [Lokalne porównanie wydajności](https://github.com/grzegorzrzeznikiewicz/company-site/blob/19a348dea7451b1b9780e336724731a9155321fe/docs/agent-workflows/wordpress-migration/GSWEB-27-vitals-2026-09-06.md).
- [Historyczny Gate C](https://github.com/grzegorzrzeznikiewicz/company-site/blob/19a348dea7451b1b9780e336724731a9155321fe/docs/agent-workflows/wordpress-migration/GSWEB-28-gate-c.md).

CI przechowuje część artefaktów przez ograniczony czas. Odnośnik do przebiegu
nie zastępuje polityki długoterminowego przechowywania dowodów wydania.
