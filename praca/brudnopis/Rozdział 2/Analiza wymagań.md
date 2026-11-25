3.1 Kto może korzystać z systemu

Z założenia, prototyp powinien obsługiwać trzy niezbędne role - student, nauczyciel oraz administrator. W prawdziwym systemie USOS lub podobnej platformie uczelnianej ról jest więcej, bo są jeszcze inni pracownicy uczelni, ale te trzy to zupełne minimum, by system był użyteczny. 

Jednocześnie, jedna osoba powinna być w stanie bezproblemowo przy pomocy jednego konta mieć dostęp do funkcji zależnych od wielu ról jednocześnie. Czyli nauczyciel, który jednocześnie studiuje na tej samej uczelni powinien być w stanie zarządzać jednym kontem zarówno zajęciami, które prowadzi, jak i swoim uczestnictwem w zajęciach prowadzonych przez innych. Dostęp do tych funkcji, ograniczony przez autoryzację w punktach końcowych API, powinien być odzwierciedlony w aplikacji klienckiej - nie powinna być widoczna zakładka, do której użytkownik nie ma dostępu. Jednocześnie bardzo ważna jest walidacja po stronie serwera - samo ograniczenie widoczności nie zapewnia bezpieczeństwa, ponieważ z API można komunikować się bezpośrednio, z pominięciem aplikacji klienckiej, np. za pomocą narzędzi do testowania API lub własnych programów.

System ma wspierać zarówno dane obecne, jak i archiwalne. Odebranie dostępu osobie, która przestała korzystać z systemu, ma być możliwe poprzez usunięcie bądź dezaktywację jej konta. Jeśli ktoś odejdzie z uczelni, jego dane mają pozostać w systemie, nawet jeśli ta osoba już nie ma możliwości zalogowania.

3.2 Wymagania funkcjonalne

Użytkownik z utworzonym kontem powinien mieć możliwość zalogowania się poprzez wpisanie adresu e-mail i hasła. Konta powinny być tworzone wyłącznie administracyjnie, bez możliwości rejestracji przez osoby trzecie. Role i uprawnienia również powinny być przyznawane wyłącznie z poziomu administracyjnego.

Każdy zalogowany użytkownik powinien mieć dostęp do katalogu. Katalog powinien pozwalać na przeglądanie informacji o uczelni, zarówno w całości, jak i po przefiltrowaniu. Informacje te powinny obejmować wydziały, kierunki, semestry, przedmioty, grupy zajęciowe oraz prowadzących.

Z racji tego, że każdy zalogowany użytkownik pełni rolę studenta, prowadzącego lub administratora, każdy powinien mieć dostęp do planu zajęć na kolejne tygodnie. Plan powinien uwzględniać również podział na tygodnie parzyste i nieparzyste. Nie musi natomiast rozpoznawać świąt, dni rektorskich ani innych wydarzeń, które mogłyby przesunąć lub odwołać zajęcia danego dnia.

Student powinien mieć możliwość podglądu własnego planu studiów oraz dotychczas odbytych semestrów na kierunkach, na których jest zapisany. Powinien mieć też dostęp do przypisanych mu tur rejestracyjnych w odpowiednich rejestracjach oraz możliwość zapisu do grup objętych daną rejestracją i wypisu z nich. Dla każdego typu grupy zajęciowej w ramach przedmiotu student powinien móc zapisać się do co najwyżej jednej grupy. Pojemność grupy zajęciowej powinna być śledzona na bieżąco, a próby zapisu do grupy bez wolnych miejsc powinny być odrzucane.

Student powinien również mieć możliwość odczytu ocen otrzymanych w ramach przedmiotów i grup zajęciowych, a także wystawienia opinii o odbytych zajęciach i ich prowadzącym.

Prowadzący (nauczyciel) powinien mieć wgląd w prowadzone przez siebie grupy. Powinny być one widoczne w jego kalendarzu, z odróżnieniem od grup, w których uczestniczy, jeśli pełni jednocześnie rolę studenta i nauczyciela. Nauczyciel powinien też móc wyświetlić listę studentów zapisanych do prowadzonej grupy zajęciowej oraz odczytać szczegółowe informacje o nich. Student nie powinien mieć dostępu do informacji o innych studentach.

