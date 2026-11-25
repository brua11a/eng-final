7.1 Środowisko i organizacja testów

Testy funkcjonalne, bezpieczeństwa oraz pomiary wydajności przeprowadzono lokalnie na komputerze z procesorem AMD Ryzen 7 5800X (8 rdzeni, 16 wątków, do 4,85 GHz), 16 GB pamięci RAM i dyskiem SSD NVMe ADATA XPG SX8200 Pro 512 GB, pod kontrolą systemu Arch Linux (jądro 7.2.11) oraz środowiska Docker 29.9.2 z Docker Compose (5.1).

Zakres testów oparto na wymaganiach z rozdziału 3. Każdy przypadek zaimplementowano jako niezależny skrypt Pythona w katalogu `tests/`, uruchamiany zbiorczo przez `tests/run_all.py` (z zapisem raportów w `tests/wyniki/`). Żądania kierowano z hosta po HTTPS z weryfikacją lokalnego CA, a operacje pomocnicze (dane testowe, kontrola stanu baz, generowanie tokenów) wykonywano z kontenera `app` z użyciem kont bazodanowych API.

7.2 Uwierzytelnianie i kontrola dostępu

7.2.1 Kontrola dostępu i kolejność sprawdzeń

Mechanizmy RBAC i ReBAC zweryfikowano skryptem `tests/test_permissions.py` dla wszystkich 59 punktów końcowych backendu grafowego pobranych ze specyfikacji OpenAPI (5.4), przy czym macierz uprawnień zdefiniowano na podstawie tabel 3.1–3.3. Każdy punkt końcowy wywołano bez tokenu oraz z rolami studenta, prowadzącego, administratora i osoby łączącej role studenta i prowadzącego.

**Tab. 7.1:** Wyniki testu RBAC dla 59 punktów końcowych (291 żądań)

| Moduł | Punkty końcowe | Bez tokenu | Student | Prowadzący | Administrator | Student i prowadzący |
| --- | ---: | :---: | :---: | :---: | :---: | :---: |
| public (logowanie) | 1 | dostęp | – | – | – | – |
| catalogue | 10 | 401 | dostęp | dostęp | dostęp | dostęp |
| student | 10 | 401 | dostęp | 403 | 403 | dostęp |
| teacher | 4 | 401 | 403 | dostęp | dostęp¹ | dostęp |
| admin | 34 | 401 | 403 | 403 | dostęp | 403 |

*¹ Z wyjątkiem listy własnych grup (`GET /me/groups`), dostępnej wyłącznie dla roli prowadzącego.*

W 16 scenariuszach ReBAC (4.4.2) potwierdzono, że prowadzący ma dostęp wyłącznie do własnych grup i nauczanych studentów, administrator do dowolnej grupy i studenta, student wyłącznie do własnych zapisów, semestrów i opinii o swoich grupach, a użytkownik wielorolowy łączy uprawnienia obu ról przy zachowaniu odmów dla cudzych zasobów. Potwierdza to spełnienie wymagań z 3.1.

Skryptem `tests/test_check_order.py` sprawdzono ponadto kolejność autoryzacji i walidacji (5.5.8): dla trzech błędnych żądań zapisu wywołania bez tokenu, z tokenem studenta i z tokenem administratora zwróciły kolejno kody 401, 403 i dopiero 422, więc komunikaty walidacji pozostają ukryte przed nieuprawnionymi użytkownikami.

7.2.2 Weryfikacja tokenów JWT i czas odpowiedzi logowania

