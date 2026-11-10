3.1 Kto może korzystać z systemu

Z założenia, prototyp powinien obsługiwać trzy niezbędne role - student, nauczyciel oraz administrator. W prawdziwym USOSie lub podobnej platformie uczelnianej roli więcej, bo są jeszcze inni pracownicy uczelni, ale te trzy to zupełne minimum, by system był użyteczny. 

Jednocześnie, jedna osoba powinna być w stanie bezproblemowo przy pomocy jednego konta mieć dostęp do funkcji zależnych od wielu ról jednocześnie. Czyli nauczyciel, który jednocześnie studiuje na tej samej uczelni powinien być w stanie zarządzać jednym kontem zarówno zajęciami, które prowadzi, jak i swoim uczestnictwem w cudzych lekcjach. Dostępy do tych funkcji, ograniczone przez autoryzację na endpointach, powinny być odzwierciedlone w kliencie - nie powinna być widoczna zakładka, do której użytkownik nie ma dostępu. Jednocześnie bardzo ważna jest walidacja na backendzie - samo ograniczenie widoczności nic nie da, jeśli dalej jest możliwość komunikacji z API poprzez programy takie jak Postman bądź własnych klientów.

System ma wspierać zarówno dane obecne, jak i archiwalne. W założeniu możliwy ma być proces offboardingu poprzez usunięcie bądź dezaktywację nieużywanego konta. Jeśli ktoś odejdzie z uczelni, jego dane mają pozostać w systemie, nawet jeśli ta osoba już nie ma mozliwości zalogowania.

3.2 Wymagania funkcjonalne

Dla użytkowników z utworzonym kontem powinna być możliwość zalogowania się poprzez wpisanie adresu e-mail i hasła. Konta są tworzone administracyjnie, zatem nie istnieje sposób na rejestrację dla osób trzecich. Role i dostępy również są przyznawane z poziomu administracyjnego.

Każdy zalogowany użytkownik powinien mieć dostęp do katalogu. Składa się on z endpointów pozwalających na wylistowanie informacji na temat uczelni, zarówno w całości, jak i po przefiltrowaniu. Na te informacje składają się wydziały, kierunki, semestry, przedmioty, grupy zajęciowe, prowadzący.

Z racji tego, że każdy zalogowany będzie studentem, prowadzącym lub administratorem, każdy powinien też mieć dostęp do planu zajęć na następne tygodnie. Plan uwzględnia granice semestru - każdy cykl akademicki ma w bazie danych datę rozpoczęcia i zakończenia zajęć, a zajęcia z danego cyklu są pokazywane wyłącznie w tym przedziale. Plan uwzględnia również podział na tygodnie parzyste i nieparzyste. Nie rozpoznaje natomiast świąt, dni rektorskich i innych wydarzeń, które mogłyby przesunąć lub usunąć zajęcia danego dnia.

Student powinien być w stanie podejrzeć swój własny plan studiów oraz dotychczasowo odbyte semestry na kierunkach, na których jest zapisany. Należy też pozwolić mu na dostęp do jego tur rejestracyjnych przypisanych do odpowiednich rejestracji. Z poziomu tur zapisowych student powinien też mieć możliwość zapisu do grup objętych tą rejestracją. Dla każdego typu grupy zajęciowej student może się zapisać do tylko jednej. Pojemność grupy zajęciowej należy śledzić na żywo i odrzucić próby zapisania się do grupy bez wolnych miejsc. 

Należy również pozwolić studentowi na odczyt ocen, które otrzymał w ramach przedmiotów i grup zajęciowych, a także wystawienie opinii na temat odbytych zajęć i prowadzącego.

Prowadzący, nauczyciel, powinien mieć wgląd w grupy, które prowadzi. Powinny one też być widoczne na jego kalendarzu, rozróżnione od grup, w których uczestniczy w wypadku, w którym ten jest zarówno studentem jak i nauczycielem. Nauczyciel powinien też móc wylistować studentów znajdujących się w grupie zajęciowej, którą prowadzi, a także odczytać szczegóły na ich temat. Z założenia, student nie widzi informacji na temat innych studentów, tak samo jak prowdzący, który studenta niczego nie uczył.

