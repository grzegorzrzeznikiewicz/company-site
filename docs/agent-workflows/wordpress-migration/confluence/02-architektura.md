# Architektura i środowiska

Stan kodu: `19a348d`, dokumentacja: 2026-09-07.

## Podział odpowiedzialności

| Element | Rola |
| --- | --- |
| WordPress Core 7.1 / PHP 8.4 | CMS, wpisy, strony, media i edytor blokowy |
| Motyw `gama-software` 0.4.1 | Wygląd, style, szablony, sekcje, logo, nagłówek i stopka |
| `gama-contact` 0.3.2 | Pola formularza, walidacja, ochrona antyspamowa i wywołanie wysyłki |
| `gama-mail-transport` 0.1.0 | Szyfrowany transport produkcyjny SMTP, konfiguracja poza kodem |
| `gama-seo` 0.1.0 | Własne zachowania technicznego SEO |
| `gama-security` 0.1.1 | Role, ograniczenia logowania i nagłówki bezpieczeństwa |
| `gama-local-mailpit` 0.1.0 | Przechwytywanie poczty wyłącznie poza produkcją |
| MariaDB oraz uploads | Trwałe treści, ustawienia i pliki użytkowników |

Motyw odpowiada za prezentację. Funkcja, która ma przetrwać zmianę motywu,
posiada endpoint, wysyła pocztę, zarządza uprawnieniami lub trwałymi danymi,
należy do wtyczki. Własne pakiety używają GPL-2.0-or-later.
Lista zaakceptowanych rozszerzeń zewnętrznych jest obecnie pusta.

## Środowiska

| Środowisko | Adres i przeznaczenie | Poczta i dane |
| --- | --- | --- |
| Lokalne | `http://localhost:8090/`; rozwój i odbiór na komputerze właściciela | Testowa poczta w Mailpit; lokalne dane |
| Produkcyjne | `https://gama-software.com`; publiczna strona | Docelowa poczta SMTP i rzeczywiste dane; wdrożenie WP jeszcze niewykonane |

Nie tworzymy odrębnego stagingu. Jednorazowe instalacje testowe i próby CI
mogą istnieć tylko na czas testu, z odizolowaną pocztą i danymi. Nie są trzecim
stałym środowiskiem ani dowodem wdrożenia produkcyjnego.

Starsze skrypty i runbooki zawierają nazwę `staging`; część oznacza tymczasowe
modele testowe, a część faktyczny zdalny etap wdrożenia. Usunięcie zależności
od tego zdalnego etapu wymaga zmiany kodu, a nie tylko zmiany nazwy w opisie.

## Kod a treści

- Kod motywu i wtyczek jest wersjonowany w Git i pakowany w kontrolowany sposób.
- Edycje wykonane w panelu WordPressa są trwałymi danymi CMS, a nie zmianami Git.
- Treści, media i nadpisania szablonów muszą przetrwać wydanie i rollback kodu.
- Wydanie kodu nie powinno nadpisywać produkcyjnej bazy lokalną bazą testową.
- Cofnięcie kodu nie jest cofnięciem publikacji artykułu ani odtworzeniem bazy.
- Sekrety pochodzą z konfiguracji środowiska; do repozytorium i Confluence
  trafiają wyłącznie nazwy parametrów, nigdy ich wartości.

## Repozytorium i uruchomienie lokalne

`wordpress/theme/gama-software` zawiera motyw, `wordpress/plugins/` wtyczki,
`wordpress/bin/` polecenia projektu, `wordpress/tests/` kontrakty i testy,
a `wordpress/qa/` przypięte narzędzia jakości. Stary stos pozostaje osobno
w `src/` i `backend/` aż do zakończenia stabilizacji i zgody na usunięcie.

Lokalny WordPress jest uruchamiany poleceniem `wordpress/bin/start`
z katalogu głównego repozytorium. Brak odpowiedzi na porcie 8090 wymaga
sprawdzenia jego środowiska, nie resetowania wszystkich kontenerów Docker.
`wordpress/bin/reset` usuwa dane projektu i nie jest zwykłym restartem.

Pakiety motywu i formularza można zbudować przez `wordpress/bin/package`
i sprawdzić na czystej instalacji przez `wordpress/bin/test-package`.
Testy instalują dokładny ZIP bez montowania źródeł z checkoutu. Samo zbudowanie
paczki w ignorowanym `wordpress/dist` nie upoważnia do jej zewnętrznej publikacji.

## Źródła techniczne

- [Granice pakietów i cykl instalacji](https://github.com/grzegorzrzeznikiewicz/company-site/blob/19a348dea7451b1b9780e336724731a9155321fe/docs/agent-workflows/wordpress-migration/GSWEB-11-architecture.md).
- [Instrukcja środowiska WordPress](https://github.com/grzegorzrzeznikiewicz/company-site/blob/19a348dea7451b1b9780e336724731a9155321fe/wordpress/README.md).
- [Inwentarz i zasady bezpieczeństwa](https://github.com/grzegorzrzeznikiewicz/company-site/blob/19a348dea7451b1b9780e336724731a9155321fe/docs/agent-workflows/wordpress-migration/GSWEB-23-security-operations.md).

Dokumenty przypięte do commita opisują tamtą implementację. Ich wymagania
osobnego stagingu zostały zastąpione późniejszą decyzją właściciela.