Weryfikację JWT (5.5.6) sprawdzono w 17 przypadkach (`tests/test_jwt.py`) na punkcie końcowym `GET /admin/people/next-idx`: token administratora zwrócił kod 200, token studenta 403, a wszystkie próby manipulacji odrzucono kodem 401. Obejmowały one dopisanie roli `Admin` przy pierwotnym podpisie, algorytm `none`, obcy klucz, podpis właściwym kluczem algorytmem HS512, token wygasły, uszkodzony, bez roszczeń `exp`/`iat`/`sub` lub z błędną strukturą ról (`Invalid token`), token wydany przed startem API (`Token revoked`) oraz brak lub błędny schemat nagłówka `Authorization` (`Not authenticated`). Odrzucenie HS512 mimo właściwego klucza potwierdza, że dozwolony algorytm wymusza wyłącznie serwer.

Odporność `POST /api/login` na atak czasowy (5.5.6) zmierzono skryptem `tests/test_login_timing.py` (30 prób na przypadek, tab. 7.2).

**Tab. 7.2:** Mediana czasu odpowiedzi punktu końcowego `POST /api/login` (30 prób na przypadek)

| Przypadek | Kod | Mediana przed poprawką [ms] | Mediana po poprawce [ms] |
| --- | :---: | ---: | ---: |
| istniejące konto, poprawne hasło | 200 | 185,1 | 182,9 |
| istniejące konto, błędne hasło | 401 | 183,7 | 182,7 |
| nieistniejące konto | 401 | 4,0 | 182,7 |

Wprowadzenie skrótu zastępczego wyrównało czasy odpowiedzi (ok. 183 ms we wszystkich przypadkach), eliminując możliwość wykrycia istnienia konta. Potwierdzono też obsługę 72-bajtowego limitu bcrypt (5.5.6): dla 73-bajtowego hasła `POST /api/admin/users` zwraca po poprawce kod 422 (wcześniej 500).

7.2.3 Cykl życia konta i unieważnianie tokenów

Operacje na kontach (5.5.9) sprawdzono skryptem `tests/test_account_lifecycle.py` na studencie bez konta: utworzenie (201), logowanie (200), dezaktywacja (200) blokująca zarówno logowanie (403), jak i wcześniejszy token (401 `Token revoked`), ponowna aktywacja (200) oraz usunięcie konta (204), po którym logowanie zwraca 401, a dane osoby pozostają dostępne pod `GET /students/{idx}` (200). Potwierdzono także blokadę usunięcia własnego konta administratora (409).

Skutki odebrania roli `Admin` zweryfikowano skryptem `tests/test_role_revocation.py` przed wdrożeniem unieważniania tokenów (5.5.6) i po nim (tab. 7.3).

**Tab. 7.3:** Dostęp do punktów końcowych administratora po odebraniu roli `Admin`

| Krok                                               | Bez unieważniania |  Z unieważnianiem   |
| -------------------------------------------------- | :---------------: | :-----------------: |
| `GET /admin/people/next-idx` przed odebraniem roli |        200        |         200         |
| `GET /admin/people/next-idx` po odebraniu roli     |        200        | 401 `Token revoked` |
| `PATCH /admin/users/281056` z `{"active": false}`  |        200        | 401 `Token revoked` |
| ponowne logowanie i `GET /admin/people/next-idx`   |        403        |         403         |

Mechanizm unieważniania natychmiast blokuje dotychczasowy token kodem 401, zmuszając użytkownika do ponownego logowania już bez odebranej roli.

7.3 Współbieżność

Skuteczność blokad przy równoległych zapisach i modyfikacji ról (5.5.10, 6.4.1) sprawdzono skryptami `tests/test_concurrent_registration.py` (Neo4j) oraz `tests/test_concurrent_registration_rel.py` (PostgreSQL). Scenariusze kontrolne bez blokad (C, C1, C2) uruchomiono bezpośrednio przez sterowniki (w PostgreSQL z 100-milisekundowym opóźnieniem zatwierdzenia, aby wymusić kolizję). Scenariusz D dotyczy wyłącznie backendu grafowego (tab. 7.4).

**Tab. 7.4:** Wyniki testów współbieżności dla backendu grafowego i relacyjnego (trzy uruchomienia, identyczne wyniki)

