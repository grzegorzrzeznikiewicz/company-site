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

## Synchronizacja wymagań Jira — 2026-09-07

Po publikacji dokumentacji zaktualizowano opisy poniższych zgłoszeń we
właściwej instancji Gama Software. Zmiany przenoszą już zaakceptowane decyzje
właściciela do wymagań; nie są odbiorem implementacji nowego pipeline'u.

| Zgłoszenie | Zapisana korekta | Status po ponownym otwarciu |
| --- | --- | --- |
| [GSWEB-8](https://gamasoftware.atlassian.net/browse/GSWEB-8) | Jeden branch `feature/GSWEB-9` z `main@c26e196`, zachowane stashe, brak stagingu, zgodność strony i rozdzielenie zgód na wydania. | W toku |
| [GSWEB-25](https://gamasoftware.atlassian.net/browse/GSWEB-25) | Bramki lokalne/CI oraz dowód tożsamości testowanego artefaktu; zachowanie kontroli legacy nie oznacza równoległych, konfliktujących deploymentów. | Testowanie |
| [GSWEB-26](https://gamasoftware.atlassian.net/browse/GSWEB-26) | Ten sam testowany artefakt trafia do produkcji bez stagingu; zachowane backup, rollback i osobna zgoda na pierwszy cutover. | Testowanie |
| [GSWEB-28](https://gamasoftware.atlassian.net/browse/GSWEB-28) | Tytuł i opis wskazują odbiór lokalnie/CI; zachowane scenariusze redaktora, zgodność strony i niezależna próba runbooka. | Testowanie |
| [GSWEB-29](https://gamasoftware.atlassian.net/browse/GSWEB-29) | Pierwsze przełączenie z osobną zgodą; kolejne standardowe wydania automatyczne po zatwierdzonym PR i merge, z koordynacją legacy. | W toku |

Przed zapisem porównano łącznie 113 pierwotnych akapitów po 11 celowych
korektach sprzecznych zapisów: żadnego nie pominięto. Dodano datowane
uzupełnienia i odnośniki do opublikowanych rozdziałów Confluence. Zmieniono
także tytuł GSWEB-28 na „WP: Przeprowadzić próbę migracji i odbiór edycji
treści lokalnie i w CI”. Po ponownym otwarciu wszystkich pięciu zgłoszeń
potwierdzono pojedynczy zapis decyzji w każdym opisie oraz brak otwartych
edytorów. Statusów, przypisań i estymacji nie zmieniano; wcześniejsze
komentarze pozostawiono jako historię poprzedniego modelu.

Na zakończenie tej synchronizacji szczegółowa
[specyfikacja nowego workflow](../../../superpowers/specs/2026-09-07-wordpress-no-staging-release-design.md)
czekała na przegląd właściciela. W ramach synchronizacji nie zmieniono kodu pipeline'u, nie
wykonano merge, publikacji obrazu ani operacji produkcyjnej. Nie uruchamiano
ponownie testów runtime z powodu zmian w opisach i dokumentacji.

## Akceptacja specyfikacji i rozpoczęcie implementacji — 2026-09-07

Późniejsza odpowiedź właściciela „Tak” zatwierdziła szczegółową specyfikację.
Rozpoczęto [plan implementacji](../../../superpowers/plans/2026-09-07-wordpress-no-staging-release.md)
na `feature/GSWEB-9`, bez commitów, pushowania i dodatkowych worktree.
W rozdziale Confluence „Wydania produkcyjne bez stagingu” zaktualizowano
status oraz zapis decyzji i potwierdzono opublikowany widok. Zachowano
24 akapity, nagłówki, listy, tytuł i odnośniki; nie zmieniano uprawnień.
Pierwszy cutover, publikacja obrazu i uruchomienie produkcyjne nie zostały wykonane.

## Aktualizacja wyników i ponowna publikacja — 2026-09-08

Rozdział [Testy, audyt i odbiór migracji](04-jakosc-i-odbior.md) uzupełniono
lokalnie o świeże próby źródeł, dokładnych ZIP-ów i obrazu developerskiego.
Oddzielono je od historycznego CI oraz wskazano ograniczenie emulacji amd64
i późniejszą świeżą próbę obu rzeczywistych konsumentów po poprawkach helperów.
Lokalnie zaktualizowano również [Utrzymanie](05-utrzymanie.md) o blokadę
hosta, rozliczanie incydentów i zgodę na odzyskiwanie. Aktualizacje rozdziałów
03, 04 i 05 **opublikowano ponownie w Confluence** przez rozszerzenie Chrome
w profilu Gama Software. W opublikowanych widokach potwierdzono wszystkie
144 oczekiwane fragmenty treści i 11 odnośników. Niezależne porównanie
znormalizowanej treści z lokalnymi źródłami potwierdziło zgodność trzech rozdziałów.
Historyczne adresy, tytuły i dowody pozostają bez zmian.

W [GSWEB-8](https://gamasoftware.atlassian.net/browse/GSWEB-8) zapisano i odczytano
pojedynczy komentarz „Aktualizacja implementacji i dokumentacji — 2026-09-08”.
Aktualizuje on historyczne informacje o oczekującej specyfikacji i implementacji,
bez zmiany statusów zgłoszeń. Lokalna implementacja i niezależny przegląd są
zakończone; pełny CI nowej wersji, odbiór operacyjny i produkcja pozostają otwarte.
Gate C nadal NO-GO. Nie wykonano commitów, pushowania, merge ani wdrożenia.

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

Kod odniesienia historycznej publikacji: `19a348dea7451b1b9780e336724731a9155321fe`.
Metadane PR #8 odczytano 2026-09-07: otwarty, bez merge, `main` nadal
`c26e19699c7a66a15e0854cf3bb4fce342bf2e2c`.
Historyczne wyniki CI dotyczą potwierdzeń z 2026-09-06. Nowe wyniki lokalne
dotyczą niezacommitowanej implementacji nad `87cab81a06057142463c82201e8cbabe7d2593a1`;
opisano je osobno w rozdziale 04. Publikacja dokumentacji nie jest nowym CI.

Decyzja właściciela z 2026-09-06 o braku stagingu i automatycznych kolejnych
wydaniach zastępuje sprzeczne wymagania wcześniejszych runbooków. Nie oznacza
jednak ich wdrożenia: workflow przebudowano i sprawdzono lokalnie, lecz nie
opublikowano nowej wersji źródeł. Niniejszy pakiet dokumentacji nie nadaje
Gate C ani Gate D statusu GO.
