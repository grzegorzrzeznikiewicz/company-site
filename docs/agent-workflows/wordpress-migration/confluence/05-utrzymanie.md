# Utrzymanie, bezpieczeństwo, backup i rollback

Dokumentacja: 2026-09-07. Opisuje zasady i istniejące narzędzia; nie potwierdza
skonfigurowania tych usług na produkcji.

## Role i sekrety

Redaktor może edytować treści, media i Site Editor. Nie potrzebuje uprawnień
instalowania wtyczek, zmiany motywu, aktualizacji Core ani zarządzania kontami.
Administrator i operator odpowiadają za kod, konfigurację, dostęp i utrzymanie.
Konta są imienne, z najmniejszymi potrzebnymi uprawnieniami.

Nie przechowujemy w Jira ani Confluence haseł, tokenów, kluczy SSH, plików
`.env`, linków resetujących ani treści prywatnych wiadomości formularza.
Nowe konto, zwiększenie uprawnień i usunięcie konta wymagają udokumentowanego
celu oraz właściwej zgody. Usuwając konto, należy zachować jego treści przez
przypisanie ich zatwierdzonemu użytkownikowi.

Własna wtyczka bezpieczeństwa ogranicza błędy logowania i dodaje nagłówki.
To nie zastępuje prawidłowego HTTPS, aktualizacji, ochrony hosta i kontroli
dostępu. Wdrożenia nie wykonują samoczynnych aktualizacji kodu z panelu WP.

## Poczta i formularz

Lokalne wiadomości trafiają do Mailpit. Produkcja ma używać zweryfikowanego,
szyfrowanego SMTP z konfiguracją wyłącznie w środowisku. Nieprawidłowa
konfiguracja ma kończyć wysyłkę błędem, bez awaryjnego użycia PHP mail.

Odbiór wymaga potwierdzenia wiadomości w uzgodnionej skrzynce docelowej,
oprócz sprawdzenia komunikatu w przeglądarce. Testów nie należy wysyłać
do przypadkowych osób. Formularz nie zapisuje treści wiadomości w bazie WP.

## Backup

Komplet kopii obejmuje `database.sql`, `uploads.tar`, `manifest.txt`
i `SHA256SUMS`. Manifest identyfikuje czas, projekt, commit i obrazy,
bez sekretów. Kopia ma ograniczone uprawnienia i zweryfikowane sumy.

Docelowa polityka operacyjna to szyfrowane kopie poza hostem aplikacji,
30 punktów dziennych i 12 miesięcznych oraz alarm, gdy ostatnia udana kopia
ma ponad 24 godziny. To wymagania istniejącego runbooka, nie potwierdzenie
ich uruchomienia. Potrzebni są właściciel backupu i dowód działania.
Katalog na tym samym serwerze nie jest ukończonym backupem off-host.

Narzędzie odtworzenia akceptuje nową, pustą przestrzeń zasobów
`gama-restore-*`; odmawia nadpisania działającego projektu. Należy sprawdzić
zgodność obrazu, treści, mediów, logowania i izolacji poczty przed użyciem
odtworzonej instalacji. Lokalna próba trwająca 14 s nie określa produkcyjnego
RTO ani dopuszczalnej utraty danych.

## Trzy różne rodzaje wycofania

| Operacja | Co zmienia | Zasada ochrony danych |
| --- | --- | --- |
| Rollback kodu WordPressa | Poprzedni sprawdzony obraz | Zachowuje bieżącą bazę i uploads |
| Powrót do React/Symfony podczas migracji | Routing do zachowanego starego stosu | Nie usuwa danych WordPressa |
| Odtworzenie danych | Nowa instalacja z wybranej kopii | Osobna decyzja; kopia może nie zawierać nowszych zmian |

Nie wolno automatycznie wgrywać starej bazy tylko dlatego, że cofnięto kod:
mogłoby to skasować nowe wpisy lub edycje. Przy awarii najpierw określamy,
czy problem dotyczy kodu, routingu czy danych, i wybieramy właściwą procedurę.

## Aktualizacje i incydenty

Co miesiąc właściciel bezpieczeństwa przegląda wersje i informacje
o aktualizacjach; wynik trafia do Jira, także gdy nie ma zmian. Pilne poprawki
bezpieczeństwa rozpoczynają ten proces od razu. Nowa wersja przechodzi
przypięcie zależności, testy, przegląd i uzgodniony proces wydania bez stagingu.
Nie instalujemy jej ręcznie na produkcji z pominięciem pipeline'u.

Przy nieudanym wydaniu zachowujemy logi bez sekretów, identyfikator przebiegu,
commit, digest i odnośnik do kopii. Operator weryfikuje powrót usługi,
powiadamia właściciela o rzeczywistym wyniku i pozostawia zgłoszenie incydentu
otwarte do wyjaśnienia przyczyny. Progi alarmów, odpowiedzialne osoby i czas
stabilizacji wymagają uzgodnienia przed pierwszym cutoverem.

## Źródła

- [Narzędzia backupu i odtworzenia](https://github.com/grzegorzrzeznikiewicz/company-site/blob/19a348dea7451b1b9780e336724731a9155321fe/docs/agent-workflows/wordpress-migration/GSWEB-24-backup-restore.md).
- [Role, konta i przeglądy aktualizacji](https://github.com/grzegorzrzeznikiewicz/company-site/blob/19a348dea7451b1b9780e336724731a9155321fe/docs/agent-workflows/wordpress-migration/GSWEB-23-security-operations.md).
- [Obecna implementacja rollbacku](https://github.com/grzegorzrzeznikiewicz/company-site/blob/19a348dea7451b1b9780e336724731a9155321fe/docs/agent-workflows/wordpress-migration/GSWEB-29-production-pipeline.md).

Wymagania stagingowe starszych źródeł nie obowiązują w nowym modelu.
Produkcji i jej uprawnień nie zmieniono podczas przygotowania tej dokumentacji.