Prowadzący powinien ponadto móc wystawić studentowi ocenę z prowadzonej grupy zajęciowej. Oceny powinny przyjmować wartości ze skali 2.0–5.0, a każda inna wartość powinna zostać odrzucona. Każdy typ zajęć w ramach przedmiotu (np. wykład, laboratorium) ma przypisaną wagę. Ocena z przedmiotu jest średnią ważoną ocen z poszczególnych typów zajęć. Jeśli którakolwiek z tych ocen jest negatywna (niższa niż 3.0), ocena z przedmiotu wynosi 2.0, ponieważ niezaliczenia jednej formy zajęć nie może zrównoważyć dobra ocena z innej. Średnia ze studiów jest średnią ocen z przedmiotów ważoną punktami ECTS (ang. *European Credit Transfer and Accumulation System*). Średnia powinna być widoczna dla prowadzącego w szczegółach studenta, natomiast student powinien widzieć oceny z poszczególnych grup zajęciowych.

Administrator powinien móc z poziomu aplikacji klienckiej tworzyć wszystkie elementy struktury uczelni i powiązania między nimi, bez bezpośredniego dostępu do bazy danych. Jednocześnie powinien móc nadawać i odbierać role, aktywować i dezaktywować konta, a także je usuwać. Usunięcie konta powinno odbierać jedynie możliwość logowania, przy zachowaniu danych osoby i jej historii w bazie. Dodatkowo formularze do tworzenia elementów struktury uczelni powinny umożliwiać wybór powiązanych elementów z list, tak aby administrator nie musiał znać ich identyfikatorów z pamięci ani wyszukiwać ich osobno.

3.3 Wymagania niefunkcjonalne

Najważniejszym wymaganiem niefunkcjonalnym będzie bezpieczeństwo, rozumiane jako poufność, integralność i dostępność. Poufność należy zapewnić poprzez odpowiednie uwierzytelnienie i wynikającą z niej autoryzację. Procesy uwierzytelniające koniecznie muszą się odbywać po stronie serwera. Hasła muszą być przechowywane w postaci wyników jednokierunkowej funkcji skrótu. Należy wprowadzić dodatkowe utwardzenie haseł, chociażby w postaci soli. Powinna być egzekwowana zasada najmniejszych uprawnień, dotycząca zarówno użytkowników, jak i osób zarządzających infrastrukturą platformy. Ruch sieciowy pomiędzy elementami platformy musi być zaszyfrowany.

Należy dążyć do integralności danych poprzez narzucanie ograniczeń typów danych, w szczególności w warstwie bazy danych. Można też wymusić istnienie danych i dozwolone sposoby ich połączenia. Tam, gdzie nie jest możliwe wprowadzenie ograniczeń w samej bazie, należy dokonać dodatkowej walidacji w warstwie API.

Wysoka dostępność nie jest wymagana od prototypu.

Niedopuszczalne są nieobsłużone warunki wyścigu wynikające z jednoczesnego uruchomienia funkcji przez kilku użytkowników, a także niezdefiniowane anomalie wynikające z brudnych odczytów, odczytów niepowtarzalnych i odczytów widmo (2.1).

W celu uzyskania przenośności, środowisko powinno wykorzystywać konteneryzację. Dzięki temu każdy z zainstalowanym oprogramowaniem Docker może przetestować je lokalnie. Zakłada to, że programista ma dostęp do internetu, a zasady proxy lub inne ograniczenia sieciowe pozwalają mu pobrać niezbędne kontenery i narzędzia.

3.4 Model uprawnień

Dostęp do funkcji wynika z roli użytkownika, a w ramach roli dodatkowo z jego powiązań z innymi elementami uczelni - np. prowadzący widzi tylko studentów ze swoich grup. Osoba z kilkoma rolami ma uprawnienia wszystkich z tych ról.

Tabela 3.1. Funkcje wspólne

| Funkcja         | Student | Prowadzący | Administrator | Uwagi                                                                           |
| --------------- | :-----: | :--------: | :-----------: | ------------------------------------------------------------------------------- |
| Logowanie       |   tak   |    tak     |      tak      | tylko aktywne konta                                                             |
| Katalog uczelni |   tak   |    tak     |      tak      |                                                                                 |
| Odczyt opinii   |   tak   |    tak     |      tak      | autor opinii jest niewidoczny dla innych użytkowników (pseudonimizacja)         |
| Plan zajęć      |   tak   |    tak     |      tak      | student i prowadzący widzą swój plan, administrator plan dowolnego prowadzącego |

