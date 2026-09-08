# GSWEB — automatyczne wydania WordPressa bez stagingu

Data: 2026-09-07. Zakres: GSWEB-25, 26, 28 i 29, z zachowaniem granicy GSWEB-30.

**Status: specyfikacja zaakceptowana przez właściciela 2026-09-07.** Odpowiedź
„Tak” na pytanie o zatwierdzenie tej specyfikacji odblokowuje plan i implementację.
Właściciel wcześniej zaakceptował model lokalne + produkcja oraz automatyczne
kolejne wydania po zatwierdzonym PR. Poniższe szczegóły techniczne nie są jeszcze
w całości zaimplementowane ani wdrożone.
Nie wykonano zmiany uprawnień, merge, publikacji obrazu ani cutoveru.

Aktualne zasady workspace: praca w rzeczywistym katalogu projektu, na obecnej
gałęzi `feature/GSWEB-9`, bez dodatkowych worktree, commitów i pushowania.
Zmiany implementacji oraz dowody pozostają lokalne i niezacommitowane.

## 1. Cel i granice

Po zatwierdzeniu PR i scaleniu do `main` dokładna, sprawdzona wersja WordPressa
ma być automatycznie wydawana na `https://gama-software.com`. Proces zachowuje
treści i uploads, wykonuje backup, weryfikuje wynik i ma przetestowaną drogę
wycofania. Nie wymaga ręcznego zatwierdzania każdego standardowego wydania.

Istnieją tylko środowisko lokalne oraz produkcyjne. Próby na jednorazowych
runnerach CI lub lokalnych instalacjach testowych są dozwolone. Nie tworzymy
zdalnego stagingu ani dodatkowej instalacji kandydata na serwerze produkcyjnym.

Pierwsze przełączenie React/Symfony na WordPress pozostaje osobną operacją,
wymagającą świeżej zgody na konkretną wersję, operatorów i okno. Usunięcie
starego stosu oraz odtworzenie produkcyjnych danych wymagają odrębnych decyzji.
Migracje nieodwracalne lub niezgodne z poprzednim kodem nie są standardowym
automatycznym wydaniem.

## 2. Stan wejściowy i luka

Kod sprawdzono w commicie `19a348dea7451b1b9780e336724731a9155321fe`:

| Obszar | Obecnie | Docelowo |
| --- | --- | --- |
| WordPress CI | PR oraz push do main; cztery bramki | Zachowane bramki oraz jeden kandydat obrazu przekazywany dalej |
| Budowa obrazu do publikacji | Oddzielna budowa w workflow stagingowym | Publikacja obrazu z CI bez ponownej budowy |
| Produkcja | Ręczny dispatch z `staging_run_id` | Automatyczny tryb standardowy i osobny ręczny pierwszy cutover |
| Próba kandydata | Oddzielna instalacja na hoście produkcyjnym | Jednorazowe próby wyłącznie lokalnie/CI |
| Legacy CI/CD | Może wdrażać po zielonym CI na main | Jawnie sterowany tryb, bez konfliktu z WordPressem |

Obecne próby wydania samodzielnie budują kandydatów z oznaczeniami testowymi.
Dlatego samo zastąpienie wyzwalacza workflow nie spełni zasady „wdrażamy
dokładnie przetestowany obraz”. Trzeba zmienić producenta i konsumentów
artefaktu oraz ich testy.

## 3. Rozważone podejścia

1. **Rekomendowane: CI tworzy i testuje obraz, osobny zaufany workflow go
   publikuje i wdraża.** Zachowuje rozdział testów bez sekretów od uprawnień
   rejestru i produkcji. Wymaga ścisłego sprawdzenia pochodzenia przebiegu.
2. Jeden rozbudowany workflow testów, publikacji i produkcji. Upraszcza
   przekazanie artefaktu, ale miesza obsługę niezaufanych PR z uprawnieniami
   publikacji i utrudnia oddzielenie pierwszego cutoveru.
3. Ponowna budowa po zielonym CI i bezpośredni deploy. Odrzucone: zgodny commit
   nie jest sam w sobie dowodem tożsamości obrazu z testami.

Dalsze sekcje opisują podejście pierwsze.

