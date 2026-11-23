// SZKIELET – punkty do rozpisania. Kod: `sql/`, `app/relation_backend/`, `bench/`.

6.1 Cel i zakres porównania

- po co: cel pracy z 1.2 – porównanie złożoności zapytań (liczba złączeń / przejść) i czasu wykonania
- co porównujemy: te same punkty końcowe, te same modele Pydantic, ten sam kontrakt (4.2) – różni się tylko realizacja po stronie bazy
- czego NIE porównujemy: całego backendu (tylko wybrane punkty końcowe), skalowania poziomego, klastrów
- środowisko: PostgreSQL 18.1 vs Neo4j 2026.07.1 Enterprise, oba w Dockerze na tej samej maszynie, oba po TLS, oba z kontem o minimalnych uprawnieniach
- // podać parametry maszyny testowej (CPU, RAM, dysk) i wersje sterowników (neo4j 6.2.0, psycopg 3.3.9)

6.2 Model relacyjny

6.2.1 Przekształcenie grafu w tabele
- zasada: etykieta → tabela, krawędź N:1 → kolumna z kluczem obcym, krawędź N:M → tabela łącząca; oparte na tabeli kardynalności z 4.3.6
- krawędzie N:1, które „zniknęły” w kolumnach: `OFFERED_BY`, `HAS_CURRICULUM`, `HAS_TERM`, `TAUGHT_IN` (kolumna opcjonalna), `HAS_TYPE`, `OF_TYPE`, `IN_ROOM`, `FOR_CYCLE`, `FOR_FACULTY`, `HAS_TURN`, `WRITES`, `ABOUT`, `ABOUT_TEACHER`
- krawędzie N:M → tabele łączące: `teaches`, `works_at`, `enrolled`, `registered_in` (z właściwościami `registered_at`, `grade`), `term_subject`, `opens`, `assigned`
- `Group` → tabela `class_group`, bo „group” to słowo zastrzeżone SQL
- // diagram ERD (do zrobienia, np. dbdiagram / pgModeler / mermaid erDiagram)
- // tabela: krawędź grafu → realizacja w SQL (kolumna FK / tabela łącząca)

6.2.2 Osoby i role bez wieloetykietowości
- PostgreSQL nie ma etykiet → tabela `person` + osobne tabele ról `student`, `teacher`, `admin`, których klucz główny jest jednocześnie kluczem obcym do `person` (dziedziczenie przez tabele / *class table inheritance*)
- osoba z kilkoma rolami = po jednym wierszu w kilku tabelach ról
- `User` → tabela `app_user`; `Inactive` → kolumna `deactivated_at` (NULL = konto aktywne) zamiast osobnej tabeli/etykiety
- implikowane etykiety → klucze obce (rola nie istnieje bez osoby); to, co w grafie wymagało obejścia z 22NC4 (Person jako zwykłe CONSTRAINT), tu jest naturalne
- logowanie: role sprawdzane 3× `LEFT JOIN` zamiast `u:Admin` itd.

6.2.3 Ograniczenia, których graf nie wyrażał
- `SubjectInstance` bez właściwości: w SQL klucz główny złożony (subject_code, cycle_id) – problem 22NC2 nie istnieje
- unikalność numeru grupy w obrębie formy zajęć: `UNIQUE (group_type_id, number)` – w grafie niemożliwe (klucz obejmował krawędź, 4.3.3)
- typy wyliczeniowe / dozwolone wartości: `CHECK (weekday BETWEEN 1 AND 7)`, `CHECK (pnp IN (...))`, `CHECK (season IN ('Z','L'))`, skala ocen `CHECK (grade IN (2.0, ..., 5.0))` – w grafie tylko w Pydantic (5.3.1)
- kardynalność: krawędź N:1 jako kolumna z jednym kluczem obcym = najwyżej jedna sala na grupę (w grafie nic tego nie pilnowało, 4.3.7)
- jedna opinia na trójkę student–grupa–prowadzący: `UNIQUE` (w grafie sprawdzane w API + blokada)
- najwyżej jedna tura na rejestrację: `assigned` ma kolumnę `registration_id` i złożony klucz obcy (turn_id, registration_id) → `UNIQUE (student_idx, registration_id)`; cena: zdenormalizowana kolumna
- reguły, których i SQL nie wyrazi prostym ograniczeniem: wagi sumują się do 1, kolizje sal, „prowadzący uczy tę grupę” w opinii (możliwe złożonym FK do `teaches`, świadomie pominięte, bo blokowałoby usunięcie prowadzącego z grupy)
- indeksy: PK i UNIQUE indeksowane automatycznie, klucze obce nie – dodane ręcznie indeksy na FK używanych w zapytaniach

