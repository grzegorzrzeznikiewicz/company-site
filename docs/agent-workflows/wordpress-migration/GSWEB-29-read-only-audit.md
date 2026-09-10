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

## Panel administracyjny

Lokalnie: <http://localhost:8090/wp-admin/>. Dnia 2026-09-10 sprawdzono odpowiedź
HTTP 302 do lokalnego `wp-login.php`. Po wydaniu WordPressa domyślnym adresem
będzie <https://gama-software.com/wp-admin/>; nie jest to deklaracja, że migracja
produkcyjna już nastąpiła.

Zmiana URL logowania jest opcjonalną warstwą ograniczającą część automatycznych
prób, a nie podstawą bezpieczeństwa. Priorytet: 2FA, mocne unikalne hasło, limity
logowania, aktualizacje i HTTPS. Niniejsza zmiana nie instaluje wtyczki ani nie
modyfikuje URL panelu. Podstawa:
[oficjalne zalecenia WordPress](https://developer.wordpress.org/advanced-administration/security/hardening/).