| Scenariusz | Żądania | Neo4j (odpowiedzi / stan bazy) | PostgreSQL (odpowiedzi / stan bazy) |
| --- | ---: | --- | --- |
| A: 10 studentów, grupa z 3 miejscami | 10 | 3 × 204, 7 × 409 `Group is full` / 3 zapisanych | 3 × 204, 7 × 409 `Group is full` / 3 zapisanych |
| B: 5 studentów, każdy jednocześnie do 2 grup tego samego typu | 10 | 5 × 204, 5 × 409 (konflikt typu) / każdy w 1 grupie | 5 × 204, 5 × 409 (konflikt typu) / każdy w 1 grupie |
| C / C1 (kontrola): jak A, zapytanie bez blokad | 10 | 10 × `ok` / **10 zapisanych** | 10 × `ok` / **10 zapisanych** |
| C2 (kontrola): jak A, blokada i sprawdzenie w jednej instrukcji SQL | 10 | – | 10 × `ok` / **10 zapisanych** |
| D: jednoczesne odebranie obu ról osobie z rolami `Teacher` i `Student` | 2 | 1 × 200, 1 × 409 `Cannot remove last role` / 1 rola | – |

W scenariuszach A, B i D oba backendy zachowały wszystkie ograniczenia. Scenariusze C i C1 pokazują, że przy izolacji *read committed* brak blokad prowadzi do przepełnienia grupy, a C2 potwierdza działanie migawek w PostgreSQL (6.4.1), wymagające rozbicia blokady i zapisu na osobne instrukcje w transakcji.

7.4 Logika dziedzinowa

Funkcję `average_grade()` (3.2, 5.5.5) zweryfikowano 11 testami jednostkowymi (`tests/test_average_grade.py`), obejmującymi średnią ważoną form zajęć, obniżenie oceny z przedmiotu do 2,0 przy pojedynczej ocenie negatywnej, ważenie punktami ECTS, wybór ostatniego pełnego podejścia (z uwzględnieniem kolejności semestrów Z/L), pomijanie niepełnych podejść i przedmiotów bez ECTS, dwie grupy tej samej formy oraz normalizację wag. Test integracyjny potwierdził zgodność średniej zwracanej przez `GET /students/{student_idx}` (3,75) z obliczeniami ręcznymi.

Obsługę tur zapisów i strefy czasowej (3.2, 4.3.4, 5.5.10) sprawdzono skryptem `tests/test_registration_turn.py` na turze wczorajszej, bieżącej i jutrzejszej. W aktywnej turze potwierdzono zapis, idempotentność powtórnego zapisu i wypis (204), brak zapisu przy wypisie (404) oraz odmowę dla cudzej rejestracji (403); poza turą zapis i wypis zwracały 403. Zweryfikowano również zapisywanie godzin jako `LOCAL TIME` oraz wyznaczanie przesunięcia dla strefy `Europe/Warsaw`, co eliminuje dawne godzinne opóźnienie w czasie letnim (tab. 7.5).

**Tab. 7.5:** Początek tury zapisów wyznaczonej na godzinę 8:00 w strefie `Europe/Warsaw`

| Data | Czas lokalny ze strefą (obecnie) | Stałe przesunięcie `+01:00` (dawniej) |
| --- | :---: | :---: |
| 2026-01-15 | 08:00+01:00 | 08:00 |
| 2026-03-28 | 08:00+01:00 | 08:00 |
| 2026-03-29 (zmiana na czas letni) | 08:00+02:00 | **09:00** |
| 2026-07-01 | 08:00+02:00 | **09:00** |
| 2026-10-24 | 08:00+02:00 | **09:00** |
| 2026-10-25 (zmiana na czas zimowy) | 08:00+01:00 | 08:00 |

