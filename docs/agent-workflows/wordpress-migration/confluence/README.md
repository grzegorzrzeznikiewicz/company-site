# Dokumentacja GSWEB do Confluence

Przygotowano i opublikowano: 2026-09-07. Stan: **strona główna oraz sześć
rozdziałów opublikowane w Confluence**.

Właściciel wskazał przestrzeń
[BP](https://gamasoftware.atlassian.net/wiki/spaces/BP/overview?homepageId=1212592).
Odczyt we właściwym profilu Gama Software pokazał nazwę **Budget Planner**.
Zgodnie z podanym przez właściciela adresem dokumentacja strony firmowej
powstaje tam jako osobny dział GSWEB. Nazwa przestrzeni nie zmienia wskazania
docelowego adresu i nie jest powodem tworzenia innej przestrzeni.
Nie zmieniono nazwy przestrzeni, jej strony głównej ani uprawnień.

## Struktura publikacji

Stroną nadrzędną jest [GSWEB — strona firmowa Gama Software](00-start.md).
Jej podstrony:

1. [Projekt, zakres i aktualny stan](01-projekt.md).
2. [Architektura i środowiska](02-architektura.md).
3. [Wydania produkcyjne bez stagingu](03-wydania.md).
4. [Testy, audyt i odbiór migracji](04-jakosc-i-odbior.md).
5. [Utrzymanie, bezpieczeństwo, backup i rollback](05-utrzymanie.md).
6. [Instrukcja redaktora: strona i blog](06-instrukcja-redaktora.md).

## Opublikowane strony

- [GSWEB — strona firmowa Gama Software](https://gamasoftware.atlassian.net/wiki/spaces/BP/pages/1376257/GSWEB+strona+firmowa+Gama+Software).
- [Projekt, zakres i aktualny stan](https://gamasoftware.atlassian.net/wiki/spaces/BP/pages/1507329/Projekt+zakres+i+aktualny+stan).
- [Architektura i środowiska](https://gamasoftware.atlassian.net/wiki/spaces/BP/pages/1572865/Architektura+i+rodowiska).
- [Wydania produkcyjne bez stagingu](https://gamasoftware.atlassian.net/wiki/spaces/BP/pages/1605634/Wydania+produkcyjne+bez+stagingu).
- [Testy, audyt i odbiór migracji](https://gamasoftware.atlassian.net/wiki/spaces/BP/pages/1769473/Testy+audyt+i+odbi+r+migracji).
- [Utrzymanie, bezpieczeństwo, backup i rollback](https://gamasoftware.atlassian.net/wiki/spaces/BP/pages/1703940/Utrzymanie+bezpiecze+stwo+backup+i+rollback).
- [Instrukcja redaktora — strona i blog](https://gamasoftware.atlassian.net/wiki/spaces/BP/pages/1179671/Instrukcja+redaktora+strona+i+blog).

Każdy rozdział jest bezpośrednim dzieckiem strony GSWEB. Potwierdzono zapis
w widoku opublikowanej strony, nie tylko obecność szkicu w edytorze.
Linki względne ze spisu treści są w Confluence zastępowane powyższymi adresami.

Odczyt wszystkich sześciu rozdziałów po publikacji potwierdził 245 fragmentów
treści (akapity, listy, nagłówki i komórki tabel), bez braków. Spis treści
prowadzi do sześciu właściwych identyfikatorów stron. Confluence skraca linki
do kanonicznych adresów bez slugów i rozwija WordPress.org do karty linku;
uwzględniono te widoczne różnice prezentacji przy porównaniu.

W GSWEB-8 zapisano komentarz **Dokumentacja Confluence — 2026-09-07**
z odnośnikiem do działu i rozróżnieniem dokumentacji, projektu pipeline'u
oraz wdrożenia. Nie zmieniono statusów zgłoszeń ani konfiguracji produkcji.

## Zasady aktualizacji

- Jira przechowuje wymagania, status i decyzje dotyczące zgłoszeń.
- Confluence opisuje projekt i sposób pracy; nie zastępuje dowodów z CI.
- Git przechowuje kod, wersjonowane procedury i historyczne dowody.
- Każda zmiana opisu rozróżnia decyzję, implementację i rzeczywiste wdrożenie.
- Odnośniki do historycznych wyników pozostają przypięte do właściwej wersji.
- Nie publikujemy haseł, tokenów, plików `.env`, baz danych, wiadomości
  formularza ani prywatnych linków do podglądów.
- Przy kolejnych aktualizacjach zachowujemy adresy stron i odnośnik w GSWEB-8.

## Aktualność źródeł

Kod odniesienia: `19a348dea7451b1b9780e336724731a9155321fe`.
Metadane PR #8 odczytano 2026-09-07: otwarty, bez merge, `main` nadal
`c26e19699c7a66a15e0854cf3bb4fce342bf2e2c`.
Wyniki testów i zestawienie statusów dzieci dotyczą potwierdzeń z 2026-09-06;
sam odczyt dokumentacji nie oznacza ponownego uruchomienia testów.

Decyzja właściciela z 2026-09-06 o braku stagingu i automatycznych kolejnych
wydaniach zastępuje sprzeczne wymagania wcześniejszych runbooków. Nie oznacza
jednak, że ich workflow zostały już przebudowane. Niniejszy pakiet dokumentacji
nie nadaje Gate C ani Gate D statusu GO.