## 4. Jeden obraz kandydata

`WordPress Quality Gates` zachowuje dotychczasowe cztery nazwane bramki.
Etap regresji wydania buduje kandydata raz z dokładnego checkoutu przebiegu
i przypiętych wejść. Budowa ma produkcyjne oznaczenie `release`, nie
`--test-dirty`; pliki QA i wygenerowane dane nie wchodzą do kontekstu obrazu.

Obie próby: regresja/akceptacja z rollbackiem i izolowany model produkcyjny
z szyfrowanym SMTP, przyjmują ten sam jawny identyfikator obrazu. Nie budują
własnego kandydata i nie modyfikują jego warstw. Osobno mogą przygotować obraz
poprzedniej wersji oraz efemeryczne bazy, pocztę i dane testowe.

Po udanych próbach CI zapisuje archiwum obrazu oraz manifest. Wydanie produkcji
może je skonsumować dopiero po sukcesie całego przebiegu, w tym pozostałych
bramek. Instalacje ZIP motywu i formularza nadal mają osobne dowody.

Wersja początkowa pipeline'u przyjmuje jedną platformę `linux/amd64`, zgodną
z wybranym runnerem wydaniowym. Przed uruchomieniem trzeba potwierdzić zgodność
hosta produkcyjnego; inna architektura wymaga odpowiedniego kandydata i prób,
nie emulacji ani niejawnego wyboru innego wariantu obrazu na produkcji.

### Kontrakt manifestu

Manifest jest danymi JSON o zamkniętym schemacie, nie wykonywalnym skryptem.
Zawiera wersję schematu, repozytorium, pełny Git SHA, ścieżkę/identyfikator
workflow, ID i numer próby CI, zdarzenie oraz ref źródła, platformę, image ID,
SHA-256 archiwum, inwentarz wersji pakietów oraz identyfikatory dowodów testów.
Dowody regresji wskazują ten sam image ID. Archiwum nie zawiera danych
runtime, sekretów ani checkoutu służącego do uruchamiania poleceń.

Nazwa artefaktu wiąże SHA, ID przebiegu i numer próby. Konsument pobiera go
z konkretnego przebiegu; nie wyszukuje „ostatniego zielonego”. Brak, nadmiar,
niezgodność schematu, sumy lub pochodzenia kończy promocję błędem. Pełne
ponowienie przebiegu tworzy nową tożsamość dowodu; mieszanie artefaktów
z różnych prób nie jest dopuszczalnym obejściem błędu.

Rozpakowanie transportu dopuszcza tylko oczekiwane pliki i limit rozmiaru;
odrzuca ścieżki absolutne, wyjście poza katalog, symlinki i duplikaty nazw.
Sumę archiwum sprawdzamy przed jego wczytaniem przez silnik kontenerów.
Żaden plik z artefaktu nie jest uruchamiany jako narzędzie walidujące.

## 5. Zaufana promocja

Automatyczny punkt wejścia to zakończenie `WordPress Quality Gates`.
Warunkiem działania jest sukces źródła, zdarzenie `push`, gałąź `main`,
właściwe repozytorium i zgodne metadane pobrane z API dla ID przebiegu.
Niezaufany PR, fork, inna gałąź, sam tag, brak metadanych lub błąd API
nie uruchamiają publikacji ani połączenia produkcyjnego.

Trzeba sprawdzać to przed pobraniem artefaktu do użycia z uprawnieniami.
`workflow_run` może uzyskać sekrety i token zapisu niezależnie od uprawnień
poprzednika, a jego definicja musi istnieć na gałęzi domyślnej. To wymaga
jawnej granicy zaufania, nie tylko porównania nazwy workflow.
[Dokumentacja zdarzeń GitHub](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run).

Walidator ma uprawnienia odczytu. Dopiero osobny etap publikacji uzyskuje
`packages: write`; nie otrzymuje sekretów SSH ani poczty. Wczytuje sprawdzone
archiwum, weryfikuje image ID, platformę, etykietę rewizji i oznaczenie release,
a następnie publikuje je do wyznaczonego repozytorium GHCR bez Docker build.