6.2.4 Typy danych
- `ZONED DATETIME` vs `timestamptz` dla chwil (moment zapisu, dezaktywacji, rozpoczęcia studiów): Neo4j zachowuje oryginalne przesunięcie lub nazwaną strefę (+02:00, `Europe/Warsaw`), PostgreSQL przechowuje chwilę w UTC i tak ją zwraca – ta sama chwila, inny zapis; wykryte przy porównaniu odpowiedzi (`bench/compare.py`)
- `LOCAL TIME` vs `time` dla godzin zajęć i tur (pierwotnie `ZONED TIME` vs `timetz`, zmienione z powodu zmiany czasu, 5.3.1); dokumentacja PostgreSQL odradza `timetz` [CYTOWANIE: https://www.postgresql.org/docs/current/datatype-datetime.html]
- godzina tury łączona z datą w strefie uczelni: `datetime({date, time, timezone: 'Europe/Warsaw'})` vs `(date + time) AT TIME ZONE 'Europe/Warsaw'`
- `FLOAT` vs `numeric(2,1)` dla ocen (dokładna wartość dziesiętna)
- sortowanie tekstu: domyślna kolacja PostgreSQL ≠ porządek Neo4j → `COLLATE "C"` (porządek kodów znaków), żeby wyniki były identyczne

6.3 Import danych i konfiguracja bazy
- te same pliki CSV co dla Neo4j (`import/`) – identyczne dane w obu bazach
- mechanizm `docker-entrypoint-initdb.d` obrazu PostgreSQL: skrypty wykonywane automatycznie przy pierwszym uruchomieniu na pustym wolumenie – wbudowany mechanizm, którego brakowało w Neo4j (serwis `init`, 5.1.4); wada: wykonuje się tylko raz, zmiana hasła w `.env` nie zostanie zastosowana (odwrotnie niż `CREATE OR REPLACE USER`)
- `02_import.sql`: `COPY` do tymczasowych tabel pośrednich (tekst), potem `INSERT ... SELECT ... JOIN` – krawędź N:1 trzeba „dokleić” do wiersza węzła; cały import w jednej transakcji (wszystko albo nic), tak samo jak import węzłów i krawędzi w `init_db.py` (5.3.2)
- konto aplikacji (`03_security.sh`): tylko SELECT/INSERT/UPDATE/DELETE, bez DDL i bez `pg_read_server_files` (odpowiednik `DENY LOAD`); zmienne psql `:"user"` / `:'pw'` są cytowane przez psql → wbudowane narzędzie przekazuje dane konta bezpiecznie; w Neo4j wymagało to własnego skryptu ze sterownikiem w miejsce `cypher-shell --param` (tabela z 5.1.4)
- TLS: osobny certyfikat `postgres`, `sslmode=verify-full` po stronie API, `pg_hba.conf` odrzuca połączenia bez TLS (`hostnossl ... reject`), TLS 1.3
- klucz prywatny: PostgreSQL odrzuca klucz czytelny dla innych → skrypt `start.sh` kopiuje go z prawami 600
- healthcheck `pg_isready -h 127.0.0.1`: tymczasowy serwer podczas inicjalizacji słucha tylko na gnieździe Unix, więc test przechodzi dopiero po imporcie

6.4 Backend relacyjny
- katalog `app/relation_backend/` obok `graph_backend/`: `database.py` (pula połączeń psycopg), `query.py` (`run`, `one` jak w 5.5.5), `errors.py` (IntegrityError → 409, DataError → 400), `routers/`
- te same modele Pydantic, te same zależności uwierzytelniania i autoryzacji (`require`, `Caller`), ta sama funkcja `average_grade`
- punkty końcowe pod prefiksem `/api/rel` – identyczne ścieżki i kontrakt, różni się tylko baza
- transakcja na żądanie: `pool.connection()` zatwierdza po sukcesie, wycofuje po wyjątku
- ReBAC w SQL: te same „ścieżki”, tylko jako złączenia tabel łączących (`teaches ⋈ registered_in`)
- poprawność: `bench/compare.py` – 13 przypadków (w tym błędy 401/403/422), identyczne odpowiedzi obu backendów

6.4.1 Współbieżność w PostgreSQL
- oba systemy domyślnie READ COMMITTED, ale inaczej: w PostgreSQL instrukcja widzi migawkę z chwili swojego startu – po oczekiwaniu na blokadę ponownie czyta tylko zablokowany wiersz, nie liczbę zapisanych → jedna kwerenda z blokadą (jak w Cypher, 5.5.10) NIE wystarczy
- rozwiązanie: blokady osobnymi instrukcjami (`SELECT ... FOR UPDATE`: student, potem grupa – stała kolejność), dopiero potem sprawdzenie warunków i `INSERT` nową instrukcją (nowa migawka)
- jawna składnia blokady (`FOR UPDATE`) zamiast sztuczki `SET x = x`
- alternatywa niedostępna w Neo4j: poziom SERIALIZABLE (wymaga ponawiania transakcji)
- // test współbieżności jak w 5.5.10 (scenariusze A–D) dla backendu relacyjnego – do zrobienia

6.5 Metodyka pomiarów
- porównywane zapytania (te z pracy): prosta (logowanie, sprawdzenia ReBAC), średnia (studenci w grupie, opinie, grupy w zapisach), trudna (oceny studenta do średniej, katalog przedmiotów), zapis (wystawienie oceny, zapis do grupy)
- miary:
  - złożoność zapytania: liczba przejść po krawędziach (Cypher) vs liczba `JOIN` i podzapytań (SQL), długość zapytania
  - czas zapytania mierzony przez sterownik (wykonanie + pobranie wszystkich wierszy), mediana i p95 z N powtórzeń po rozgrzaniu
  - czas raportowany przez bazę: Neo4j `result_available_after + result_consumed_after`, PostgreSQL „Execution Time” z `EXPLAIN ANALYZE` (+ osobno „Planning Time”)
  - praca bazy: Neo4j – suma *db hits* z `PROFILE`; PostgreSQL – bloki bufora (hit + read) z `EXPLAIN (ANALYZE, BUFFERS)`; UWAGA: różne jednostki (operacja na magazynie vs strona 8 kB) – porównywalne tylko w obrębie jednej bazy, np. jak rosną ze skalą
  - czas całego żądania HTTP przez API (TLS, FastAPI, walidacja, baza, serializacja) – to, co widzi użytkownik
- zapisy wykonywane w transakcji wycofywanej (pomiar bez trwałej zmiany danych)
- narzędzia: `bench/db_profile.py` (uruchamiany w kontenerze `app`), `bench/http_bench.py`, `bench/compare.py`
- skala danych: dane początkowe są za małe (29 studentów, 129 grup) – czasy zdominowane przez stały narzut protokołu; // GENERATOR DANYCH w kilku skalach (np. ×1, ×10, ×100) w tym samym formacie CSV – do zrobienia

6.6 Wyniki
- // tabela: zapytanie | klasa | przejścia (Cypher) | JOIN (SQL) | czas Neo4j | czas PostgreSQL | db hits | bufory
- // wykres: czas vs skala danych dla każdej klasy zapytań
- wstępne wyniki na danych początkowych (do zastąpienia wynikami w kilku skalach):
  - czas zapytania (sterownik): Neo4j ok. 1,6–2,1 ms dla prostych i średnich, PostgreSQL ok. 0,1–0,25 ms; katalog przedmiotów 8,6 ms vs 5,3 ms
  - żądanie HTTP: Neo4j 2,3–3,3 ms, PostgreSQL ok. 1,0–1,3 ms; katalog 10,4 ms vs 7,3 ms; logowanie ok. 180 ms w obu (bcrypt)
  - złożoność: logowanie 0 przejść vs 3 JOIN; grupy w zapisach 8 przejść vs 5 JOIN; katalog 16 wzorców krawędzi vs 9 JOIN + podzapytania
  - sprawdzenie tury studenta: 79 db hits vs 1 blok bufora – efekt denormalizacji `assigned.registration_id`
- // interpretacja: stały narzut Bolt/transakcji w Neo4j vs PostgreSQL; jak zmienia się przy większych danych

6.7 Wnioski z porównania
- // czytelność zapytań: Cypher krótszy przy ścieżkach, SQL przy prostych odczytach
- // integralność: model relacyjny wymusza więcej reguł w samej bazie (klucze złożone, CHECK, kardynalność)
- // wydajność: do uzupełnienia po pomiarach w kilku skalach
- // nawiązać do wniosków z rozdziału 8 („konceptualizować grafowo, implementować relacyjnie”)