Na koniec, prowadzący powinien być w stanie wystawić studentowi ocenę z grupy zajęciowej, którą prowadzi. Oceny przyjmują wartości ze skali 2.0 - 5.0, a każda inna wartość jest odrzucana przez API. Każdy typ zajęć w ramach przedmiotu (np. wykład, laboratorium) ma w bazie danych przypisaną wagę. Na podstawie tych wag warstwa API wylicza średnią ocen studenta. Ocena z przedmiotu jest średnią ważoną ocen z poszczególnych typów zajęć (liczoną dla najnowszego podejścia, w którym wszystkie typy zajęć zostały ocenione), a średnia ze studiów jest średnią ocen z przedmiotów ważoną punktami ECTS. Średnia jest widoczna dla prowadzącego w szczegółach studenta, natomiast student widzi oceny z poszczególnych grup zajęciowych.

Administrator powinien być w stanie z poziomu klienta stworzyć wszystkie węzły i krawędzie istniejące w bazie danych bez konieczności samodzielnego pisania kwerend. Jednocześnie, powinien być w stanie nadawać i odbierać role, aktywować i dezaktywować konta, a także je usuwać. Usunięcie konta odbiera jedynie możliwość logowania, a dane osoby i jej historia pozostają w bazie. Administrator może również zapisać studenta do grupy zajęciowej z pominięciem tur rejestracyjnych, opcjonalnie także z pominięciem limitu miejsc. Dodatkowo, formularze do tworzenia elementów systemu uczelnianego powinny ułatwiać administratorowi tworzenie odpowiednich zapytań poprzez wybieralne listy - bez tego administrator musiałby znać identyfikatory "na pamięć" lub odszukiwać je osobnym zapytaniem.

3.3 Wymagania niefunkcjonalne

Najważniejszym wymaganiem niefunkcjonalnym będzie bezpieczeństwo, rozumiane jako poufność, integralność i dostępność. Poufność należy zapewnić poprzez odpowiednie uwierzytelnienie i wynikającą z niej autoryzację. Procesy uwierzytelniające koniecznie muszą się odbywać po stronie serwera, a nie klienta. Przechowywane hasła muszą być zahashowane - przechowywane w postaci wyników jednostronnej funkcji skrótu. Należy wprowadzić dodatkowe utwardzenie haseł, chociażby w postaci soli. Powinna być egzekwowana zasada najmniejszych uprawnień, dotycząca zarówno użytkowników, jak i osób zarządzających infrastrukturą platformy.

Należy dążyć do integralności danych poprzez narzucanie ograniczeń typów danych, w szczególności w warstwie bazy danych. Można też wymusić istnienie danych i dozwolone sposoby ich połączenia. Tam, gdzie nie jest możliwe wprowadzenie ograniczeń w samej bazie, należy dokonać dodatkowej walidacji w warstwie API.

Wysoka dostępność nie jest wymagana od prototypu.

Niedopuszczalne są nieobsłużone warunki wyścigu (ang. *race conditions*) wynikające z jednoczesnego uruchomienia funkcji przez kilku użytkowników, a także niezdefiniowane anomalie wynikające z brudnych odczytów (ang. *dirty read*), odczytów niepowtarzalnych (ang. *non-repeatable read*) i odczytów widmo (ang. *phantom read*).

W celu uzyskania przenośności, środowisko wykorzystuje kontenery Docker. Dzięki temu każdy z zainstalowanym oprogramowaniem Docker może przetestować je lokalnie. Zakłada to, że programista ma dostęp do internetu, a zasady proxy lub inne ograniczenia sieciowe pozwalają mu pobrać niezbędne kontenery i narzędzia.

3.4 Model uprawnień

Dostęp do funkcji wynika z roli użytkownika, a w ramach roli dodatkowo z jego powiązań z innymi elementami uczelni - np. prowadzący widzi tylko studentów ze swoich grup. Osoba z kilkoma rolami ma uprawnienia wszystkich z nich. W kolumnie „Uwagi” opisano, kiedy dostęp jest ograniczony.

Tabela 3.1. Funkcje wspólne

| Funkcja         | Student | Prowadzący | Administrator | Uwagi                                                                           |
| --------------- | :-----: | :--------: | :-----------: | ------------------------------------------------------------------------------- |
| Logowanie       |   tak   |    tak     |      tak      | tylko aktywne konta                                                             |
| Katalog uczelni |   tak   |    tak     |      tak      |                                                                                 |
| Odczyt opinii   |   tak   |    tak     |      tak      | opinie są anonimowe                                                             |
| Plan zajęć      |   tak   |    tak     |      tak      | student i prowadzący widzą swój plan, administrator plan dowolnego prowadzącego |

Tabela 3.2. Funkcje studenta i prowadzącego

