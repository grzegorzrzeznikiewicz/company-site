# GSWEB-29 — jednorazowa inwentaryzacja serwera bez wdrożenia

## Zgoda i granice — 2026-09-10

Właściciel zatwierdził przygotowanie trybu `read-only-audit`, testy, niezależny
przegląd, commit/push do PR #8 oraz jedno ręczne uruchomienie. Zgoda nie obejmuje
merge, instalowania narzędzi na serwerze, restartów ani przełączenia produkcji.
Celem całej epiki pozostaje wydanie WordPressa na `gama-software.com`.

Istniejący workflow `.github/workflows/deploy.yml` jest zarejestrowany na `main`.
Nowy tryb można wywołać z opublikowanej gałęzi `feature/GSWEB-9`, bez merge.
Nie wolno wywoływać dotychczasowego trybu wydania na `main` w celu audytu.

## Ograniczenia wykonania

- Wyłącznie ręczne `workflow_dispatch` z `operation=read-only-audit`.
- Dokładna gałąź `feature/GSWEB-9`, repozytorium i ścieżka workflow.
- Właściciel GitHub ID `50638878`, ten sam zatwierdzony inicjator ponownego
  wywołania, tylko próba nr 1 i `GAMA_DEPLOYMENT_MODE=off`.
- Oddzielny bezsekretowy `audit-guard`, następnie niezależny job audytu.
- Zwykły `guard`, budowanie i wdrażanie są pomijane dla trybu audytu.
- Brak uprawnień zapisu GitHub; checkout dokładnego SHA bez zachowania tokenu.
- Ponowna walidacja warunków w procesie używającym SSH.
- Istniejące sekrety `SERVER_HOST`, `SERVER_USER`, `SSH_PORT`, `SSH_PRIVATE_KEY`
  pozostają w Actions. Nie są pobierane na komputer ani wypisywane w logach.

## Weryfikacja tożsamości serwera

Wymagany jest dodatkowo `SERVER_SSH_FINGERPRINT` w formacie `SHA256:…`.
Odcisk musi pochodzić z konsoli dostawcy lub wcześniej zaufanej sesji SSH,
a nie z niezweryfikowanego skanowania sieci przez ten sam audyt.
Jest to odcisk **publicznego klucza hosta**, nie klucza prywatnego użytkownika.

Brak lub niepoprawny format odcisku zatrzymuje audyt przed połączeniem.
`ssh-keyscan` służy tylko do pobrania publicznego klucza do porównania z odciskiem;
sam wynik skanowania nie ustanawia zaufania. Niedopasowanie blokuje uwierzytelnienie.
SSH używa tylko przypiętego klucza hosta, bez TOFU, konfiguracji użytkownika,
agenta SSH, haseł i interaktywnego uwierzytelnienia. Tymczasowy klucz klienta
powstaje wyłącznie na runnerze z prawami `0600` i jest usuwany po próbie.

## Co raport oznacza

Stały skrypt przesyłany przez stdin sprawdza Linux, amd64, wersję Pythona oraz
metadane siedmiu z góry znanych ścieżek Gama. Nie zapisuje skryptu na serwerze,
nie używa sudo, nie uruchamia Docker/Compose, nie przegląda katalogów i nie
czyta treści konfiguracji, sekretów, baz ani plików innych projektów.
Zwykłe logi systemowe połączenia SSH mogą oczywiście zostać zapisane przez serwer.

Raport zawiera tylko zamknięty zbiór nazw oraz wartości typu `yes`, `missing`,
`file`, `directory`, `symlink`, `unreadable`. Niedostępna ścieżka nie jest dowodem
jej nieistnienia. Surowe stdout/stderr z połączenia nie trafiają do publicznych
logów; publikowany jest jedynie raport po walidacji zamkniętego schematu.

To inwentaryzacja, **nie pozytywny Gate C**. Nie potwierdza uruchomionych usług,
routingu, SMTP, retencji ani skutecznego odtworzenia backupu. Te dowody oraz
zgoda na dokładną wersję i okno pierwszego wdrożenia pozostają wymagane.

## Uruchomienie po przeglądzie i opublikowaniu

Weryfikacja lokalna 2026-09-10: `production-workflow-boundary-contract.sh`
przeszedł 191/191 testów w izolowanym, tylko do odczytu kontenerze Linux.
`wordpress-ci-contract.sh` przeszedł walidację rzeczywistego YAML i 17 negatywnych
wariantów uprawnień/zależności. `production-deployment-contract.sh` oraz
`git diff --check` również przeszły. Niezależny przegląd kodu audytu: APPROVE,
bez usterek blokujących; po przeglądzie dodano dwa testy granicy CLI.

