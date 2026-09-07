# Instrukcja redaktora — strona i blog

Dokumentacja: 2026-09-07. Oparta na rzeczywistych próbach kontem Editor
z 2026-09-06, WordPress 7.1 i motyw `gama-software` 0.4.1.
Panel w próbach był anglojęzyczny, dlatego podajemy jego nazwy przycisków.

## Zanim zaczniesz

Lokalny podgląd to `http://localhost:8090/`, a logowanie znajduje się pod
`/wp-login.php` tej instalacji. Ćwicz lokalnie na uzgodnionych danych.
Nie używaj nieaktualnych portów ze zrzutów historycznych prób.

**Save w Site Editor zmienia stronę widoczną dla odwiedzających tej instalacji.**
Nie działa jak szkic wpisu blogowego. Na produkcji zapis będzie od razu zmianą
publicznej strony. Wdrożenie kodu i publikacja treści w CMS to różne operacje.

## Strona główna i przyciski

1. Otwórz **Appearance → Editor → Templates → Front Page**.
   **Pages → Home** nie otwiera szablonu zawierającego wszystkie nasze sekcje.
2. Włącz **Document Overview → List View**, aby wybierać konkretne bloki.
3. W sekcji Hero zmień nagłówek i akapit. Zachowaj H1 dla głównego tytułu,
   H2 dla sekcji i H3 dla kart.
4. Przycisk zachęcający do działania to CTA, np. „Poznaj nasze usługi”.
   Zmień tekst i przez **Edit link → Apply** sprawdź adres: `/#services`
   dla usług albo `/#contact` dla kontaktu.
5. Kliknij **Save**, sprawdź listę zmienionych elementów i potwierdź zapis.
   Następnie obejrzyj rzeczywistą stronę, nie tylko podgląd edytora.

## Usługi i moduły

W List View rozwiń odpowiednią sekcję i jej **Grid**. Każda karta jest
osobnym **Group**. Aby dodać usługę, zaznacz dokładnie jedną kartę,
wybierz **Duplicate** i zmień treści kopii. Aby usunąć kartę, wybierz jej
Group i **Delete**; nie zaznaczaj przez pomyłkę całej sekcji.

Nie zmieniaj kotwic `home`, `services`, `modules` i `contact`, ponieważ
prowadzą do nich menu i przyciski. Moduły również mają karty dostępne
w List View. Udokumentowana ręczna próba dodawania i usuwania karty dotyczyła
usługi, nie oddzielnego pełnego scenariusza modułów.

## Menu, logo i stopka

Wybierz **Header**, potem menu i **Edit navigation**, jeśli się pojawi.
Zmiana tekstu pozycji nie powinna usuwać jej adresu. Blog prowadzi do
`/blog/`, a Kontakt do `/#contact`, także przy powrocie z wpisu blogowego.

Zapis menu może obejmować **Header** i **Header menu**. Zatwierdź tylko zmiany
należące do Twojej edycji. Nagłówek i stopka są współdzielone, więc po zapisie
sprawdź stronę główną, listę bloga oraz wpis. Upewnij się, że logo pozostało
widoczne i linkuje prawidłowo.

Stopkę zmienisz przez **Footer → Paragraph** w List View, następnie **Save**.

## Kontakt

Formularz ma pola Imię i nazwisko, E-mail, Telefon, Wiadomość i przycisk
wysyłki. Treści sekcji są edytowalne; pola, walidacja, odbiorca i SMTP należą
do wtyczki i konfiguracji operatora.

Edytor może pokazywać zastępczy komunikat o chwilowej niedostępności formularza.
Nie usuwaj z tego powodu bloku Content ani grupy formularza. Sprawdź front.
Jeżeli tam również nie ma formularza albo wysyłka nie działa, zgłoś błąd.
Przewinięcie do Kontaktu nie jest potwierdzeniem dostarczenia wiadomości.

## Blog: szkic, podgląd i publikacja

1. **Posts → Add Post**: wpisz tytuł i treść, następnie **Save draft**.
   Potwierdź status Draft.
2. **View → Preview in new tab**: sprawdź wpis w szablonie strony oraz układ
   mobilny. Szkic nie powinien być publicznie dostępny.
3. Przed publikacją sprawdź treść, odnośniki, kategorię, miniaturę i opis
   alternatywny znaczących obrazów.
4. Dla publikacji późniejszej kliknij datę przy **Publish**, wybierz przyszłą
   datę i godzinę, sprawdź strefę czasową oraz AM/PM, potem potwierdź
   **Schedule**. Dla publikacji od razu użyj **Publish** po odbiorze treści.
5. Po terminie sprawdź `/blog/`, stronę główną i adres wpisu jako gość.
   Planowanie wymaga działającego mechanizmu zadań na docelowej instalacji;
   lokalny test nie potwierdza konfiguracji produkcji.

Aby poprawić wpis, otwórz go na liście Posts i zapisz zmianę. Aby wycofać
publikację z zachowaniem treści, zmień **Status → Draft** i naciśnij **Save**.
Nie wybieraj **Move to trash**, jeżeli chodzi tylko o wycofanie z widoku.

## Kontrola po edycji

- Sprawdź desktop i wąski widok; podgląd Mobile nie zastępuje telefonu.
- Kliknij wszystkie zmienione pozycje menu i przyciski, także z bloga.
- Sprawdź logo, nagłówki, karty, stopkę i Kontakt.
- Upewnij się, że zapisałeś tylko zamierzone zmiany.
- Próbną wiadomość wysyłaj wyłącznie do uzgodnionej testowej skrzynki.
- Nie udostępniaj hasła ani prywatnego linku do podglądu szkicu.

## Instrukcje ze zrzutami

- [Strona główna, menu i stopka — pełny przewodnik](https://github.com/grzegorzrzeznikiewicz/company-site/blob/19a348dea7451b1b9780e336724731a9155321fe/docs/agent-workflows/wordpress-migration/GSWEB-28-editor-site-guide.md).
- [Blog — pełny przewodnik](https://github.com/grzegorzrzeznikiewicz/company-site/blob/19a348dea7451b1b9780e336724731a9155321fe/docs/agent-workflows/wordpress-migration/GSWEB-28-editor-blog-guide.md).

Zrzuty przedstawiają testową treść i wyłączone już jednorazowe instalacje.
Ta instrukcja nie jest zgodą na publikację niezatwierdzonych materiałów.
