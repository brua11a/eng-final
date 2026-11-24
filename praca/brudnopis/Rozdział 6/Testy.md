7.1 Środowisko i organizacja testów

Testy funkcjonalne, bezpieczeństwa oraz pomiary wydajności przeprowadzono lokalnie na komputerze z procesorem AMD Ryzen 7 5800X (8 rdzeni, 16 wątków, do 4,85 GHz), 16 GB pamięci RAM i dyskiem SSD NVMe ADATA XPG SX8200 Pro 512 GB, pod kontrolą systemu Arch Linux (jądro 7.2.11) oraz środowiska Docker 29.9.2 z Docker Compose (5.1).

Zakres testów oparto na wymaganiach z rozdziału 3. Każdy przypadek zaimplementowano jako niezależny skrypt Pythona w katalogu `tests/`, uruchamiany zbiorczo przez `tests/run_all.py` (z zapisem raportów w `tests/wyniki/`). Żądania kierowano z hosta po HTTPS z weryfikacją lokalnego CA, a operacje pomocnicze (dane testowe, kontrola stanu baz, generowanie tokenów) wykonywano z kontenera `app` z użyciem kont bazodanowych API; w testach logowania stosowano właściwe hasła. Obiekty testowe oznaczano prefiksem `test-` i usuwano po przebiegu. Wszystkie testy zakończyły się zgodnie z oczekiwaniami.

7.2 Uwierzytelnianie i kontrola dostępu

7.2.1 Kontrola dostępu i kolejność sprawdzeń

Mechanizmy RBAC i ReBAC zweryfikowano skryptem `tests/test_permissions.py` dla wszystkich 59 punktów końcowych backendu grafowego pobranych ze specyfikacji OpenAPI (5.4), przy czym macierz uprawnień zdefiniowano niezależnie na podstawie tabel 3.1–3.3. Każdy punkt końcowy wywołano bez tokenu oraz z rolami studenta, prowadzącego, administratora i osoby łączącej role studenta i prowadzącego; żądania zapisujące wysyłano z błędną treścią (422) lub nieistniejącymi identyfikatorami (404), aby nie modyfikować bazy (tab. 7.1).

**Tab. 7.1:** Wyniki testu RBAC dla 59 punktów końcowych (291 żądań)

| Moduł | Punkty końcowe | Bez tokenu | Student | Prowadzący | Administrator | Student i prowadzący |
| --- | ---: | :---: | :---: | :---: | :---: | :---: |
| public (logowanie) | 1 | dostęp | – | – | – | – |
| catalogue | 10 | 401 | dostęp | dostęp | dostęp | dostęp |
| student | 10 | 401 | dostęp | 403 | 403 | dostęp |
| teacher | 4 | 401 | 403 | dostęp | dostęp¹ | dostęp |
| admin | 34 | 401 | 403 | 403 | dostęp | 403 |

*¹ Z wyjątkiem listy własnych grup (`GET /me/groups`), dostępnej wyłącznie dla roli prowadzącego.*

W 16 scenariuszach ReBAC (4.4.2) potwierdzono, że prowadzący ma dostęp wyłącznie do własnych grup i nauczanych studentów (200 wobec 403 dla cudzych zasobów), administrator do dowolnej grupy i studenta (200), student wyłącznie do własnych zapisów, semestrów i opinii o swoich grupach (403 dla cudzych danych lub zapisów bez tury), a użytkownik wielorolowy łączy uprawnienia obu ról przy zachowaniu odmów dla cudzych zasobów. Potwierdza to spełnienie wymagań z 3.1.

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

| Krok | Bez unieważniania | Z unieważnianiem |
| --- | :---: | :---: |
| `GET /admin/people/next-idx` przed odebraniem roli | 200 | 200 |
| `GET /admin/people/next-idx` po odebraniu roli (stary token) | 200 | 401 `Token revoked` |
| `PATCH /admin/users/281056` z `{"active": false}` (stary token) | 200 | 401 `Token revoked` |
| ponowne logowanie i `GET /admin/people/next-idx` | 403 | 403 |