Na moment przygotowania zmiany `SERVER_SSH_FINGERPRINT` nie istnieje w sekretach
repozytorium. Nie wykonano połączenia audytowego ani wdrożenia. Zgoda właściciela
na jedno uruchomienie pozostaje do wykorzystania po dostarczeniu zaufanego odcisku.

Przed uruchomieniem sprawdzić SHA gałęzi, wynik testów, aktualny tryb `off` i
obecność zaufanego odcisku. Wywołać dokładnie raz:

```sh
gh workflow run deploy.yml --ref feature/GSWEB-9 -f operation=read-only-audit
```

Sprawdzić rzeczywiste SHA i input w runie, wynik `audit-guard`, wynik audytu oraz
status `skipped` dla `guard`, `build` i `deploy`. Nie interpretować samego zielonego
statusu workflow jako dowodu wykonania sondy. Zapisać ID runu i zweryfikowany raport.

## Wynik jednej zatwierdzonej próby — 2026-09-27

Właściciel przekazał publiczny klucz ED25519 i polecił spróbować z tym kluczem.
Jego odcisk zapisano jako `SERVER_SSH_FINGERPRINT`. Źródło klucza nie zostało
niezależnie potwierdzone; użyto wartości wskazanej przez właściciela, bez TOFU
i bez wyłączania kontroli klucza hosta.

