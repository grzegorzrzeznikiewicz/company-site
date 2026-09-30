# GSWEB-28 — lokalna próba Site Editor, 2026-09-06

## Wynik i granice

Kontroler wykonał przez UI Chrome Gama Software jako redaktor: zmianę Hero
i tekstu/linku CTA, dodanie i usunięcie pojedynczej karty usługi, zapis menu
oraz stopki. Zapisane zmiany potwierdzono na stronie głównej i blogu.
Powstała [ilustrowana instrukcja](GSWEB-28-editor-site-guide.md).

To próba **pełnego lokalnego obrazu kandydata**, nie publiczny staging,
samodzielny odbiór właściciela ani zakończenie całego GSWEB-28. Nie wykonywano
w tym przebiegu wysyłki formularza, publikacji wpisu, uploadu mediów, pełnej
edycji modułów, testu technologii wspomagającej ani zmian infrastruktury.
Osobna [próba bloga](GSWEB-18-editor-journey-2026-09-06.md) ma własną tożsamość
instalacji i nie jest przedstawiana jako część tego samego przebiegu.

## Tożsamość

- Kandydat `sha256:60f33f8e680c794ba106831471a18d1da894cd058e7dd6ff8f31b24e5cec53e9`,
  etykieta rewizji `d9486d319fbe69d35d5e4f2f191f27253b537541`.
  Brak zmian motywu, wtyczek i konfiguracji wdrożenia między tą rewizją
  a opublikowanym na początku próby `177afe9` potwierdzono przez Git.
  Nie przypisujemy starszego obrazu do nowszego SHA dokumentacji/testów.
- WordPress 7.1, motyw 0.4.1 i kontakt 0.3.2, z pozostałymi wtyczkami obrazu
  wydania. Kod aplikacji bez montowania źródeł z worktree.
- Dokładny projekt `gama-wp-staging-guide-20260906-ryacvr`, loopback
  `http://127.0.0.1:18099/`; oddzielna baza, Core, uploads, sieć i Mailpit.
  `noindex` zachowany, odbiorcy testowi `example.test`.
- Redaktor `guide-editor`, ID 2, rola `editor`.
  Odczyt uprawnień: `edit_theme_options=true`, `activate_plugins=false`,
  `manage_options=false`, `create_users=false`.
- Chrome 152 na macOS, profil `gama-software.com`, angielski panel WordPressa.
  Zrzuty bez retuszu; Mobile to podgląd edytora, nie fizyczny telefon.
- Surowe pliki lokalne: `/tmp/gama-site-editor-177afe9.RYaCVr/`.
  Instalacja uruchomiona o 12:43 UTC; udokumentowane czynności UI około
  12:47–13:02 UTC. Praca była przeplatana obsługą CI, więc nie jest to
  benchmark czasu migracji lub edycji.

## Rzeczywisty przebieg

| Krok            | Działanie UI i wynik                                                                                                         | Kontrola                                                                                              |
| --------------- | ---------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Wejście         | Dashboard → Appearance → Editor → Templates → Front Page → Get started                                                       | Pasek Front Page · Template, konto guide-editor; bez paneli administracyjnych Plugins/Users/Settings. |
| Hero/CTA        | Nagłówek „Gama Software — próba redakcji”; tekst przycisku „Porozmawiajmy — próba”; Edit link → `/#contact` → Apply → Save   | „Template updated”, Save nieaktywny; anonimowy HTML `02-saved-home.html`.                             |
| Dodanie usługi  | List View → services → Group → Grid → pojedynczy Group → Duplicate; tytuł „Usługa testowa — instrukcja”; Save                | Kopia w anonimowym `04-added-card.html`.                                                              |
| Usunięcie kopii | Zaznaczenie Group testowej kopii → Delete → Save                                                                             | Kopia nieobecna, trzy oryginalne usługi zachowane w końcowym HTML.                                    |
| Menu            | Header → Edit navigation → Usługi → TEXT „Oferta — próba”, adres bez zmiany `/#services`; Save → Header i Header menu → Save | „Site updated”; nowa etykieta i właściwy link na `/` oraz `/blog/`.                                   |
| Stopka          | Footer → Paragraph, tekst „© 2026 Gama Software. Próba instrukcji redaktora.”; Save → Footer → Save                         | „Site updated”; wspólny tekst na `/` oraz `/blog/`.                                                   |
| Wąski podgląd   | View → Mobile, następnie przywrócone Desktop                                                                                 | Zrzut `09-mobile-preview.jpg`; bez zmiany natywnego zoomu lub wymiarów urządzenia.                    |
| CTA na stronie  | Rzeczywiste kliknięcie zmienionego przycisku                                                                                 | URL `/#contact`, widoczne cztery pola formularza i Wyślij wiadomość; bez wysyłki.                     |
| Blog            | Kliknięcie Blog w menu                                                                                                       | URL `/blog/`, nagłówek Blog, wspólne nowe menu i stopka.                                              |

