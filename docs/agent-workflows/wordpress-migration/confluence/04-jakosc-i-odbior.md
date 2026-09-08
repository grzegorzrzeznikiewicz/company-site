# Testy, audyt i odbiór migracji

Dokumentacja: 2026-09-08. Rozdzielamy historyczne wyniki CI z
2026-09-06 od nowych prób lokalnych. Aktualizacja tej strony nie oznacza
uruchomienia nowego CI ani wdrożenia produkcyjnego.

## Potwierdzone historyczne dowody CI

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

## Nowe próby lokalne — 2026-09-08

Przebudowa procesu bez stagingu odbywa się na `feature/GSWEB-9`, jako
niezacommitowane zmiany nad `87cab81a06057142463c82201e8cbabe7d2593a1`.
Poniższe wyniki nie zastępują czystego przebiegu CI dla nowego pipeline'u:

- Kontrole JS/CSS, PHPCS/WPCS i PHPStan zakończyły się sukcesem. Audyty
  Composer i dwóch zestawów zależności npm nie zgłosiły podatności.
- Motyw 0.4.1 i formularz 0.3.2 przeszły ponownie pełne cykle instalacji
  dokładnych ZIP-ów. Przed próbami porównano komplet plików i każdą sumę
  z bieżącymi źródłami; nie nadpisano ani nie rozpowszechniano paczek.
- Cykl ZIP motywu wykonał 34 udane testy przeglądarkowe w 19 grupach wyników.
  Zachowano artefakty i sprawdzono każdy plik wyniku, nie tylko komunikat
  zbiorczy. Testy kontaktu objęły również odrzucane dane i błędy transportu.
- Manifest, bezpieczny transport, producent obrazu i walidacja promocji
  przeszły niezależne przeglądy z poprawkami. Świeży zestaw jednostkowy
  na przypiętym Linuksie/Pythonie 3.12 zakończył się wynikiem 170/170,
  z ostrzeżeniami traktowanymi jako błędy. Przegląd transakcji hosta wykrył
  trzy przypadki odzyskiwania, które poprawiono i sprawdzono w ponownym
  niezależnym przeglądzie. Etapy 1–6 są zaakceptowane technicznie.
  Workflow przeszły także kontrolę rzeczywistego YAML i 10 błędnych wariantów
  uprawnień/zależności. Poprawiono historię ponowień legacy i wspólną kontrolę
  źródła. Niezależna recenzja poprawek końcowego przeglądu potwierdziła
  usunięcie wszystkich 11 usterek; w ich zakresie nie wykryto nowych
  problemów Critical/Important. Pełny CI i odbiór operacyjny pozostają otwarte.
- Dodatkowe kontrole źródeł Kontaktu, SEO i bezpieczeństwa oraz 15 wybranych
  kontraktów źródeł/granic motywu przeszły bez zmian paczek i podglądu.
  Statyczna kontrola połączeń testów nie jest nowym uruchomieniem przeglądarki
  ani pełnym przebiegiem CI. Ponownie zweryfikowano 120 sum źródeł i QA.

Jedna lokalna próba wydania użyła obrazu developerskiego
`sha256:0a0ac3a3392c275e14f261c4d929de0d49de482519c65ddf69117fa804513072`
w obu konsumentach, z lokalnym numerem próby `2/1`. Potwierdzono TLS,
kontrolowane SMTP i zachowanie konkretnych treści oraz mediów przez deploy
i rollback. Pierwszy zestaw prób poprzedzał poprawki przeglądu producenta.
Po nich oba rzeczywiste skrypty uruchomiono ponownie na tym samym obrazie,
tym razem z jawną bazą rollbacku 043beee6490664758bdbbff55d7a9cdf9156a398.
Oba zakończyły się kodem 0 i wygenerowały nowe zgodne potwierdzenia.

Świeży konsument regresji wykonał 6 testów Chromium/WebKit i 13 testów
akceptacyjnych, obejmujących menu, logo, Kontakt, blog, treści i role.
Sprawdzono zachowane pliki wyników obu grup oraz pozytywne i negatywne
próby TLS. Model produkcyjny potwierdził zachowanie wpisu o ID 11,
jego dokładnego tytułu/treści i sumy pliku po aktualizacji oraz po
rollbacku z celowo uszkodzonym PHP. Ostatnią parę prób wykonano po
zamrożeniu poprawek końcowego audytu, w nowych przestrzeniach zasobów.

