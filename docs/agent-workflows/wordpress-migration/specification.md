# Specyfikacja migracji strony Gama Software do WordPressa

## Cel

Zastąpić obecną aplikację React/Symfony stroną opartą na WordPressie, którą
właściciel może szybko edytować z panelu administracyjnego, zachowując wygląd,
układ, menu, treści, zachowania, formularz, jakość techniczną i możliwość
tworzenia własnych rozszerzeń. Migracja nie jest redesignem.

## Źródła prawdy

1. Zakres produktu i kryteria akceptacji: zgłoszenia Jira GSWEB-8–GSWEB-30.
2. Obowiązujące decyzje wspólne: ten dokument.
3. Rzeczywisty stan techniczny: aktualny kod i konfiguracja repozytorium.
4. Historia decyzji technicznych: zaakceptowane dokumenty oraz commity.

W razie sprzeczności agent nie zgaduje. Dokumentuje sprzeczność i prosi
właściciela o decyzję przed wykonaniem zmiany trudnej do cofnięcia.

## Wierność obecnej strony

- Zatwierdzony inwentarz GSWEB-9, działający kod React/Symfony i przekazane przez
  właściciela zrzuty ekranu są materiałem porównawczym, a nie opcjonalną
  inspiracją do nowego projektu.
- WordPress musi zachować strukturę i kolejność publicznej strony: logo oraz
  menu Start/Usługi/Moduły/Blog/Kontakt, Hero z CTA, karty usług, sekcję
  modułów, blog, kontakt i stopkę. Treść, linki, media i komunikaty muszą
  odpowiadać baseline'owi, chyba że właściciel zaakceptuje konkretną zmianę.
- Zachowania muszą obejmować działającą nawigację desktopową i mobilną, kotwice
  oraz CTA, użyteczną responsywność, publikację bloga i pełny przepływ formularza
  kontaktowego. WordPress może użyć własnych mechanizmów, ale nie może tracić
  funkcjonalności obecnej strony.
- Odbiór obejmuje porównanie renderowanej strony WordPress z baseline'em na
  desktopie i telefonie. Każde istotne odchylenie wizualne, treściowe lub
  funkcjonalne wymaga udokumentowania i akceptacji właściciela.

## Architektura docelowa

- WordPress działa jako klasyczna aplikacja renderująca stronę, a nie jako
  headless CMS z osobnym frontendem React.
- Interfejs strony powstaje jako własny motyw blokowy zgodny z Site Editorem.
- Globalne style i tokeny wizualne znajdują się przede wszystkim w `theme.json`.
- Nagłówek, stopka, nawigacja, szablony i sekcje strony są edytowalne przez
  natywne mechanizmy blokowe WordPressa.
- Powtarzalne sekcje mogą korzystać z patterns, template parts i natywnych
  bloków. Własny blok powstaje tylko wtedy, gdy mechanizmy Core nie zapewniają
  bezpiecznej i wygodnej edycji.
- Logika niezależna od wyglądu należy do własnej wtyczki, nie do motywu.
- Własne rozszerzenia mają być możliwe do zbudowania jako czyste paczki ZIP,
  instalowane na świeżej, wspieranej wersji WordPressa.
- Dane trwałe obejmują co najmniej bazę oraz `wp-content/uploads`. Kod motywu,
  własnych wtyczek i zatwierdzonej konfiguracji jest wersjonowany w Git.

## Edycja z panelu

Użytkownik z rolą Editor ma bez edycji kodu móc:

- zmienić treść Hero i CTA;
- zmienić elementy oraz kolejność menu;
- edytować nagłówek i stopkę w dozwolonym zakresie;
- dodawać, usuwać i zmieniać kolejność kart usług i modułów;
- edytować sekcję kontaktową;
- tworzyć, publikować, aktualizować i wycofywać wpisy blogowe;
- wymieniać obrazy i uzupełniać ich tekst alternatywny;
- zmieniać kolejność sekcji strony głównej bez naruszania jej responsywności.

Editor nie może instalować wtyczek, zmieniać kodu, zarządzać administratorami
ani wykonywać operacji infrastrukturalnych.

## Rozszerzenia i zależności

- Funkcje wymagane przez epik muszą działać bez płatnej licencji.
- Preferowane są WordPress Core i niewielka liczba aktywnie utrzymywanych,
  darmowych wtyczek z wiarygodnego źródła.
- Nie wprowadzamy page buildera zastępującego Gutenberg i Site Editor.
- Każda zewnętrzna wtyczka wymaga udokumentowania celu, źródła, licencji,
  kompatybilności, historii aktualizacji, ograniczeń i możliwej alternatywy.
- Dwie wtyczki nie powinny implementować tej samej funkcji, np. generowania
  metadanych SEO, cache lub zabezpieczenia logowania.
- Funkcja istotna dla projektu, która ma być dystrybuowana innym użytkownikom,
  musi mieć granicę API, testy, wersjonowanie semantyczne i instrukcję budowania.