Reguły opinii (3.4, 3.5, 4.3.5) zweryfikowano skryptem `tests/test_opinions.py`: odrzucenie ocen spoza skali i zbyt długich komentarzy (422), odmowę dla niezapisanego studenta i nieprzypisanego prowadzącego (403), unikalność na parę grupa–prowadzący (201 wobec 409, w tym przy 10 równoległych żądaniach: 1 × 201, 9 × 409) oraz pseudonimizację w `GET /opinions` (brak autora i sama data).

7.5 Integralność danych i uprawnienia kont bazodanowych

7.5.1 Ograniczenia schematu

Skryptem `tests/test_schema_constraints.py` sprawdzono ograniczenia schematu bezpośrednio w Neo4j. Każda z 14 prób niepoprawnego zapisu w osobnej zatwierdzanej transakcji została odrzucona z odpowiednim kodem błędu GQL (ang. *Graph Query Language*, 4.3.7, tab. 7.6).

**Tab. 7.6:** Niepoprawne operacje zapisu odrzucone bezpośrednio przez bazę Neo4j (14 przypadków)

| Kod GQL | Rodzaj ograniczenia | Przetestowane naruszenia |
| :---: | --- | --- |
| 22N78 | typ właściwości | dzień tygodnia, godzina zajęć lub ocena na krawędzi `REGISTERED_IN` zapisane jako tekst |
| 22N77 | istnienie właściwości | grupa bez limitu miejsc, konto `Inactive` bez momentu dezaktywacji, krawędź `REGISTERED_IN` bez `registered_at` |
| 22N79 | unikalność i klucze | duplikat identyfikatora grupy, adresu e-mail, pary (budynek, numer sali), pary (rok, semestr) oraz trójki (imię, nazwisko, telefon) |
| 22NB3 | etykieta implikowana | węzeł `Student` bez etykiety i wymaganych właściwości `Person` |
| 22NB4 | typy węzłów na końcach krawędzi | krawędź `TEACHES` wychodząca od studenta, krawędź `IN_ROOM` prowadząca do przedmiotu |

Potwierdzono także 10 nieegzekwowanych przez `GRAPH TYPE` reguł (4.3.7, 5.3.1), które Neo4j przyjęło, a których pilnuje dopiero API lub Pydantic: dozwolone zakresy wartości, kardynalność powiązań, sumowanie wag do 1 oraz etykietę `Inactive` bez `User` (por. tabela z 6.2.3).

7.5.2 Uprawnienia kont bazodanowych

Zgodność kont bazodanowych API z zasadą najmniejszych uprawnień (3.3, 4.4.3, 6.3) zweryfikowano skryptem `tests/test_db_privileges.py` w wycofywanych transakcjach (tab. 7.7).

**Tab. 7.7:** Wyniki testu uprawnień kont bazodanowych wykorzystywanych przez API

| Operacja | Neo4j | PostgreSQL |
| --- | --- | --- |
| odczyt i zapis danych (kontrola) | dozwolone | dozwolone |
| odczyt pliku serwera bazy | odmowa (`LOAD CSV`) | odmowa (`COPY FROM`, `pg_read_file`) |
| zapis pliku serwera bazy | – | odmowa (`COPY TO`) |
| żądanie do usługi w sieci wewnętrznej (SSRF) | odmowa (`LOAD CSV` z `https://app:8000/...`) | – |
| utworzenie etykiety spoza schematu | odmowa | – |
| modyfikacja schematu | odmowa (ograniczenia, indeksy) | odmowa (`CREATE`, `ALTER`, `DROP TABLE`) |
| wyczyszczenie całej tabeli | – | odmowa (`TRUNCATE`) |
| odczyt listy kont i skrótów haseł | odmowa (`SHOW USERS`) | odmowa (`pg_authid`) |
| utworzenie konta lub nadanie roli | odmowa | odmowa |

Dla nieistniejącej domeny `LOAD CSV` w Neo4j zgłasza błąd sieci przed sprawdzeniem uprawnienia `LOAD`; dla adresów rozwiązywalnych (w tym w sieci Dockera) żądanie HTTP jest blokowane, choć samo zapytanie DNS może się wykonać.