Po publikacji zapisuje digest rejestru i ponownie pobiera obraz dokładnie
po tym digescie. Image ID, platforma, rewizja i warstwy muszą odpowiadać
kandydatowi z CI. Metadane promocji wiążą digest ze źródłowym przebiegiem,
artefaktem i sumą archiwum. Tag jest etykietą pomocniczą, nie wejściem deployu.

Podczas pierwszego uruchomienia publikacja obrazu jest objęta osobną zgodą
na wskazany artefakt. Później mieści się w zatwierdzonym procesie standardowych
wydań. Tryb wyłączony nie publikuje obrazów w GHCR.

## 6. Zatwierdzony merge a automatyczny deploy

`main` ma wymagać PR, recenzji oraz określonych bramek WordPressa; do zakończenia
migracji pozostają także wymagane kontrole legacy. Nazwy nie mogą oznaczać
pustej listy checks. Niedozwolony jest bezpośredni push lub pominięcie kontroli
w zwykłym procesie. Rejestr wydania wiąże commit ze scalonym, zatwierdzonym PR.

Ochrona gałęzi i uprawnienia osób mogących ją zmieniać stanowią warunek
operacyjnego uruchomienia, a nie rzecz domyślnie udowodnioną przez YAML.
Automatyczny tryb odmawia promocji rewizji bez dowodu zatwierdzonego PR.

