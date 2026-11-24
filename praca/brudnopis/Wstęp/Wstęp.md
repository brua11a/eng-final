1.1 Wprowadzenie

Relacyjne bazy danych, oparte na tabelach, kluczach obcych i języku SQL (ang. *Structured Query Language*), przez dekady były dominującym sposobem przechowywania danych w systemach informatycznych [CYTOWANIE]. Alternatywę dla nich stanowią bazy grafowe, w których dane reprezentowane są jako węzły połączone krawędziami. Powiązania stanowią tam bezpośredni element modelu danych, co eliminuje konieczność łączenia tabel podczas wykonywania zapytań [CYTOWANIE]. Jedną z najpopularniejszych baz tego typu jest Neo4j, wykorzystująca model grafu właściwości (ang. *property graph*), w którym zarówno węzły, jak i krawędzie mogą posiadać atrybuty, a węzły dodatkowo etykiety [CYTOWANIE]. Dane w Neo4j odpytuje się za pomocą deklaratywnego języka Cypher [CYTOWANIE].

Struktura uczelni jest z natury silnie powiązana: studenci należą do grup, grupy do przedmiotów, przedmioty do kierunków, a prowadzący, sale i terminy dodatkowo łączą te elementy ze sobą. W Politechnice Wrocławskiej funkcję systemu obsługującego studia, w tym rejestrację na zajęcia, pełni USOS (Uniwersytecki System Obsługi Studiów). Obok tego studenci stworzyli forum PolWro, w którym mogą wystawiać opinie na temat prowadzących grup zajęciowych.

Pomysł na podjęcie tematu pojawił się podczas zajęć laboratoryjnych z przedmiotu „Bazy danych”, na których zadano zaprojektowanie struktury uczelnianej na potrzeby czyjejś aplikacji. Miała ona przypominać hybrydę USOSa i forum PolWro. Ponieważ wtedy w grupie nie znano baz innych niż relacyjne, tabele stały się naturalnym, bo jedynym wyborem.

W trakcie konceptualnego rozpisywania potrzebnych zapytań i po osiągnięciu trzeciej postaci normalnej (3NF, ang. *Third Normal Form*), okazało się, że uzyskanie z bazy danych przydatnej informacji wymagało czterokrotnego lub nawet pięciokrotnego wykorzystania instrukcji JOIN. Były to zapytania, których nie dało się zastąpić podzapytaniami (ang. *subqueries*), a gęsta sieć powiązań między encjami wynikała bezpośrednio z samej domeny uczelnianej.

Po kilku miesiącach autor zainteresował się grafowymi bazami danych. W tej strukturze silne powiązanie ze sobą danych jest wręcz oczekiwane, co skłoniło autora do zastanowienia się, czy struktura uczelni nie jest lepiej opisywana grafem niż tabelami. Wielokrotne instrukcje JOIN zastępuje przeszukiwanie grafu, skomplikowane powiązania wiele-do-wielu znikają na rzecz krawędzi, a role spełniane przez osoby w uczelni są nieodłączną częścią samych osób, zamiast być reprezentowane kluczami obcymi.

Platforma uczelniana przechowuje dane o różnym stopniu poufności i jest używana przez użytkowników o różnych uprawnieniach: studentów, prowadzących i administratorów. Kontrola dostępu jest zatem jej nieodłączną częścią. W pracy zbadano możliwość wykorzystania bazy grafowej zarówno do przechowywania danych, jak i do opisu uprawnień w modelu kontroli dostępu opartej na rolach (RBAC, ang. _Role-Based Access Control_) i relacjach (ReBAC, ang. _Relationship-Based Access Control_) [CYTOWANIE].

Zapewnienie, że użytkownik ma dostęp wyłącznie do danych niezbędnych do wykonywania jego zadań (zasada najmniejszych uprawnień, ang. _principle of least privilege_), jest jednym z podstawowych wymagań poufności i integralności danych, tym istotniejszym, że system przetwarza dane osobowe studentów [CYTOWANIE].


1.2 Cel i zakres pracy

Celem pracy jest zaprojektowanie i implementacja prototypu platformy uczelnianej, inspirowanej systemem USOS i forum PolWro, udostępniającej funkcje dla studenta, prowadzącego i administratora oraz wykorzystującej grafową bazę danych Neo4j zarówno do przechowywania danych, jak i do opisu uprawnień użytkowników. Dodatkowo struktura danych zostanie odwzorowana w modelu relacyjnym, aby porównać złożoność zapytań w obu podejściach.

Do realizacji celu zaplanowano następujące zadania:  
- zaprojektowanie grafowego modelu danych dla wybranych fragmentów struktury uczelni, 
- zapewnienie integralności danych poprzez ograniczenia (ang. _constraints_) narzucone na poziomie bazy danych,  
- implementacja kontroli dostępu w warstwie interfejsu programistycznego aplikacji (API, ang. *Application Programming Interface*) w modelu RBAC, uzupełnionym o elementy ReBAC, z rolami i relacjami przechowywanymi w grafie oraz z wykorzystaniem wieloetykietowości (ang. _multilabeling_) i implikowanych etykiet (ang. _implied labels_),
- implementacja uwierzytelniania opartego na tokenach, z przechowywaniem haseł w postaci skrótów (haszy),
- przygotowanie API udostępniającego funkcje platformy,  
- wykonanie prostej aplikacji klienckiej działającej w przeglądarce,  
- opis mechanizmów Neo4j wykorzystanych w projekcie (typy grafu, ograniczenia, etykiety),
- odwzorowanie modelu danych w postaci relacyjnej i porównanie przykładowych zapytań (liczby złączeń oraz czasu wykonania) z ich odpowiednikami w języku Cypher.

Zakres funkcji obejmuje przede wszystkim proces zapisu na zajęcia, przeglądanie katalogu oferty dydaktycznej, wystawianie opinii i ocen oraz zarządzanie strukturą uczelni przez administratora. Szczegółowe wymagania przedstawiono w rozdziale 3. Prototyp zrealizowano w postaci API w języku Python (FastAPI) i aplikacji klienckiej w Vue, uruchamianych w kontenerach Docker.

Poza zakresem pracy pozostają inne funkcje systemu USOS, w szczególności obsługa stypendiów i podań. Praca nie obejmuje również skalowania ani wdrożenia produkcyjnego. 

1.3 Układ pracy
Napiszę jak bede wiedział jakie są rozdziały

1.4 Wykorzystanie narzędzi sztucznej inteligencji
W pracy korzystano z narzędzi sztucznej inteligencji (AI, ang. *Artificial Intelligence*) takich jak Claude Code i Antigravity. Wykorzystywano modele Claude Opus 5.5 oraz Claude Haiku 5.5 od firmy Anthropic, a także Gemini Neon 4 od firmy Google. Służyły one do generowania danych testowych, przeprowadzania i pisania testów oraz do pisania kodu aplikacji klienckiej. Wykorzystano je również do szukania w dokumentacji konkretnych cytatów, redagowania tekstu pracy inżynierskiej i formatowania dokumentu w LaTeX. 