Uruchomiono dokładnie jeden
[audyt 36341394731](https://github.com/grzegorzrzeznikiewicz/company-site/actions/runs/36341394731)
na `feature/GSWEB-9`, SHA `4f4fb3f2b78500ad77a216c509fecaf05997ff03`,
z `operation=read-only-audit` i trybem `off`.

- Osiem kontroli CI tego SHA: SUCCESS; ponowne lokalne testy sondy: 9/9.
- `audit-guard`: SUCCESS.
- Porównanie odcisku z publicznym kluczem pobranym przez `ssh-keyscan` przeszło:
  kod dotarł do właściwego wywołania SSH.
- SSH zwróciło kod różny od zera, komunikat `SSH audit failed; raw connection
  output suppressed.`. Raport inwentaryzacji nie powstał. Nie ustalono, czy
  przyczyną było uwierzytelnienie, weryfikacja klucza w samym SSH, połączenie,
  czy wykonanie zdalnego Pythona; nie należy utożsamiać porównania odcisku ze
  skutecznym zalogowaniem.
- `guard`, `Deploy to Server` (build), `deploy`: SKIPPED. Brak merge, wdrożenia
  i restartu. `GAMA_DEPLOYMENT_MODE` pozostaje `off`.

Jednorazowa zgoda została wykorzystana. Dalsza próba wymaga uzgodnienia;
następny krok to diagnostyka z zamkniętymi kategoriami błędów bez wypisywania
surowych danych połączenia, kluczy ani konfiguracji.

## Dodatkowa zgoda i diagnostyka — 2026-09-27

Właściciel zatwierdził dodanie bezpiecznej diagnostyki, commit/push tej zmiany
i jedną kolejną próbę audytu, bez wdrożenia. Rozszerzenie nie zmienia komendy SSH,
kluczy, sprawdzania tożsamości hosta, warunków uruchomienia ani zdalnej sondy.

Przy błędzie raportowana jest tylko stała kategoria i liczbowy kod zakończenia
procesu SSH. Rozpoznawane są: problem odczytu klucza prywatnego, odrzucenie
uwierzytelnienia, weryfikacja klucza hosta, timeout/odmowa/zamknięcie połączenia,
DNS, negocjacja algorytmów, brak Pythona i błąd zdalnej komendy. Nieznane błędy
pozostają nieznane. Timeout całego procesu wskazuje etap: pobranie klucza hosta
lub właściwe SSH. Kategorie opisują zaobserwowany komunikat, a nie stanowią
samodzielnego dowodu przyczyny źródłowej. Surowe stdout/stderr pozostają ukryte;
nie dodano automatycznych ponowień.

Weryfikacja rozszerzenia: 193/193 testów mechanizmu wydań w izolowanym kontenerze
Linux, walidacja YAML z 17 negatywnymi przypadkami, kontrakt wdrożenia i kontrola
diff: PASS. Niezależny przegląd zmiany kodu: APPROVE. Testy CLI obejmują 14
przypadków błędu SSH oraz oba etapy timeoutu, z potwierdzeniem braku wycieku
surowych danych i braku automatycznej ponownej próby.

### Wynik próby diagnostycznej

Zmiana została opublikowana jako `bd0501faa701c9fb3229cc1f4b04e0f6967f01a7`.
Dokładnie jedna kolejna próba:
[run 36341937212](https://github.com/grzegorzrzeznikiewicz/company-site/actions/runs/36341937212),
2026-09-27, etap SSH około 18:47:33–18:47:45 UTC (20:47:33–20:47:45 Europe/Warsaw).

`audit-guard` zakończył się SUCCESS; porównanie odcisku hosta przeszło.
Proces SSH zakończył się z `category=connection_timeout, exit=255`.
Nie uzyskano raportu sondy. Ten wynik wskazuje timeout połączenia, nie jest
potwierdzeniem odrzucenia klucza użytkownika ani udanego uwierzytelnienia.
Dokładny etap i przyczyna timeoutu wymagają danych z logów SSH/sieci serwera;
firewall, limity połączeń i inne blokady pozostają hipotezami, nie ustaleniami.

Zadania `guard`, `Deploy to Server` i `deploy` zostały SKIPPED. Brak merge,
wdrożenia i restartów. Zgoda na tę pojedynczą próbę została wykorzystana;
nie wykonano automatycznego ponowienia ani zmiany kluczy lub polityk dostępu.

## Diagnostyka serwera i ograniczenie skanowania — 2026-09-27

Właściciel udostępnił połączoną sesję Codex w WebSSH. Zlecona diagnostyka była
wyłącznie odczytowa: bez zmian konfiguracji, odblokowania IP i restartów.
Raport serwera wskazał synchronizowany czas UTC oraz blokady `UFW LIMIT BLOCK`
pakietów SYN do portu 22 z tych samych źródeł, z których chwilę wcześniej
przychodziła seria połączeń SSH. Sekwencje wystąpiły w obu oknach audytów:
18:38:41–18:38:46 oraz 18:47:34–18:47:39 UTC. Reguła SSH miała stan `LIMIT IN`,
z progiem sześciu połączeń z jednego źródła w ciągu 30 sekund. W tych oknach
nie znaleziono wpisów Fail2ban. Sam raport nie przypisuje każdego pakietu do
konkretnego procesu klienta; korelacja mocno wspiera hipotezę wyczerpania limitu
przez skanowanie wielu typów kluczy, a nie odrzucenia klucza użytkownika.

Właściciel zatwierdził minimalną poprawkę, testy, commit/push i dokładnie jedną
kolejną próbę audytu, bez merge i wdrożenia. `ssh-keyscan` otrzymuje teraz
`-t ed25519`, zgodnie z typem przypiętego klucza właściciela. Według
[dokumentacji OpenSSH](https://man.openbsd.org/ssh-keyscan#t) domyślnie skanowane
są wszystkie obsługiwane typy. Nie zmieniono odcisku, sekretów, właściwej
komendy SSH, zdalnej sondy, timeoutów, liczby ponowień ani zabezpieczeń serwera.
Brak oczekiwanego klucza nadal zatrzymuje audyt przed uwierzytelnieniem.

Test transportu najpierw zakończył się oczekiwanym błędem dla nieograniczonego
skanowania; po zmianie polecenia wszystkie 11 testów audytu przeszło.
Pełny zestaw mechanizmu wydań: 193/193 PASS w izolowanym kontenerze Linux;
walidacja YAML i 17 negatywnych wariantów, kontrakt wdrożenia oraz
`git diff --check`: PASS. Pozostałe lokalne zmiany dokumentacji są poza zakresem
tej poprawki i nie wchodzą do jej commita.
Niezależny przegląd poprawki: APPROVE, bez usterek. Przegląd potwierdził zachowanie
granic bezpieczeństwa i ponownie uruchomił 11 testów audytu; nie zastępuje wyniku
połączenia ani akceptacji produkcyjnego wydania.

## Panel administracyjny (adresy)

Lokalnie: <http://localhost:8090/wp-admin/>. Dnia 2026-09-10 sprawdzono odpowiedź
HTTP 302 do lokalnego `wp-login.php`. Po wydaniu WordPressa domyślnym adresem
będzie <https://gama-software.com/wp-admin/>; nie jest to deklaracja, że migracja
produkcyjna już nastąpiła.

Zmiana URL logowania jest opcjonalną warstwą ograniczającą część automatycznych
prób, a nie podstawą bezpieczeństwa. Priorytet: 2FA, mocne unikalne hasło, limity
logowania, aktualizacje i HTTPS. Niniejsza zmiana nie instaluje wtyczki ani nie
modyfikuje URL panelu. Podstawa:
[oficjalne zalecenia WordPress](https://developer.wordpress.org/advanced-administration/security/hardening/).