7.6 Szyfrowanie połączeń

Konfigurację TLS (5.1.1, 6.3) sprawdzono testem portów (`tests/test_tls_config.py`) oraz analizą przechwyconego ruchu (`tests/test_tls_capture.py`). Dla każdego portu opublikowanego na `127.0.0.1` zweryfikowano połączenie TLS z weryfikacją certyfikatu i nazwy hosta, odrzucenie obcej nazwy oraz brak obsługi połączeń jawnych; dla Bolt i PostgreSQL komunikaty startowe wysłano bezpośrednio przez gniazda TCP (tab. 7.8).

**Tab. 7.8:** Wyniki weryfikacji konfiguracji TLS dla portów opublikowanych na hoście

| Port | Usługa | Wersja TLS | Obca nazwa hosta | Żądanie bez TLS |
| ---: | --- | :---: | :---: | --- |
| 5173 | nginx | TLS 1.3 | odrzucona | `400 Bad Request` |
| 8000 | API | TLS 1.3 | odrzucona | połączenie zamknięte bez odpowiedzi |
| 7473 | konsola Neo4j | TLS 1.3 | odrzucona | odpowiedź wyłącznie w protokole TLS |
| 7687 | Neo4j (Bolt) | TLS 1.3 | odrzucona | połączenie zamknięte bez odpowiedzi |
| 5432 | PostgreSQL | TLS 1.3 | odrzucona | `pg_hba.conf rejects connection … no encryption` |

W sieci Dockera potwierdzono również odrzucenie połączeń z bazami po adresie IP i połączeń jawnych (`bolt://`, `sslmode=disable`). Wersję TLS 1.3 jako minimalną wymuszają PostgreSQL oraz połączenie nginx–API; pozostałe usługi akceptują też TLS 1.2.

Brak jawnych danych potwierdzono, nagrywając pakiety na czterech połączeniach systemu (4.1) programem `tcpdump` z pomocniczego kontenera sieciowego podczas logowania i zapytań z losowym znacznikiem do obu backendów. Analiza `tshark` nie wykryła w surowych segmentach TCP haseł, e-maili, znaczników, tokenów JWT ani zapytań SQL/Cypher (tab. 7.9).

**Tab. 7.9:** Wyniki analizy przechwyconego ruchu sieciowego na połączeniach systemu

| Połączenie | Wersja TLS | Rekordy TLS z danymi | Jawnie widoczne wartości |
| --- | :---: | ---: | --- |
| przeglądarka → nginx | TLS 1.3 | 22 | brak |
| nginx → API | TLS 1.3 | 23 | brak |
| API → Neo4j | TLS 1.3 | 24 | brak |
| API → PostgreSQL | TLS 1.3 | 25 | brak |

![[Pasted image 20261125130900.png]]

*Zaszyfrowany ruch z aplikacji widoczny w Wireshark*

**Rys. 7.1:** Przechwycone połączenie w programie Wireshark bez kluczy sesji oraz po odszyfrowaniu

7.7 Uruchomienie środowiska od zera

Przenośność systemu (3.3) sprawdzono skryptem `tests/test_fresh_start.py` na świeżym klonie repozytorium z pustymi wolumenami. Po wygenerowaniu certyfikatów i uruchomieniu `docker compose up --build` logowanie przez nginx zadziałało po 27 s, z pełnym stanem baz (563 węzły i 1 448 krawędzi w Neo4j; 32 tabele i 1 635 wierszy w PostgreSQL).

Restart środowiska nie zmienił liczby obiektów (idempotentność `MERGE`, 5.3.2). Zmiana `NEO4J_APP_PASSWORD` zadziałała automatycznie (`CREATE OR REPLACE USER`, 5.1.4), natomiast zmiana `PG_APP_PASSWORD` bez usunięcia wolumenu `pg_data` zablokowała start API, co wynika z jednorazowej inicjalizacji PostgreSQL (6.3) i współdzielenia procesu przez oba backendy (5.5.2).