| Funkcja | Student | Prowadzący | Administrator | Uwagi |
| --- | :---: | :---: | :---: | --- |
| Plan studiów, semestry i oceny | tak | nie | nie | tylko własne |
| Przeglądanie rejestracji | tak | nie | nie | tylko te, do których tury student jest przypisany |
| Zapis do grupy | tak | nie | tak | student tylko do grup ze swojej rejestracji, jedna grupa danego typu na przedmiot, w ramach limitu miejsc; administrator bez rejestracji (dziekanat) |
| Wypis z grupy | tak | nie | nie | tylko z grup ze swojej rejestracji |
| Wystawienie opinii | tak | nie | tak | tylko o grupie, do której student jest zapisany, i jej prowadzącym, raz na grupę i prowadzącego; administrator w imieniu studenta |
| Lista prowadzonych grup | nie | tak | tak | prowadzący swoje, administrator dowolnego prowadzącego |
| Lista studentów w grupie | nie | tak | tak | prowadzący tylko w swoich grupach |
| Szczegóły studenta | nie | tak | tak | prowadzący tylko studentów, których uczy lub uczył |
| Wystawienie oceny | nie | tak | tak | prowadzący tylko w swoich grupach |

Tabela 3.3. Funkcje administracyjne

| Funkcja | Student | Prowadzący | Administrator |
| --- | :---: | :---: | :---: |
| Tworzenie osób i kont | nie | nie | tak |
| Aktywacja, dezaktywacja i usuwanie kont | nie | nie | tak |
| Nadawanie i odbieranie ról | nie | nie | tak |
| Tworzenie struktury uczelni | nie | nie | tak |
| Przypisywanie prowadzących i studentów | nie | nie | tak |
| Tworzenie rejestracji i tur | nie | nie | tak |

3.5 Przypadki użycia

Kto może korzystać z jakich funkcji, pokazuje macierz uprawnień w sekcji 3.4. Poniżej opisano przebieg trzech najważniejszych procesów, wraz z sytuacjami, w których system odmawia wykonania operacji.

**Zapis na zajęcia**

Aktor: student.

1. Student otwiera listę swoich rejestracji. Widzi tylko te, do których tury został przypisany, wraz z numerem tury, datą i godzinami.
2. Wybiera rejestrację i widzi listę przedmiotów, do których grup może się w niej zapisać.
3. Wybiera przedmiot i widzi jego grupy zajęciowe: typ, numer, termin, salę, prowadzącego oraz liczbę zajętych i wszystkich miejsc.
4. Wybiera grupę i zapisuje się do niej.
5. System zapisuje studenta do grupy i aktualizuje liczbę zajętych miejsc.

Sytuacje alternatywne:
- Grupa nie ma wolnych miejsc - system odrzuca zapis.
- Student jest już zapisany do innej grupy tego samego typu w ramach przedmiotu (np. do innego laboratorium) - system odrzuca zapis. Aby zmienić grupę, student musi się najpierw wypisać z dotychczasowej.
- Grupa nie należy do rejestracji, do której student ma dostęp - system odrzuca zapis.
- Kilku studentów jednocześnie zapisuje się na ostatnie wolne miejsce - zapisuje się tylko jeden z nich, pozostali dostają informację o braku miejsc.

**Wystawienie oceny**

Aktor: prowadzący.

1. Prowadzący otwiera listę swoich grup zajęciowych.
2. Wybiera grupę i widzi listę zapisanych do niej studentów wraz z dotychczasowymi ocenami.
3. Dla wybranych studentów wybiera ocenę ze skali 2,0-5,0 i zapisuje zmiany.
4. System zapisuje oceny. Na ich podstawie, z uwzględnieniem wag typów zajęć, wyliczana jest średnia studenta.

Sytuacje alternatywne:
- Prowadzący próbuje ocenić studenta w grupie, której nie prowadzi - system odmawia dostępu.
- Ocena spoza skali - system ją odrzuca.

**Wystawienie opinii**

Aktor: student.

1. Student otwiera listę grup, do których jest zapisany, wraz z ich prowadzącymi.
2. Dla wybranej grupy i prowadzącego podaje ocenę od 2 do 5 i opcjonalnie komentarz.
3. System zapisuje opinię. Jest ona widoczna w katalogu przy grupie i przy prowadzącym, bez informacji o autorze.

Sytuacje alternatywne:
- Student wystawił już opinię o tej grupie i tym prowadzącym - system odrzuca kolejną.
- Student nie jest zapisany do grupy albo wskazana osoba jej nie prowadzi - system odrzuca opinię.