Konto i instalację przygotowano skryptem, ale wszystkie powyższe zmiany treści
wykonano przez interfejs, bez bezpośredniego zapisu WP-CLI/REST/SQL/store.
CLI i anonimowe HTTP służyły wyłącznie do odczytu efektów. `verify-evidence.mjs`
sprawdził 12 asercji, wynik **PASS**: rolę/uprawnienia, H1, link/tekst CTA,
pojawienie się i zniknięcie testowej karty, zachowanie oryginalnych usług,
menu/stopkę/noindex na obu adresach i rzeczywisty formularz. Końcowe żądania
HTTP do strony głównej i bloga zakończyły się poprawnie.

Zachowane AX, HTML, JPEG i odczyty potwierdzają obserwowane działania;
nie stanowią kompletnego, niezależnego śladu każdej akcji. Pierwszy plik
`01-hero-cta.ax.txt` jest różnicą drzewa, a nie pełnym snapshotem.

## Diagnostyka i porządkowanie

Początkowy widok edytora dotyczył treści Home, nie Front Page; przejście przez
Templates otworzyło właściwy szablon. Próba znalezienia pola TEXT przez locator
nie znalazła elementu; po odczycie aktualnego drzewa użyto dostępnego pola UI.
Nie było z tego powodu dodatkowego zapisu ani obejścia uprawnień.

Zachowany `wordpress.log` zawiera cztery HTTP 403 dla odczytu
`/wp-json/wp/v2/settings?_locale=user` z edytora. Odczyt `manage_options=false`
jest z nimi zgodny, ale nie ustalono tu całej przyczyny żądań Core. Nie
poszerzano uprawnień i nie wyciszano odmów. Log ma też startowe komunikaty
Apache o niewskazanym ServerName; bootstrap ostrzegł o konfiguracji potrzebnej
do regeneracji `.htaccess`. Zrzut błędów/ostrzeżeń przeglądarki wykonany po
ponownym podłączeniu sesji ma puste listy dla obu kart — **nie** dowodzi braku
wcześniejszych komunikatów przez cały przebieg.

Kontakt w Site Editor wyświetlał tekst zastępczy, a Content opis bloku Core;
na rzeczywistej stronie formularz był obecny. Instrukcja wyjaśnia różnicę,
bez przedstawiania jej jako testu dostarczania poczty.

Po zakończeniu `cleanup.sh` usunął wyłącznie cztery kontenery, trzy wolumeny
i jedną sieć dokładnego projektu testowego. Zapytania po etykietach Compose
potwierdziły brak jego zasobów. Dane testowe można odtworzyć przygotowaniem
instalacji i powtórzeniem scenariusza; nie wykonano backupu tej jednorazowej
edycji. Dwie własne karty zamknięto przez API przeglądarki i potwierdzono
ich brak na liście kart. Podgląd właściciela `http://localhost:8090/`
pozostał dostępny, HTTP 200. Żaden element środowiska produkcyjnego nie zmienił
się w ramach próby.

## Sumy dowodów

Manifest `SHA256SUMS` w katalogu surowych plików:
`a2076b089d73eac8a9734183e7c57b39923ecb30a42f32849586cd92dd5a8dc1`.
Wszystkie jego 15 wpisów zweryfikowano; zawiera sześć JPEG-ów, cztery HTML-e,
uprawnienia, wynik asercji i trzy logi/odczyty. Nie zawiera haseł ani pliku env.
Do repozytorium trafiają wyłącznie instrukcja, raport i wybrane JPEG-i,
nie surowe odpowiedzi z nonce lub konfiguracja konta testowego.

| Plik                      | SHA-256                                                            |
| ------------------------- | ------------------------------------------------------------------ |
| `01-hero-cta.jpg`         | `e505da43b81db67d4d3c1e6a6f9e85dd3e0ef9c2d606e352298c167d87ead2dc` |
| `03-card-menu.jpg`        | `5d3dd456fa2da44ef4bcf4a2a9a9b6a4c33abd84824b1ca737d86630b4e7b817` |
| `06-save-header-menu.jpg` | `a494b743c345a3b77c898f9eaed9c864813e63bbfc3b75881d8274970242beca` |
| `07-footer.jpg`           | `20468f6d05383f6e456bc1427b65f1637b1c8a5eae82876e783ea6e26d365dc5` |
| `08-cta-contact.jpg`      | `e78250da27c83f9e0cbf012710d463951833dc4a8673e21c5135898b93ce7c64` |
| `09-mobile-preview.jpg`   | `b6a79a9a171f5a28ca39f9cd17a54a25ca04e387185a54eb3e2367710bdb317c` |
| `readback-results.json`   | `57a268bf27c60fb9131e4e9f6ca609d66a0b681a98d97d3435207f5e61117f72` |
| `cleanup.log`             | `5e53132ac0dd5f2da95ee8aa97cf75c5090c597bef3bdc041b698fa810f32ca1` |

Pełny odbiór GSWEB-28 nadal wymaga właściciela, publicznego zatwierdzonego
stagingu, pozostałych scenariuszy oraz spełnienia Gate C. Ta próba nie zmienia
decyzji **NO-GO** dla produkcji.