7.8 Porównanie z modelem relacyjnym

7.8.1 Zgodność backendów i metodyka pomiarów

Zgodność semantyczną zweryfikowano skryptem `bench/compare.py`: w 13 przypadkach (w tym błędach 401, 403, 422) backendy `/api` i `/api/rel` zwróciły identyczne kody i treść JSON.

Pomiary (`bench/run.py`, `bench/measure.py`) objęły siedem z ośmiu wspólnych punktów końcowych. Mierzono czas żądania HTTPS przez serwer nginx (port 5173), czyli tak, jak wysyła je przeglądarka. Podane wartości to mediany 50 pomiarów (dla `POST /login` 10 ze względu na bcrypt), poprzedzonych rozgrzewką: każdy punkt końcowy wywołano wcześniej 200 razy, ponieważ Neo4j działa w maszynie wirtualnej Javy, której kompilator JIT (ang. *Just-In-Time*) optymalizuje kod dopiero po setkach wykonań.

Do badania skalowalności wygenerowano (`bench/generate.py`) spójne zbiory dla 1 000, 3 000 i 10 000 studentów (tab. 7.10), mierzone na świeżych środowiskach (`docker compose down -v` przed każdą skalą) z domyślną konfiguracją baz. Parametry zapytań punktowych zwracały zbliżoną liczbę wierszy (poza katalogiem: 168 lub 336 wierszy i opiniami: 9 lub 14).

**Tab. 7.10:** Rozmiar wygenerowanych zbiorów danych w kolejnych skalach pomiarowych

| Studentów | Wydziałów | Grup | Zapisów na grupy | Węzłów | Krawędzi |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 29 (dane początkowe) | 2 | 129 | 215 | 563 | 1 448 |
| 1 000 | 2 | 1 248 | 28 000 | 4 265 | 40 846 |
| 3 000 | 2 | 2 688 | 84 000 | 8 607 | 114 052 |
| 10 000 | 4 | 9 216 | 280 000 | 27 065 | 378 121 |

7.8.2 Czas odpowiedzi i wpływ skali danych

**Tab. 7.11:** Mediana czasu żądania przez serwer nginx w zależności od liczby studentów [ms]

| Punkt końcowy | Baza | 29 | 1 000 | 3 000 | 10 000 |
| --- | --- | ---: | ---: | ---: | ---: |
| `GET /subjects` | Neo4j | 10,20 | 43,99 | 59,08 | 223,10 |
|  | PostgreSQL | 8,02 | 23,80 | 29,88 | 90,66 |
| `GET /opinions` | Neo4j | 2,83 | 2,88 | 3,34 | 3,31 |
|  | PostgreSQL | 1,86 | 1,87 | 1,96 | 1,93 |
| `GET /me/registrations/{id}/groups` | Neo4j | 3,15 | 3,95 | 3,80 | 5,04 |
|  | PostgreSQL | 2,03 | 2,16 | 3,21 | 3,61 |
| `GET /groups/{id}/students` | Neo4j | 2,91 | 4,38 | 4,74 | 4,63 |
|  | PostgreSQL | 1,91 | 2,19 | 3,14 | 3,25 |
| `GET /students/{idx}` | Neo4j | 4,33 | 6,07 | 6,56 | 6,52 |
|  | PostgreSQL | 2,13 | 2,90 | 3,05 | 3,48 |
| `PUT /groups/{id}/students/{idx}/grade` | Neo4j | 3,62 | 3,66 | 3,36 | 3,26 |
|  | PostgreSQL | 1,97 | 1,92 | 1,94 | 2,06 |

![[skala_czas.png]]

**Rys. 7.2:** Mediana czasu żądania przez serwer nginx (linia ciągła) i czasu silnika (linia przerywana) w zależności od liczby studentów

