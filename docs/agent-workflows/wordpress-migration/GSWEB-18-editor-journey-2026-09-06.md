# GSWEB-18 — próba pracy redaktora, 2026-09-06

## Wynik i granice

**Ścieżka szkic → podgląd → zaplanowana publikacja → aktualizacja → wycofanie
do szkicu przeszła.** Treść, wybór daty, zapisy i wycofanie wykonał kontroler
przez interfejs WordPressa w Chrome Gama Software, jako użytkownik o roli
`editor`, bez bezpośredniego sterowania rekordem przez API lub skrypt.
Samą publikację wykonała kolejka zadań Core po nadejściu terminu. To uzupełnienie
brakującego scenariusza z [audytu epiki](GSWEB-8-acceptance-audit.md), a nie
ponowny odbiór całego GSWEB-18 lub epiki.

Próba jest lokalna, na dokładnym ZIP-ie. Nie potwierdza publicznego stagingu,
konfiguracji jego zegara zadań, produkcyjnego SEO, technologii wspomagającej
ani samodzielnego odbioru przez właściciela. Opublikowano tylko jednorazowy
artykuł testowy w odizolowanej instalacji. Kod aplikacji nie został zmieniony.

## Tożsamość instalacji

- Źródła aplikacji: opublikowany `1398f41`; lokalny HEAD na początku próby
  `d9486d3` dodaje tylko QA/dokumentację, bez zmian plików motywu i formularza.
- WordPress 7.1, motyw 0.4.1, kontakt 0.3.2; przypięte obrazy z
  `wordpress/tests/theme-package-compose.yaml`. Zainstalowano paczki, bez
  montowania źródeł motywu. Nie był to pełny obraz kandydata wydania z jego
  pozostałymi wtyczkami.
- Lokalny ZIP motywu SHA-256:
  `67caf7865fb19b0acdcef21e626c28116725eb55c52511501d6c6ee808747bef`.
- Lokalny ZIP formularza SHA-256:
  `7b150f168fce6053910d87ca81592c1175a9129e1b49ef6162fc13361ceb6b7e`.
  To archiwa z czasem commita. ZIP-y CI używają stałej daty archiwizacji,
  więc mimo identycznych plików mają inne metadane i sumy, opisane w
  [checkpointcie GSWEB-13](GSWEB-13-native-zoom-2026-09-06.md).
- Projekt: `gama-gsweb18-editor-20260906-gukmd9`; adres wyłącznie loopback
  `http://127.0.0.1:18098`. Baza w sieci wewnętrznej, `blog_public=0`.
- Redaktor `journey-editor`, ID 2, rola `editor`; artykuł ID 9, autor ID 2.
  Język panelu angielski, strefa witryny `Europe/Warsaw`.
- Skrypty, surowe stany, HTML, logi i sześć zrzutów:
  `/tmp/gama-editor-1398f41.gUKmD9/`. Wybrane nieprzetworzone JPEG-i są
  wersjonowane w [instrukcji bloga](GSWEB-28-editor-blog-guide.md).

## Przebieg i sprawdzenia

| Krok           | Działanie redaktora / obserwacja                                      | Wynik                                                                                                                                       |
| -------------- | --------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| Szkic          | Posts → Add Post; tytuł i akapit; Save draft                          | „Draft saved”, status `draft`; anonimowy adres wpisu HTTP 404.                                                                              |
| Podgląd        | View → Preview in new tab                                             | Tytuł, treść, logo, menu i szablon single widoczne pod `?p=9&preview=true`; wpis nie występuje jeszcze na blogu.                            |
| Planowanie     | Publish → data 6 września, 1:36 PM; Schedule i potwierdzenie Schedule | „Post scheduled”, status `future`, data lokalna `2026-09-06 13:36:00`, GMT `11:36:00`; anonimowo nadal 404.                                 |
| Przed terminem | Zwykły zegar uruchamia tylko zaległe zadania                          | Do `11:35:54Z` nie uruchomił publikacji; blog pokazuje poprawny pusty stan „W budowie”.                                                     |
| Publikacja     | Bez dalszej ingerencji w wpis                                         | O `11:36:04Z` wykonano `publish_future_post` dla ID 9; status `publish`, anonimowo HTTP 200, artykuł na `/blog/` i w sekcji bloga homepage. |
| Aktualizacja   | Zmiana akapitu w edytorze, Save                                       | „Post updated”; nowa treść na publicznym adresie oraz w zapisanym rekordzie tego samego autora.                                             |
| Wycofanie      | Post → Status → Draft, zamknięcie panelu i Save                       | „Post reverted to draft”; ten sam ID i nowa treść zachowane, anonimowo 404, brak wpisu na blogu i homepage.                                 |