Tabela 3.2. Funkcje studenta i prowadzącego

| Funkcja | Student | Prowadzący | Administrator | Uwagi |
| --- | :---: | :---: | :---: | --- |
| Plan studiów, semestry i oceny | tak | nie | nie | tylko własne |
| Przeglądanie rejestracji | tak | nie | nie | tylko te, do których tury student jest przypisany |
| Zapis do grupy | tak | nie | tak | student tylko do grup ze swojej rejestracji, jedna grupa danego typu na przedmiot, w ramach limitu miejsc; administrator bez rejestracji (dziekanat) |
| Wypis z grupy | tak | nie | nie | tylko z grup ze swojej rejestracji |
| Wystawienie opinii | tak | nie | nie | tylko o grupie, do której student jest zapisany, i jej prowadzącym, raz na grupę i prowadzącego |
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

Zakres funkcji dostępnych dla poszczególnych ról przedstawiono w macierzy uprawnień (3.4). Poniżej opisano przebieg trzech najważniejszych procesów biznesowych platformy, natomiast warunki odmowy i sytuacje wyjątkowe dla wszystkich trzech procesów zestawiono w tabeli 3.4.

**Zapis na zajęcia (student).** Student otwiera listę swoich rejestracji, na której widzi wyłącznie akcje z przypisaną mu turą wraz z numerem tury, datą i godzinami. Po wyborze rejestracji i przedmiotu przegląda dostępne grupy zajęciowe (typ, numer, termin, salę, prowadzącego oraz liczbę zajętych i wszystkich miejsc), a następnie zapisuje się do wybranej grupy. System utrwala zapis i na bieżąco aktualizuje liczbę zajętych miejsc.

**Wystawienie oceny (prowadzący).** Prowadzący otwiera listę prowadzonych przez siebie grup, po czym wybiera konkretną grupę, aby wyświetlić listę zapisanych do niej studentów wraz z dotychczasowymi ocenami. Dla wybranych studentów wprowadza oceny ze skali 2,0–5,0 i zatwierdza zmiany. System zapisuje oceny, a na ich podstawie – z uwzględnieniem wag poszczególnych form zajęć – wyznaczana jest średnia studenta.

**Wystawienie opinii (student).** Student otwiera listę grup, do których jest zapisany, wraz z przypisanymi do nich prowadzącymi. Dla wybranej pary grupa–prowadzący podaje ocenę w skali 2,0–5,0 oraz opcjonalny komentarz. Zapisana opinia trafia do katalogu i jest widoczna przy grupie oraz przy prowadzącym, bez danych autora (pseudonimizacja) i wyłącznie z datą wystawienia.

Tabela 3.4. Warunki odmowy i sytuacje wyjątkowe w głównych przypadkach użycia

| Proces (aktor) | Sytuacja wyjątkowa / warunek odmowy | Oczekiwana reakcja systemu |
| --- | --- | --- |
| Zapis na zajęcia (student) | brak wolnych miejsc w grupie | odrzucenie zapisu |
| | jednoczesny zapis wielu studentów na ostatnie wolne miejsce | zapis wyłącznie jednego studenta; pozostali otrzymują informację o braku miejsc |
| | student jest już zapisany do innej grupy tego samego typu w ramach przedmiotu | odrzucenie zapisu (zmiana wymaga wcześniejszego wypisu z dotychczasowej grupy) |
| | grupa nie należy do rejestracji dostępnej dla studenta lub tura nie trwa | odmowa dostępu |
| Wystawienie oceny (prowadzący) | próba oceny studenta w grupie, której użytkownik nie prowadzi | odmowa dostępu |
| | wartość oceny spoza skali 2,0–5,0 | odrzucenie operacji |
| Wystawienie opinii (student) | student wystawił już opinię o tej samej parze grupa–prowadzący | odrzucenie kolejnej opinii |
| | brak zapisu studenta do grupy lub wskazana osoba jej nie prowadzi | odrzucenie opinii |