- Jeżeli odtworzenie funkcji wymaga rozszerzenia poza WordPress Core, motyw i
  istniejące własne wtyczki, powstaje osobne zgłoszenie Jira w epiku GSWEB-8.
  Opisuje ono lukę funkcjonalną, uzasadnienie wyboru, alternatywy, licencję,
  bezpieczeństwo, kompatybilność, sposób aktualizacji i test odbiorczy. Nie
  instalujemy takiej wtyczki poza tym śladem pracy.

## Bezpieczeństwo i prywatność

- Sekrety nie trafiają do Git, obrazów kontenerów, logów ani paczek ZIP.
- Produkcja wymusza HTTPS, bezpieczne cookies i wyłączone wyświetlanie błędów.
- Edytor plików motywu oraz wtyczek w panelu jest wyłączony.
- Formularz ma walidację serwerową, sanityzację, ochronę CSRF i ochronę
  antyspamową bez wymagania płatnej usługi.
- Treść formularza nie jest zapisywana w bazie bez odrębnej, uzasadnionej
  decyzji dotyczącej retencji i prywatności.
- Uprawnienia ról są zgodne z zasadą najmniejszych uprawnień.
- Aktualizacje Core, motywu i wtyczek przechodzą najpierw przez staging, testy,
  backup oraz udokumentowaną możliwość cofnięcia.

## Jakość, dostępność i SEO

- Zachowujemy istniejącą tożsamość wizualną; migracja nie jest redesignem.
- Strona ma semantyczną hierarchię nagłówków, obsługę klawiaturą, widoczny focus,
  właściwe etykiety formularza, teksty alternatywne i kontrast zgodny z WCAG 2.1 AA.
- Publiczne adresy URL pozostają bez zmian albo otrzymują pojedyncze
  przekierowanie 301 do właściwego odpowiednika.
- Produkcja nie może mieć przypadkowego `noindex`; staging musi być wyłączony
  z indeksowania i nie może wysyłać wiadomości do rzeczywistych klientów.
- Tytuły, opisy, canonical, robots, sitemap XML, Open Graph i podstawowe dane
  strukturalne muszą mieć jedno, niekonfliktujące źródło.
- Każda zmiana dodaje test na poziomie proporcjonalnym do ryzyka: jednostkowy,
  integracyjny, E2E, statyczny albo jawnie opisany test ręczny.

## CI/CD i eksploatacja

- Obecne workflow React/Symfony pozostają dostępne, dopóki WordPress nie przejdzie
  odbioru i nie zakończy się okres stabilizacji.
- Ten sam niezmienny artefakt powinien przejść przez staging i produkcję.
- Obrazy i zależności mają przypięte wersje; wdrożenia są identyfikowalne przez
  SHA commita lub równoważny niezmienny identyfikator.
- Baza i media przeżywają restart oraz wymianę obrazu aplikacji.
- Backup znajduje się poza hostem produkcyjnym, ma kontrolę świeżości, retencję
  i przetestowaną procedurę pełnego odtworzenia.
- Rollback kodu jest oddzielony od odzyskiwania danych. Baza nie jest cofana
  automatycznie bez jawnej procedury i decyzji.
- Logi i monitoring pozwalają wykryć błędy HTTP 5xx, błędy PHP/JavaScript,
  problemy z pocztą, stan kontenerów i problemy z zasobami.

## Granice migracji

- Nie usuwamy ani nie modyfikujemy zasobów współdzielonych z innymi projektami
  na hoście `/srv/magento-devops`.
- Nie publikujemy niezatwierdzonych treści prawnych.
- Nie dodajemy płatnych wtyczek jako warunku spełnienia kryteriów epika.
- Nie usuwamy starego stosu przed zakończeniem okresu stabilizacji i jawną zgodą
  właściciela.
- Nie włączamy niezwiązanych zmian użytkownika do commitów migracyjnych.

## Definition of Done pojedynczego zgłoszenia

Zgłoszenie można uznać za wykonane, gdy:

1. Wszystkie jego kryteria akceptacji mają dowód wykonania.
2. Zmiana jest ograniczona do uzgodnionego zakresu.
3. Odpowiednie testy przechodzą na czystym środowisku lub istnieje udokumentowany
   test ręczny z wynikiem.
4. Nie ma nierozwiązanych problemów recenzji o priorytecie blokującym lub wysokim.
5. Dokumentacja, przykładowa konfiguracja i nazwy sekretów odpowiadają kodowi.
6. Commit lub pull request zawiera klucz Jira.
7. Jira zawiera podsumowanie zmian, wyniki testów, ryzyka i kroki operacyjne.

## Definition of Done epika

Epik jest zakończony, gdy wszystkie zgłoszenia GSWEB-9–GSWEB-30 spełniają własne
kryteria, WordPress działa na produkcji, właściciel potwierdził edycję z panelu,
backup i rollback zostały sprawdzone, okres stabilizacji dobiegł końca, a stare
usługi usunięto bez wpływu na inne projekty.