Mechanizm unieważniania natychmiast blokuje dotychczasowy token kodem 401, zmuszając użytkownika do ponownego logowania już bez odebranej roli.

7.3 Współbieżność

Skuteczność blokad przy równoległych zapisach i modyfikacji ról (5.5.10, 6.4.1) sprawdzono skryptami `tests/test_concurrent_registration.py` (Neo4j) oraz `tests/test_concurrent_registration_rel.py` (PostgreSQL). Żądania wysyłano z wątków synchronizowanych barierą; scenariusze kontrolne bez blokad (C, C1, C2) uruchomiono bezpośrednio przez sterowniki (w PostgreSQL z 100-milisekundowym opóźnieniem zatwierdzenia, aby wymusić kolizję). Scenariusz D dotyczy wyłącznie backendu grafowego (tab. 7.4).

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

Skryptem `tests/test_schema_constraints.py` sprawdzono ograniczenia schematu bezpośrednio w Neo4j (z pominięciem API, na koncie aplikacji). Każda z 14 prób niepoprawnego zapisu w osobnej zatwierdzanej transakcji została odrzucona z odpowiednim kodem błędu GQL (ang. *Graph Query Language*, 4.3.7, tab. 7.6).

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

W próbie kontrolnej z kluczami sesji z `SSLKEYLOGFILE` [CYTOWANIE: https://docs.python.org/3/library/ssl.html#ssl.SSLContext.keylog_filename] program `tshark` odczytał z tego samego nagrania wszystkie trzy żądania z hasłem i znacznikiem, potwierdzając obecność danych i skuteczność szyfrowania (rys. 7.1).

*[Zrzut ekranu: to samo nagranie w programie Wireshark bez kluczy sesji i z kluczami sesji]*

**Rys. 7.1:** Przechwycone połączenie w programie Wireshark bez kluczy sesji oraz po odszyfrowaniu

7.7 Uruchomienie środowiska od zera

Przenośność systemu (3.3) sprawdzono skryptem `tests/test_fresh_start.py` na świeżym klonie repozytorium z pustymi wolumenami. Po wygenerowaniu certyfikatów i uruchomieniu `docker compose up --build` logowanie przez nginx zadziałało po 27 s, z pełnym stanem baz (563 węzły i 1 448 krawędzi w Neo4j; 32 tabele i 1 635 wierszy w PostgreSQL).

Restart środowiska nie zmienił liczby obiektów (idempotentność `MERGE`, 5.3.2). Zmiana `NEO4J_APP_PASSWORD` zadziałała automatycznie (`CREATE OR REPLACE USER`, 5.1.4), natomiast zmiana `PG_APP_PASSWORD` bez usunięcia wolumenu `pg_data` zablokowała start API, co wynika z jednorazowej inicjalizacji PostgreSQL (6.3) i współdzielenia procesu przez oba backendy (5.5.2).

7.8 Porównanie z modelem relacyjnym

7.8.1 Zgodność backendów i metodyka pomiarów

Zgodność semantyczną zweryfikowano skryptem `bench/compare.py`: w 13 przypadkach (w tym błędach 401, 403, 422) backendy `/api` i `/api/rel` zwróciły identyczne kody i treść JSON (po sprowadzeniu znaczników czasu do strefy UTC, ang. *Coordinated Universal Time*, gdyż Neo4j zachowuje oryginalne przesunięcie, a PostgreSQL zwraca czas w strefie sesji [CYTOWANIE: https://www.postgresql.org/docs/current/datatype-datetime.html]).

Pomiary (`bench/measure.py`) objęły siedem z ośmiu wspólnych punktów końcowych (6.4; zapis na grupę sprawdzono w 7.3) w pięciu warstwach stosu: **silnik** (`PROFILE` w Neo4j, `EXPLAIN (ANALYZE, TIMING OFF)` w PostgreSQL), **sterownik** (z pobraniem wierszy w kontenerze `app`), **FastAPI** (bez sieci i TLS), **HTTPS do API** (port 8000) oraz **HTTPS przez nginx** (port 5173). Treść i parametry zapytań przechwytywano z wywołania API i odtwarzano zgodnie z modelem transakcji każdego backendu (5.5.3, 6.4). Przed pomiarami każdy punkt końcowy wywołano 200 razy: Neo4j działa w maszynie wirtualnej Javy, której kompilator JIT (ang. *Just-In-Time*) optymalizuje kod dopiero po setkach wykonań, a przy krótszej rozgrzewce warstwy mierzone wcześniej wypadały wolniej od późniejszych, choć obejmują mniej pracy. Następnie każdą warstwę mierzono 50 razy po 10 przebiegach rozgrzewkowych (dla `POST /login` 10 pomiarów ze względu na bcrypt); pełne dane wraz z 95. percentylami zapisano w `bench/results/`. Warstwy mierzono w osobnych seriach, dlatego różnice median sąsiednich warstw mniejsze niż ok. 0,3 ms mieszczą się w rozrzucie pomiarów.

W PostgreSQL wyłączono pomiar per operator (`TIMING OFF`), gdyż zawyżał czas katalogu o ok. 10%, natomiast w Neo4j czas silnika pochodzi z `PROFILE` i zawiera narzut profilowania – miarodajne porównanie zaczyna się więc od warstwy sterownika. Czas silnika PostgreSQL mierzono na poleceniu przygotowanym (`PREPARE` i `EXPLAIN ANALYZE EXECUTE`), tak jak wykonuje je API: `psycopg` przygotowuje zapytanie po pięciu wykonaniach, a PostgreSQL po kolejnych pięciu może przejść na plan ogólny [CYTOWANIE: https://www.postgresql.org/docs/current/sql-prepare.html]. Pierwotny pomiar bez przygotowania zawyżał czas katalogu przedmiotów przy 10 000 studentów (103,6 ms wobec 86,1 ms całej warstwy sterownika): plan dla konkretnych parametrów miał szacowany koszt ok. 262 tys., powyżej progu kompilacji JIT (`jit_above_cost` = 100 tys.) [CYTOWANIE: https://www.postgresql.org/docs/current/jit-decision.html], a kompilacja 108 funkcji wydłużała wykonanie o ok. 40%; plan ogólny używany przez API (koszt ok. 37 tys.) progu nie przekracza. Równolegle zbierano metryki diagnostyczne z `PROFILE` [CYTOWANIE: https://neo4j.com/docs/cypher-manual/current/planning-and-tuning/] i `EXPLAIN (ANALYZE, BUFFERS, MEMORY, SERIALIZE)` [CYTOWANIE: https://www.postgresql.org/docs/current/sql-explain.html].

Do badania skalowalności wygenerowano (`bench/generate.py`) spójne zbiory dla 1 000, 3 000 i 10 000 studentów (tab. 7.10), mierzone na świeżych środowiskach (`docker compose down -v` przed każdą skalą) z domyślną konfiguracją baz. Parametry zapytań punktowych zwracały zbliżoną liczbę wierszy (poza katalogiem: 168 lub 336 wierszy i opiniami: 9 lub 14); cały zbiór mieścił się w pamięci RAM (zero chybień pamięci podręcznej).

**Tab. 7.10:** Rozmiar wygenerowanych zbiorów danych w kolejnych skalach pomiarowych

| Studentów | Wydziałów | Grup | Zapisów na grupy | Węzłów | Krawędzi |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 29 (dane początkowe) | 2 | 129 | 215 | 563 | 1 448 |
| 1 000 | 2 | 1 248 | 28 000 | 4 265 | 40 846 |
| 3 000 | 2 | 2 688 | 84 000 | 8 607 | 114 052 |
| 10 000 | 4 | 9 216 | 280 000 | 27 065 | 378 121 |

7.8.2 Czas wykonania w warstwach i wpływ skali danych

**Tab. 7.11:** Mediana czasu wykonania żądania w kolejnych warstwach dla skali 10 000 studentów [ms]

| Punkt końcowy | Baza | Silnik | Sterownik | FastAPI | HTTPS do API | HTTPS przez nginx |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `POST /login` | Neo4j | 0,05 | 0,77 | 180,10 | 179,59 | 180,39 |
|  | PostgreSQL | 0,03 | 0,25 | 178,31 | 178,79 | 179,89 |
| `GET /subjects` | Neo4j | 186,85 | 219,99 | 225,76 | 221,72 | 223,10 |
|  | PostgreSQL | 81,83 | 85,39 | 88,77 | 89,43 | 90,66 |
| `GET /opinions` | Neo4j | 0,24 | 1,69 | 2,04 | 2,41 | 3,31 |
|  | PostgreSQL | 0,15 | 0,45 | 0,84 | 1,17 | 1,93 |
| `GET /me/registrations/{id}/groups` | Neo4j | 0,38 | 3,13 | 3,74 | 3,60 | 5,04 |
|  | PostgreSQL | 0,28 | 1,58 | 2,03 | 2,68 | 3,61 |
| `GET /groups/{id}/students` | Neo4j | 0,15 | 2,84 | 3,13 | 3,84 | 4,63 |
|  | PostgreSQL | 0,57 | 1,58 | 1,92 | 2,40 | 3,25 |
| `GET /students/{idx}` | Neo4j | 1,31 | 5,08 | 5,66 | 5,51 | 6,52 |
|  | PostgreSQL | 1,13 | 1,68 | 2,33 | 2,72 | 3,48 |
| `PUT /groups/{id}/students/{idx}/grade` | Neo4j | 0,11 | 1,83 | 2,16 | 2,42 | 3,26 |
|  | PostgreSQL | 0,05 | 0,79 | 1,13 | 1,12 | 2,06 |

![[narzut_10000.png]]

**Rys. 7.2:** Udział kolejnych warstw w czasie żądania przez serwer nginx dla zapytań punktowych przy 10 000 studentów (warstwy HTTPS do API i nginx połączono, ponieważ ich osobne różnice mieszczą się w rozrzucie pomiarów)

Poza katalogiem przedmiotów wykonanie zapytań w silniku stanowi jedynie 3–20% czasu żądania w Neo4j i 3–33% w PostgreSQL (tab. 7.11, rys. 7.2). Główną różnicę wprowadza sterownik: w Neo4j dodaje 0,7–1,5 ms na zapytanie (osobne transakcje automatyczne po Bolt i konwersja `native()`, 5.5.5), podczas gdy w PostgreSQL 0,2–0,7 ms dzięki jednej transakcji na żądanie i automatycznemu przygotowywaniu zapytań w `psycopg` [CYTOWANIE: https://www.psycopg.org/psycopg3/docs/advanced/prepare.html]. FastAPI wnosi 0,3–0,6 ms (w `POST /login` ponad 98% czasu zajmuje bcrypt), a uvicorn, TLS i nginx łącznie 0,9–1,6 ms w obu backendach. W efekcie zapytania punktowe w Neo4j trwają 1,4–1,9 raza dłużej mimo porównywalnych czasów silników (dla `GET /groups/{id}/students` silnik Neo4j był nawet blisko czterokrotnie szybszy). W katalogu przedmiotów (`GET /subjects`), jedynym punkcie zdominowanym przez silnik, PostgreSQL okazał się 2,5 raza szybszy.

**Tab. 7.12:** Mediana czasu żądania przez serwer nginx w zależności od liczby studentów [ms]

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

**Rys. 7.3:** Mediana czasu żądania przez serwer nginx (linia ciągła) i czasu silnika (linia przerywana) w zależności od liczby studentów

![[skala_praca.png]]

**Rys. 7.4:** Względna praca bazy odniesiona do skali 1 000 studentów: *db hits* (Neo4j) oraz odczytane bloki bufora (PostgreSQL)

Dziesięciokrotny wzrost liczby studentów (1 000 → 10 000) wydłużył zapytania punktowe w Neo4j najwyżej o 28%, a w PostgreSQL o 67% (tab. 7.12, rys. 7.3). W Neo4j liczba *db hits* zapytań punktowych rośnie tylko wraz z wynikiem (rys. 7.4): w liście grup zapisów 3,6 raza, bo zapis przy 10 000 studentów otwiera 18 grup zamiast 4 (praca na zwrócony wiersz pozostaje stała), a w opiniach 1,6 raza przy 14 opiniach zamiast 9. W PostgreSQL odczytane bloki rosną 1,1–3,3 raza, przy czym planista częściej wybiera dostęp przez indeks (`Seq Scan` 17 → 11, `Index Only Scan` 11 → 15 we wszystkich planach). W katalogu przedmiotów czas silnika wzrósł siedmiokrotnie w Neo4j (11,6× więcej *db hits* przez zagnieżdżone podzapytania na komórkę siatki, 5.4.3) i pięciokrotnie w PostgreSQL (3,1× więcej bloków dzięki `Hash Join`).

7.8.3 Diagnostyka zapytań

Jednostki pracy bazy w diagnostyce (tab. 7.13) są różne (*db hits* w Neo4j, 8-kilobajtowe bloki bufora w PostgreSQL) i należy je porównywać wyłącznie w obrębie jednego silnika.

**Tab. 7.13:** Wyniki diagnostyki zapytań dla skali 10 000 studentów (sumy po zapytaniach punktu końcowego)

| Punkt końcowy | Baza | Wzorce krawędzi / złączenia | Praca | Pamięć [kB] | Maks. błąd oszacowania |
| --- | --- | ---: | ---: | ---: | ---: |
| `POST /login` | Neo4j | 0 | 4 | 0 | 1 |
|  | PostgreSQL | 4 | 9 | 4 | 1 |
| `GET /subjects` | Neo4j | 16 | 822 402 | 168 | 3,3 |
|  | PostgreSQL | 10 | 53 363 | 379 | 8,8 |
| `GET /opinions` | Neo4j | 6 | 382 | 5 | 14 |
|  | PostgreSQL | 6 | 242 | 32 | 14 |
| `GET /me/registrations/{id}/groups` | Neo4j | 10 | 461 | 8 | 18 |
|  | PostgreSQL | 6 | 353 | 676 | 18 |
| `GET /groups/{id}/students` | Neo4j | 2 | 210 | 5 | 10 |
|  | PostgreSQL | 4 | 210 | 284 | 1,9 |
| `GET /students/{idx}` | Neo4j | 11 | 2 742 | 45 | 49 |
|  | PostgreSQL | 11 | 1 843 | 41 | 49 |
| `PUT /groups/{id}/students/{idx}/grade` | Neo4j | 2 | 87 | 1 | 10 |
|  | PostgreSQL | 0 | 14 | 13 | 1 |

Liczba wzorców krawędzi w Cypher i złączeń w SQL jest zbliżona: Neo4j wygrywa w logowaniu dzięki wieloetykietowości (0 wobec 4 `LEFT JOIN`, 5.4.2, 6.2.2), natomiast w zapisie oceny tabela `registered_in` z kluczem złożonym obywa się bez złączeń. Zużycie pamięci nie przekracza 0,7 MB. Planowanie w PostgreSQL trwało 0,004–0,02 ms dla zapytań wykonywanych z planem ogólnym z pamięci podręcznej i do 1 ms tam, gdzie planista pozostał przy planach dla konkretnych parametrów (lista grup zapisów, lista studentów grupy). Największy błąd oszacowania (49×) wystąpił w ocenach studenta; planista Neo4j nie utrzymuje histogramów wartości właściwości [CYTOWANIE: https://neo4j.com/docs/cypher-manual/current/planning-and-tuning/execution-plans/], a plan ogólny PostgreSQL powstaje bez wartości parametrów.

Diagnostyka ujawniła ten sam błąd wydajnościowy `GET /opinions` w obu backendach (5.5.9): warunek `$x IS NULL OR ...` na obu kolumnach filtra nie pozwala planiście wybrać indeksu, jeśli nie zna wartości parametrów. W Neo4j skutkował pełnym skanem `NodeByLabelScan`; po rozdzieleniu zapytania na warianty dla prowadzącego i grupy (`NodeUniqueIndexSeek`) praca przy 10 000 studentów spadła z 2 227 do 382 *db hits*, błąd oszacowania z 692 do 14, a czas przez nginx z 4,61 do 3,31 ms. W PostgreSQL problem ujawnił się dopiero przy pomiarze na poleceniu przygotowanym: plan ogólny przeglądał całą tabelę `opinion` (`Seq Scan`). Po analogicznym rozdzieleniu zapytania plan korzysta z indeksów, a czas silnika spadł z 0,42 do 0,15 ms, czas przez nginx z 2,28 do 1,93 ms.

Diagnostyka wskazuje też miejsce dalszej optymalizacji w Neo4j: sprawdzenie ReBAC w `GET /students/{idx}` (`Teacher → TEACHES → Group ← REGISTERED_IN ← Student`) rozwija krawędzie od prowadzącego, przeglądając studentów wszystkich jego grup (ok. 1 000 *db hits* przy 10 000 studentów dla jednego zwróconego wiersza). Rozpoczęcie dopasowania od obu końców wzorca ograniczyłoby pracę do grup jednego studenta.

7.8.4 Import, rozmiar baz oraz rozszerzenie sterownika Neo4j

Rozmiar Neo4j (tab. 7.14) zmierzono po `CALL db.checkpoint()`, bez wstępnie przydzielonego dziennika transakcji (256 MiB).

**Tab. 7.14:** Czas importu danych przy pierwszym uruchomieniu oraz rozmiar baz na dysku

| Studentów | Import Neo4j przed poprawką [s] | Import Neo4j [s] | Import PostgreSQL [s] | Rozmiar Neo4j [MB] | Rozmiar PostgreSQL [MB] | w tym indeksy PostgreSQL [MB] |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 29 | 6,2 | 6,2 | 0,3 | 2,2 | 10,4 | 1,0 |
| 1 000 | 14,8 | 7,6 | 1,1 | 5,0 | 22,8 | 7,2 |
| 3 000 | 78,3 | 9,1 | 2,6 | 11,4 | 45,3 | 19,1 |
| 10 000 | 851,9 | 14,2 | 10,4 | 34,3 | 125,2 | 62,0 |

![[import.png]]

**Rys. 7.5:** Czas importu danych do obu baz w zależności od liczby studentów

Pierwsze pomiary wykazały kwadratowy wzrost czasu importu do Neo4j (do 851,9 s dla 10 000 studentów, druga kolumna tab. 7.14). Pomiar czasu poszczególnych instrukcji wskazał krawędzie studentów: wyszukanie `(:Student {idx: ...})` w trakcie importu nie korzystało z indeksu klucza zdefiniowanego dla `Person`, ponieważ planista planował zapytanie na statystykach pustej bazy. Jawne wskazanie indeksu (5.3.3) skróciło import do 14,2 s. Zamiana `MERGE` na `CREATE` nie dała natomiast mierzalnego zysku (5,5 wobec 5,9 s przy 3 000 studentów), więc import pozostał bezpieczny do powtarzania przy każdym starcie. Czas importu Neo4j obejmuje też połączenie z bazą, utworzenie typu grafu i konta API, dlatego przy małych zbiorach przekracza czas `COPY` w PostgreSQL, rosnącego liniowo z danymi. Baza grafowa zajmuje 3,6 raza mniej miejsca na dysku niż PostgreSQL, w którym połowę rozmiaru (62 MB) stanowią indeksy.

Dodatkowo przetestowano (`bench/rust_ext.py`) rozszerzenie `neo4j-rust-ext` 6.2.0.0 [CYTOWANIE: https://pypi.org/project/neo4j-rust-ext/], przyspieszające kodowanie i dekodowanie PackStream w języku Rust (tab. 7.15). Oba warianty zmierzono w jednym przebiegu na tej samej bazie; wartości bezwzględne różnią się od tab. 7.11 o rozrzut między niezależnymi przebiegami (dla warstwy sterownika Neo4j do ok. 0,5 ms), dlatego porównywać należy wyłącznie warianty między sobą.

**Tab. 7.15:** Mediana czasu wykonania w Neo4j bez rozszerzenia `neo4j-rust-ext` i z nim [ms]

| Punkt końcowy | 1 000 studentów: sterownik | 1 000: FastAPI | 10 000 studentów: sterownik | 10 000: FastAPI |
| --- | ---: | ---: | ---: | ---: |
| `POST /login` | 0,49 → 0,49 | 178,51 → 178,04 | 0,51 → 0,45 | 178,90 → 178,23 |
| `GET /subjects` | 30,33 → 26,57 | 40,69 → 34,17 | 161,02 → 147,66 | 167,62 → 160,75 |
| `GET /opinions` | 0,88 → 0,69 | 1,32 → 1,04 | 1,37 → 1,08 | 1,60 → 1,50 |
| `GET /me/registrations/{id}/groups` | 1,15 → 0,85 | 1,55 → 1,22 | 2,32 → 2,08 | 2,76 → 2,43 |
| `GET /groups/{id}/students` | 1,67 → 1,31 | 1,93 → 1,71 | 2,34 → 2,01 | 2,87 → 2,50 |
| `GET /students/{idx}` | 2,85 → 2,33 | 3,44 → 2,89 | 3,12 → 2,90 | 3,96 → 3,37 |
| `PUT /groups/{id}/students/{idx}/grade` | 1,27 → 1,15 | 1,75 → 1,50 | 1,28 → 1,11 | 1,86 → 1,62 |

Rozszerzenie obniżyło czas sterownika o 0,1–0,5 ms dla zapytań punktowych i o 4–13 ms (8–12%) dla katalogu, przy niezmienionym czasie silnika. Narzut sterownika ponad silnik pozostał jednak większy niż w PostgreSQL (0,6–1,8 wobec 0,2–1,3 ms na punkt końcowy) z powodu osobnych transakcji automatycznych i konwersji `native()` (5.5.5).

7.8.5 Podsumowanie porównania

W zapytaniach punktowych oba silniki działają poniżej 1,5 ms, a o czasie odpowiedzi decydują warstwy pośredniczące; końcowo PostgreSQL okazał się 1,4–1,9 raza szybszy w zapytaniach punktowych i 2,5 raza szybszy w agregującym katalogu przedmiotów. Neo4j zachowuje stałą pracę na zwrócony wiersz w zapytaniach lokalnych, mniejszy rozmiar na dysku i krótsze zapytania korzystające z wieloetykietowości, jednak indeksy w PostgreSQL zapewniły porównywalne skalowanie, przy silniejszych ograniczeniach schematu (6.2.3, 7.5.1). Pomiary ujawniły przy tym trzy problemy wynikające ze sposobu planowania zapytań – kwadratowy czas importu do Neo4j, pełne skany w opiniach w obu backendach oraz kompilację JIT zawyżającą pomiar w PostgreSQL – co pokazuje, że wnioski o wydajności wymagają analizy planów, a nie wyłącznie czasu odpowiedzi.