Zegar testowy uruchamiał co około 10 sekund udokumentowane
[`wp cron event run --due-now`](https://github.com/wp-cli/handbook/blob/main/commands/cron/event/run.md).
Przed terminem odczytano zdarzenie `publish_future_post`, `args:[9]`,
`next_run_gmt:2026-09-06 11:36:00`. Nie zmieniano dat ani statusu wpisu
poleceniami; nie wykonano przyszłego hooka przed terminem. W tej instalacji
`DISABLE_WP_CRON=true`, więc świadomie zapewniono osobny zegar testowy.
**Działający harmonogram na docelowym hoście nadal wymaga wdrożenia i próby.**

Odczyty WP-CLI i anonimowe HTTP były wyłącznie kontrolą skutków UI. Asercje
`jq -e` potwierdziły wspólne ID/autor oraz kolejność `draft/future/publish`,
niezmienioną zaplanowaną datę GMT i zachowanie treści po wycofaniu. Zachowane
HTML-e potwierdzają pojawienie się i zniknięcie linku do wpisu z obu list.

## Diagnostyka i porządkowanie

Pierwsze uruchomienie skryptu przygotowania zakończyło się błędem **ostatniego
odczytu metadanych**: CLI nie otrzymało `WORDPRESS_CONFIG_EXTRA`, a odczyt
używał niezdefiniowanego `DISABLE_WP_CRON`. Instalacja i konto były już
utworzone. Uzupełniono konfigurację wyłącznie testowego CLI, zabezpieczono
odczyt `defined()` i ponowiono pomiar: poprawne URL-e, strefa, wyłączony
automatyczny cron, zero opublikowanych wpisów. Nie odtwarzano całej poprawionej
instalacji drugi raz. Pełny powyższy scenariusz wykonano po tej korekcie.

Przechwycony log edytora: **0 błędów, 2 ostrzeżenia**, dotyczące
niezużytych preloadów `api-fetch` oraz dodania
`global-styles-css-custom-properties-inline-css` do iframe. Ostrzeżenia
pochodzą z plików Core JS; ich przyczyny nie rozstrzygnięto w tej próbie.
Nie są tu wyciszane ani przedstawiane jako czysty log.
Log PHP zachował jedno ostrzeżenie `wp_update_plugins()` z inicjalizacji
o nieudanym połączeniu z WordPress.org w środowisku offline. Błąd odczytu
CLI jest zachowany w `setup.log`, nie przypisany do edycji wpisu.

Po potwierdzeniu publikacji zatrzymano dokładny proces zegara testowego.
Zamknięto dwie karty testowe. `cleanup.sh` usunął tylko kontenery, trzy wolumeny
oraz dwie sieci powyższego projektu; kontrola ich braku przeszła. Dane testowe
można odtworzyć skryptem przygotowania i powtórzeniem scenariusza. Podgląd
właściciela `http://localhost:8090/` nadal odpowiadał HTTP 200.

## Sumy dowodów

SHA-256, pliki w powyższym katalogu tymczasowym:

| Plik                     | SHA-256                                                            |
| ------------------------ | ------------------------------------------------------------------ |
| `draft-state.json`       | `040628857431bb93aa4317c62e222a582c57b124d900b3c36b24985417844a80` |
| `scheduled-state.json`   | `565bf66b920a700ca6b84ce68d2772edc8c69896d1da8a3c8c56b4776f64e916` |
| `scheduled-event.json`   | `6e846d306230ec338d25fd8d32bdb2c65087f41aad8505eeb15a335458db951c` |
| `published-state.json`   | `6e1594c621b085724d567673b0389e72e705ae32d9930a3d3489c01bf1f51056` |
| `updated-state.json`     | `df64c312bd73d81cb21e88ab8b06b42f051038ec796f127c7445d2110b81bf6b` |
| `withdrawn-state.json`   | `0c0cafcf2198f53313950143ce72df1de166061cfa4ce458b0f84051f339ba28` |
| `scheduler.log`          | `69d1bfa528192b118396971917eccf2bf9a7989611a612b4343339ca30f71278` |
| `02-preview.jpg`         | `9209ee238a3b7bf911e3f25de80d09f7a69f909927426618afc9d50216b9866d` |
| `03-scheduled.jpg`       | `220b1332de395e495a93047fb383b6886d804dff8260a2a3c5da028a39459029` |
| `05-published-blog.jpg`  | `ccc838b2c5d9b9f0afbb5272118e448dd40f5c32763da28ccbf01562ce24a3ad` |
| `06-withdrawn-draft.jpg` | `63bca06f16ecf34eadacd6a5fd6211e1053d6ce609ecec39db79d5eb4e463a1e` |