Każdy rzeczywisty konsument wykrył zmianę tytułu, zmianę treści, usunięcie
wpisu, uszkodzenie pliku i jego usunięcie. Przed zapisaniem potwierdzenia
odtworzył wyłącznie własny rekord i plik oraz zweryfikował dokładny stan.
Model produkcyjny zachował tytuł/treść GSWEB29-production-e9efd92802dadd04
oraz SHA-256 pliku cdab1a72efe7fe37c2514af498debd3621af907bc2d4c334f3ad5ea083216a24.
Pięć nowych zrzutów Kontaktu było bajtowo identycznych z wcześniej
obejrzanymi zrzutami dla szerokości 320/390/767/768/1440. To lokalny test
układu, nie potwierdzenie dostarczalności produkcyjnej poczty.

W logach kontenerowych pozostają znane ostrzeżenia bootstrapu .htaccess,
zestawienia usług Compose i przeliczania zestawu certyfikatów testowych.
Są zachowane do oceny; udany kod wyjścia nie oznacza logu bez ostrzeżeń.

Próby kontenerowe na tym komputerze działały natywnie jako `linux/arm64`.
Wariant `linux/amd64` dwukrotnie zatrzymał się w emulacji QEMU przy starcie
obrazu bazowego Apache. Obraz developerski pozostaje niepublikowalny;
nie zmieniono wymaganej platformy wydania `linux/amd64`. Nowe CI na tej
platformie, wraz z jej próbą odzyskiwania, pozostają wymagane.

Zasoby jednorazowych prób zostały usunięte w ich własnych przestrzeniach;
oryginalne kontenery podglądu pozostały zdrowe, a `http://localhost:8090/`
odpowiadał HTTP 200 po weryfikacji. Nie uruchamiano destrukcyjnego resetu
podglądu ani nie zmieniano produkcji.

## Identyfikacja paczek

Paczki z CI z ustalonym `SOURCE_DATE_EPOCH=1767225600`:

- Motyw 0.4.1 SHA-256:
  `2a921df6330cc45b2f53eaaf044b71c70ea7bf647cc1b1f601c5f83679fd238b`.
- Kontakt 0.3.2 SHA-256:
  `d0800517e14e399f0b603ad3077f64e01c95346d34ebaac62ef889c590db46d7`.

Inny timestamp archiwum może zmienić jego hash mimo identycznych plików.
Nie wolno mieszać lokalnych i CI-owych sum ani używać numeru wersji zamiast
identyfikatora faktycznie sprawdzonej paczki.

Lokalne ZIP-y użyte w próbach z 2026-09-08 mają inne sumy niż powyższy
historyczny zestaw CI (ponowny odczyt SHA-256 po próbach):

- Motyw 0.4.1:
  `67caf7865fb19b0acdcef21e626c28116725eb55c52511501d6c6ee808747bef`.
- Kontakt 0.3.2:
  `7b150f168fce6053910d87ca81592c1175a9129e1b49ef6162fc13361ceb6b7e`.

Komplet plików tych ZIP-ów odpowiadał lokalnym źródłom. Nie utożsamiamy
lokalnych archiwów z artefaktami historycznego przebiegu CI.

## Wygląd, dostępność i redaktor

Udokumentowano poprawę Kontaktu, logo i nawigacji, pięć szerokości formularza,
próbę Chrome z powiększeniem 200%, edycję Site Editor oraz pełny cykl bloga:
szkic, podgląd, planowanie, publikacja, aktualizacja i wycofanie.

Porównanie wydajności obejmowało 40 lokalnych próbek w ośmiu grupach.
Są to pomiary laboratoryjne, nie dane rzeczywistych użytkowników ani
zaakceptowane przez właściciela budżety. Automatyczne kontrole dostępności
nie zastępują odbioru z technologią asystującą i na rzeczywistym urządzeniu.

## Co nadal blokuje zamknięcie migracji

- Pełny czysty CI na linux/amd64 i weryfikacja operacyjna nowego modelu
  wydań bez stagingu; implementacja lokalna i niezależny przegląd są zakończone.
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