PostgreSQL odpowiadał szybciej we wszystkich porównywanych punktach końcowych: przy 10 000 studentów 1,4–1,9 raza w zapytaniach punktowych i 2,5 raza w katalogu przedmiotów (`GET /subjects`, tab. 7.11). Dziesięciokrotny wzrost liczby studentów (1 000 → 10 000) wydłużył zapytania punktowe w Neo4j najwyżej o 28%, a w PostgreSQL o 67%; czas katalogu przedmiotów wzrósł odpowiednio 5,1 i 3,8 raza (rys. 7.2). Zapytania punktowe w obu backendach mieszczą się poniżej 7 ms.

Szczegółowa analiza przyczyn tych różnic wykracza poza zakres pracy. Wpływają na nie m.in. sposób przesyłania zapytań przez sterowniki oraz plany wykonania wybierane przez planistów obu baz – PostgreSQL wykonuje zapytania API jako polecenia przygotowane i po kilku wykonaniach może przejść na plan ogólny, sporządzony bez znajomości wartości parametrów [CYTOWANIE: https://www.postgresql.org/docs/current/sql-prepare.html].

7.8.3 Import i rozmiar baz

Rozmiar Neo4j (tab. 7.12) zmierzono po `CALL db.checkpoint()`, bez wstępnie przydzielonego dziennika transakcji (256 MiB).

**Tab. 7.12:** Czas importu danych przy pierwszym uruchomieniu oraz rozmiar baz na dysku

| Studentów | Import Neo4j przed poprawką [s] | Import Neo4j [s] | Import PostgreSQL [s] | Rozmiar Neo4j [MB] | Rozmiar PostgreSQL [MB] | w tym indeksy PostgreSQL [MB] |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 29 | 6,2 | 6,2 | 0,3 | 2,2 | 10,4 | 1,0 |
| 1 000 | 14,8 | 7,6 | 1,1 | 5,0 | 22,8 | 7,2 |
| 3 000 | 78,3 | 9,1 | 2,6 | 11,4 | 45,3 | 19,1 |
| 10 000 | 851,9 | 14,2 | 10,4 | 34,3 | 125,2 | 62,0 |

![[import.png]]

**Rys. 7.3:** Czas importu danych do obu baz w zależności od liczby studentów

Pierwsza wersja importu do Neo4j wydłużała się kwadratowo z rozmiarem danych (851,9 s dla 10 000 studentów, druga kolumna tab. 7.12), ponieważ wyszukiwanie studentów przy tworzeniu krawędzi nie korzystało z indeksu. Po wskazaniu indeksu w instrukcjach importu (5.3.3) czas spadł do 14,2 s. Zamiana `MERGE` na `CREATE` nie dała mierzalnego zysku (5,5 wobec 5,9 s przy 3 000 studentów), więc import pozostał bezpieczny do powtarzania przy każdym starcie. Czas importu Neo4j obejmuje też połączenie z bazą, utworzenie typu grafu i konta API, dlatego przy małych zbiorach przekracza czas `COPY` w PostgreSQL, rosnącego liniowo z danymi. Baza grafowa zajmuje 3,6 raza mniej miejsca na dysku niż PostgreSQL, w którym połowę rozmiaru (62 MB) stanowią indeksy.

7.8.4 Podsumowanie porównania

PostgreSQL okazał się 1,4–1,9 raza szybszy w zapytaniach punktowych i 2,5 raza szybszy w agregującym katalogu przedmiotów. Przy 10 000 studentów oba backendy odpowiadają na zapytania punktowe w czasie kilku milisekund, więc dla skali uczelni różnica nie wpływa na użyteczność systemu. Neo4j zajmuje mniej miejsca na dysku i pozwala na krótsze zapytania dzięki wieloetykietowości, natomiast PostgreSQL zapewnia silniejsze ograniczenia schematu (6.2.3, 7.5.1).
