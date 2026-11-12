1.1 Wprowadzenie

Relacyjne bazy danych, oparte na tabelach, kluczach obcych i języku SQL (ang. *Structured Query Language*), przez dekady były dominującym sposobem przechowywania danych w systemach informatycznych [CYTOWANIE]. Alternatywę dla nich stanowią bazy grafowe, w których dane reprezentowane są jako węzły połączone krawędziami, a powiązania są pełnoprawnym elementem modelu, a nie wynikiem złączenia tabel w trakcie zapytania [CYTOWANIE]. Jedną z najpopularniejszych baz tego typu jest Neo4j, wykorzystująca model grafu właściwości (ang. property graph), w którym zarówno węzły, jak i krawędzie mogą posiadać atrybuty, a węzły dodatkowo etykiety [CYTOWANIE]. Dane w Neo4j odpytuje się za pomocą deklaratywnego języka Cypher [CYTOWANIE].

Struktura uczelni jest z natury silnie powiązana: studenci należą do grup, grupy do przedmiotów, przedmioty do kierunków, a prowadzący, sale i terminy dodatkowo łączą te elementy ze sobą. W Politechnice Wrocławskiej funkcję systemu obsługującego studia, w tym rejestrację na zajęcia, pełni USOS (Uniwersytecki System Obsługi Studiów). Obok tego studenci stworzyli forum PolWro, w którym mogą wystawiać opinie na temat prowadzących grup zajęciowych.

Pomysł na podjęcie tematu pojawił się podczas zajęć laboratoryjnych z przedmiotu „Bazy danych“, na których zadano zaprojektowanie struktury uczelnianej na potrzeby czyjejś aplikacji. Miała ona przypominać hybrydę USOSa i forum PolWro. Ponieważ wtedy w grupie nie znano baz innych niż relacyjne, tabele stały się naturalnym, bo jedynym wyborem.

W trakcie konceptualnego rozpisywania potrzebnych zapytań i po osiągnięciu trzeciej postaci normalnej (3NF, ang. *Third Normal Form*), okazało się, że uzyskanie z bazy danych przydatnej informacji wymagało czterokrotnego lub nawet pięciokrotnego wykorzystania instrukcji JOIN. Były to zapytania, których nie dało się obsłużyć podzapytaniami (ang. *subqueries*), a silne powiązanie encji wynikało z domeny, nie z implementacji.

Po kilku miesiącach autor zainteresował się grafowymi bazami danych. W tej strukturze silne powiązanie ze sobą danych jest naturalne, co skłoniło autora do zastanowienia się, czy struktura uczelni nie jest lepiej opisywana grafem niż tabelami. Wielokrotne instrukcje JOIN zastępuje przeszukiwanie grafu, skomplikowane powiązania wiele-do-wielu znikają na rzecz krawędzi, a role spełniane przez osoby w uczelni są nieodłączną częścią samych osób, zamiast być reprezentowane kluczami obcymi.

Platforma uczelniana przechowuje dane o różnym stopniu poufności i jest używana przez użytkowników o różnych uprawnieniach: studentów, prowadzących i administratorów. Kontrola dostępu jest zatem jej nieodłączną częścią. W tradycyjnych rozwiązaniach realizuje się ją osobno, w warstwie aplikacji, podczas gdy w modelu grafowym uprawnienia wynikają z tych samych węzłów i relacji, które opisują domenę. Dlatego w pracy zbadano możliwość wykorzystania bazy grafowej zarówno do przechowywania danych, jak i do opisu uprawnień w modelu kontroli dostępu opartej na rolach (RBAC, ang. _Role-Based Access Control_) i relacjach (ReBAC, ang. _Relationship-Based Access Control_) [CYTOWANIE].

Zapewnienie, że użytkownik ma dostęp wyłącznie do danych niezbędnych do wykonywania jego zadań (zasada najmniejszych uprawnień, ang. _principle of least privilege_), jest jednym z podstawowych wymagań poufności i integralności danych, tym istotniejszym, że system przetwarza dane osobowe studentów [CYTOWANIE].


1.2 Cel i zakres pracy
Celem pracy jest zaprojektowanie i implementacja prototypu platformy uczelnianej, inspirowanej systemem USOS i forum PolWro, udostępniającej funkcje dla studenta, prowadzącego i administratora oraz wykorzystującej grafową bazę danych Neo4j zarówno do przechowywania danych, jak i do opisu uprawnień użytkowników, na podstawie którego API kontroluje dostęp. Dodatkowo struktura danych zostanie odwzorowana w modelu relacyjnym, aby porównać złożoność zapytań w obu podejściach.

Do realizacji celu zaplanowano następujące zadania:  
- zaprojektowanie grafowego modelu danych dla wybranego fragmentu struktury uczelni,  
- zapewnienie integralności danych poprzez ograniczenia (ang. _constraints_) narzucone na poziomie bazy danych,  
- implementacja dedykowanej kontroli dostępu w warstwie API w modelu RBAC, uzupełnionym o elementy ReBAC, z rolami i relacjami przechowywanymi w grafie oraz z wykorzystaniem wieloetykietowości (ang. _multilabeling_) i implikowanych etykiet (ang. _implied labels_),
- implementacja uwierzytelniania opartego na tokenach, z przechowywaniem haseł w postaci skrótów (haszy),
- przygotowanie interfejsu programistycznego (API, ang. *Application Programming Interface*) udostępniającego funkcje platformy,  
- wykonanie prostej aplikacji klienckiej działającej w przeglądarce,  
- opis mechanizmów Neo4j wykorzystanych w projekcie (typy grafu, ograniczenia, etykiety),
- odwzorowanie modelu danych w postaci relacyjnej i porównanie przykładowych zapytań (liczby złączeń oraz czasu wykonania) z ich odpowiednikami w języku Cypher.

Zakres funkcji obejmuje przede wszystkim proces zapisu na zajęcia: tury rejestracyjne, grupy zajęciowe oraz zapisy na nie, z perspektywy studenta. Konta użytkowników zakłada administrator - samodzielna rejestracja nowego konta nie jest przewidziana. Student może ponadto przeglądać katalog przedmiotów, programów zajęć, kursów i prowadzących oraz wystawiać opinie o grupach zajęciowych i prowadzących. Zaimplementowano również niezbędne funkcje dla prowadzącego, takie jak wystawianie ocen. Z poziomu administracyjnego przygotowano punkty końcowe API (ang. _endpoints_) umożliwiające tworzenie i zarządzanie elementami struktury uczelni bez bezpośredniego dostępu do bazy danych. Prototyp zrealizowano w postaci API w języku Python (FastAPI) i aplikacji klienckiej w Vue, uruchamianych w kontenerach Docker. Poza zakresem pracy pozostają inne funkcje systemu USOS, w szczególności obsługa stypendiów i podań. Praca nie obejmuje również skalowania ani wdrożenia produkcyjnego. 

Role i relacje stanowiące podstawę uprawnień przechowywane są w grafie, natomiast decyzję o udzieleniu dostępu podejmuje warstwa API na podstawie roli zapisanej w tokenie oraz relacji sprawdzanych kwerendą do bazy. Baza danych egzekwuje wyłącznie integralność danych (ograniczenia), a nie uprawnienia użytkowników: aplikacja łączy się z nią jednym kontem technicznym, bez tworzenia osobnego konta bazodanowego dla każdego użytkownika uczelni. Aplikacja kliencka ogranicza jedynie widoczność elementów interfejsu. Praca nie obejmuje testów penetracyjnych ani audytu bezpieczeństwa.

1.3 Układ pracy
Napiszę jak bede wiedział jakie są rozdziały