Standardowe wydanie korzysta z sekretów środowiska produkcyjnego ograniczonego
do `main`, bez dodatkowej ręcznej bramki redaktora środowiska. Pierwszy cutover
i ręczne operacje odzyskiwania mają własną jawną autoryzację. Środowisko GitHub
to granica uprawnień, nie dodatkowy serwer stagingowy.
[Dokumentacja środowisk GitHub](https://docs.github.com/en/actions/concepts/workflows-and-actions/deployment-environments).

Konfiguracja tych reguł wymaga uzgodnienia z właścicielem i weryfikacji
ich rzeczywistego działania. Ta specyfikacja nie zmienia istniejących reguł.

## 7. Wyłączony tryb początkowy i przełączenie legacy

Wspólny przełącznik wdrożeń ma trzy jawne wartości: `off`, `legacy`,
`wordpress`. Brak lub niepoprawna wartość oznacza odmowę mutacji.
Nie wyciągamy trybu z dostępności sekretów ani z istnienia kontenera.

- `off`: brak automatycznej publikacji/deployu; używany podczas przygotowania
  integracji. Istniejąca publiczna strona nadal działa.
- `legacy`: może działać tylko uzgodniony deployment starego stosu.
- `wordpress`: standardowy pipeline WordPressa jest automatyczny, a legacy
  nie może wdrażać niezależnie po swoim CI.

Pierwszy cutover jest osobnym, ręcznie autoryzowanym wejściem z trybu `off`.
Przyjmuje dokładny udany przebieg CI z `main`, zaakceptowany artefakt i okno.
Instaluje jedyny docelowy namespace WordPressa, początkowo za istniejącym
routingiem legacy. Nie tworzy drugiej instalacji kandydata. Po kontroli
lokalnej, poczty i backupu przełącza routing oraz weryfikuje publiczny HTTPS.

Zanim pierwszy cutover zmieni host lub routing, musi istnieć zweryfikowany
backup danych legacy i zapis konfiguracji powrotu. Dane przygotowanego
WordPressa są kopiowane przed przełączeniem ruchu. Nie wymagamy backupu
nieistniejącej jeszcze instalacji WP i nie traktujemy jego kopii jako
zastępstwa kopii działającego starego stosu.

Po udanym pierwszym przełączeniu powstaje chroniony zapis na hoście o przyjętej
wersji i gotowości instalacji. Dopiero potwierdzone uruchomienie trybu
`wordpress` pozwala na kolejne automatyczne wydania. Tryb ten wymaga istniejącej,
zdrowej instalacji i tego zapisu; nigdy nie wykonuje pierwszej migracji sam.

Przed merge trzeba wyłączyć konflikt z obecnym legacy workflow. Zmiana flagi,
uprawnień, rejestracja workflow, pierwsza publikacja i cutover są częścią
uzgodnionego uruchomienia, nie skutkiem ubocznym pisania dokumentacji.

## 8. Sekcja krytyczna wdrożenia

Publikacja obrazu nie zmienia hosta. Pierwszy cutover, standardowy deploy
i rollback korzystają natomiast ze wspólnej grupy współbieżności produkcji,
bez anulowania działającej operacji. `queue: max` zachowuje więcej oczekujących
przebiegów, ale kolejność wynika z momentu wejścia do kolejki, nie z daty merge.
Sama kolejka nie gwarantuje porządku wersji.
[Dokumentacja współbieżności GitHub](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency).

Na hoście dodatkowa blokada chroni mutacje przed innym operatorem lub retry.
Po jej uzyskaniu pipeline ponownie sprawdza tryb, zdrowie, brak niezakończonej
operacji i bieżący zatwierdzony SHA `main`. Starszy kandydat jest jawnie
oznaczony jako pominięty, a nie jako wdrożony. Nie przerywamy rozpoczętej
sekcji krytycznej, gdy w międzyczasie pojawi się nowy merge.

Przed zmianą zachowywane są poprzedni digest, identyfikatory trwałych zasobów,
odniesienie do backupu i zapis rozpoczętej operacji. Backup ma potwierdzony
cel off-host, sumy i aktualny dowód odtworzenia. Brak tych warunków blokuje
zmianę działającej usługi. Pliki i narzędzia kontrolne pozostają root-owned,
bez symlinków i zapisu dla nieuprawnionych użytkowników.

Wdrożenie używa niezmiennego digestu, zachowuje bazę i uploads, nie importuje
bazy z lokalnego środowiska i nie resetuje treści redaktora. Aktualny model
Compose może wymagać krótkiego zatrzymania WordPressa; ta specyfikacja nie
obiecuje zero-downtime i nie dodaje infrastruktury blue/green.

## 9. Kontrola wyniku i odzyskiwanie

Po zmianie sprawdzane są zgodność obrazu, zdrowie procesu, publiczny HTTPS,
główna strona, blog, logowanie, logo/nawigacja, formularz i indeksowalność.
Kontrolowana próba poczty używa wcześniej uzgodnionej skrzynki. Sukces SMTP
oznacza przyjęcie do transportu, nie potwierdzenie odbioru w skrzynce; realna
dostarczalność jest osobnym dowodem pierwszego odbioru i monitorowania.

Niepowodzenie po rozpoczęciu zmiany wywołuje kontrolowane odzyskiwanie:

- Przy pierwszym cutoverze wraca zachowany routing legacy, bez usuwania danych WP.
- Przy standardowym wydaniu wraca poprzedni sprawdzony obraz WordPressa,
  z bieżącymi DB/uploads. Nie ma stałej zależności od React/Symfony.
- Automatyczny rollback nie wymaga zdrowia wadliwego nowego procesu PHP ani
  ponownego backupu jako warunku przywrócenia kodu. Używa zapisu przed zmianą;
  nie odtwarza bazy i nie usuwa danych.

Po udanym odzyskaniu pipeline potwierdza publiczny stan, zachowuje pierwotny
wynik failed i blokuje dalsze automatyczne mutacje do rozliczenia incydentu.
Nieudane odzyskanie wymaga operatora i pozostaje alarmem, nie sukcesem.

Retry jest idempotentny względem ID operacji, SHA i digestu. Duplikat nie
wdraża ponownie bez potrzeby. Stan po zerwanym SSH, timeout lub przerwaniu
runnera wymaga odczytu dziennika na hoście; brak odpowiedzi nie jest dowodem,
że operacja nie wystartowała. Nie zakładamy, że EXIT trap naprawi utratę hosta
lub twarde zatrzymanie procesu. Nierozliczony stan blokuje kolejne mutacje.

Odtworzenie danych jest osobną, zatwierdzaną procedurą w nowym namespace.
Zmiany schematu niezgodne z poprzednim kodem nie przechodzą standardowej
bramki rollbacku; wymagają odrębnego planu i zgody na ryzyko danych.

## 10. Zakres implementacji i testów

Zmiany obejmą producenta artefaktu w `wordpress-ci.yml`, konsumentów obrazu
w próbach wydania, workflow produkcji/rollbacku, granice narzędzi wdrożeniowych
i przełącznik konfliktującego `deploy.yml`. Zdalny workflow stagingowy zostanie
wycofany z procesu. Nie usuwamy runtime React/Symfony ani jego danych.
Nazwy historycznych fixture'ów można zachować tylko z jednoznacznym opisem,
że chodzi o jednorazowe próby, a nie wymagane środowisko stagingowe.

Wymagane dowody przed uznaniem implementacji za gotową:

1. Jeden kandydat: oba realne scenariusze testują ten sam image ID; publikacja
   bez build; po pobraniu digestu tożsamość obrazu nadal się zgadza.
2. Walidacja pochodzenia odrzuca PR/fork, inny ref/repo/SHA/workflow, nieudany
   run, błędną próbę, brak artefaktu, zmieniony manifest i uszkodzone archiwum.
3. Zdarzenia niedozwolone i tryb `off` nie wywołują rejestru ani SSH.
4. Brak pierwszego odbioru lub częściowo istniejąca instalacja nie powodują
   automatycznego bootstrapu/cutoveru.
5. Wadliwy backup, źródło mountu, uprawnienia, symlink lub niezgodna platforma
   blokują zmianę przed zatrzymaniem działającego WordPressa.
6. Prawdziwe kontenery zachowują konkretne ID/tytuł/treść i hash mediów po
   deployu oraz rollbacku; testy negatywne wykrywają ich utratę lub zmianę.
7. Błąd health/publicznego sprawdzenia uruchamia właściwy rodzaj odzyskiwania;
   błąd nowego PHP nie blokuje cofnięcia kodu. Pierwotny wynik pozostaje failed.
8. Równoległe żądania, starszy SHA, duplikat, retry, sygnał i utrata odpowiedzi
   nie prowadzą do podwójnej mutacji ani samowolnego uznania sukcesu.
9. Legacy i WordPress nie wdrażają jednocześnie. Automatyczny WordPress działa
   po pierwszym odbiorze bez dodatkowego ręcznego kliknięcia każdej wersji.
10. Zachowane są wszystkie dotychczasowe bramki, regresja przeglądarek,
    testy Kontaktu/SEO/ról i kontrola odtworzenia. Nowy pełny Linux CI oraz
    niezależny przegląd dotyczą dokładnej wersji zmienionego pipeline'u.

Testy mutujące stały lokalny projekt nie mogą działać na komputerze właściciela
przy jego podglądzie. Wykorzystują oddzielny runner/daemon lub rzeczywiście
unikalne, sprawdzone namespace'y i usuwają wyłącznie własne zasoby.

## 11. Dokumentacja, odbiór i prace operacyjne

Należy zsynchronizować wymagania GSWEB-25/26/28/29, indeks migracji,
Gate C i dokumentację Confluence. Starsze wyniki zachowują swój commit
i datę. Nie są dowodem działania nowej automatyzacji.

Do rzeczywistego pierwszego uruchomienia pozostają: potwierdzony host,
architektura i dostęp, operatorzy, produkcyjne TLS/routing/SMTP, odbiorca próby,
szyfrowany backup off-host z retencją i alarmami, próba odtworzenia, odbiór
treści/prawa/dostępności, budżety wydajności, okno, stabilizacja i uprawnienie
do rollbacku. To jawne warunki uruchomienia, nie domyślne konfiguracje.

Nie prosimy ponownie o host stagingowy. Brak zdalnego stagingu nie jest
blokadą nowego modelu. GSWEB-30 pozostaje za stabilizacją i osobną zgodą
na dokładny inwentarz usuwanego starego stosu.

## 12. Przegląd specyfikacji

Sprawdzono rozdzielenie zaakceptowanej polityki, projektowanej implementacji
i faktycznego wdrożenia. Pierwszy cutover jest oddzielony od standardowych
wydań; powrót do legacy nie jest trwałą zależnością WordPressa. Brak stagingu
nie jest zastąpiony drugim środowiskiem na produkcji. Tożsamość artefaktu,
pochodzenie CI, ochrona danych i nierozliczone błędy mają jawne warunki odmowy.

Następny krok po przeglądzie właściciela: szczegółowy plan implementacji
z kontraktami RED/GREEN i niezależnymi punktami odbioru.
