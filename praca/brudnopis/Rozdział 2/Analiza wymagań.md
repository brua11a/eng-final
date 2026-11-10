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
Najważniejszym wymaganiem niefunkcjonalnym będzie bezpieczeństwo, rozumiane jako poufność, integralność i dostępność. Poufność należy zapewnić poprzez odpowiednie uwierzytelnienie i wynikającą z niej autoryzację. Procesy uwierzytelniające koniecznie muszą się odbywać po stronie serwera, a nie klienta. Przechowywane hasła muszą być zahashowane - przechowywane w postaci wyników jednostronnej funkcji skrótu. Należy rozważyć dodatkowe utwardzenie haseł, np. w postaci soli. Powinna być egzekwowana zasada najmniejszych uprawnień, dotycząca zarówno użytkowników, jak i osób zarządzających infrastrukturą platformy.

Należy dążyć do integralności danych poprzez narzucanie ograniczeń typów danych, w szczególności w warstwie bazy danych. Można też wymusić istnienie danych i dozwolone sposoby ich połączenia. Tam, gdzie nie jest możliwe wprowadzenie ograniczeń w samej bazie, należy dokonać dodatkowej walidacji w warstwie API.

Niedopuszczalne są nieobsłużone warunki wyścigu (ang. *race conditions*) wynikające z jednoczesnego uruchomienia funkcji przez kilku użytkowników, a także niezdefiniowane anomalie wynikające z brudnych odczytów (ang. *dirty read*), odczytów niepowtarzalnych (ang. *non-repeatable read*) i odczytów widmo (ang. *phantom read*).

W celu uzyskania przenośności, środowisko wykorzystuje kontenery Docker. Dzięki temu każdy z zainstalowanym oprogramowaniem Docker może przetestować je lokalnie. Zakłada to, że programista ma dostęp do internetu, a zasady proxy lub inne ograniczenia sieciowe pozwalają mu pobrać niezbędne kontenery i narzędzia.

