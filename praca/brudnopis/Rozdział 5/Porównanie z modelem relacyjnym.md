6.1 Cel i zakres porównania

Aby porównać model grafowy z relacyjnym, wybrane punkty końcowe API zaimplementowano równolegle z wykorzystaniem relacyjnej bazy danych. Obie wersje działają w jednym procesie API pod prefiksami `/api` (Neo4j) i `/api/rel` (PostgreSQL). Mają identyczne ścieżki, modele Pydantic oraz mechanizmy uwierzytelniania i autoryzacji, więc różnią się jedynie warstwą bazy danych.

Jako bazę relacyjną wykorzystano PostgreSQL 18.1 (oficjalny obraz `postgres:18.1`), uruchamiany razem z Neo4j 2026.07.1 Enterprise w ramach tego samego pliku `docker-compose.yml`. Konfiguracja obu baz jest analogiczna: szyfrowanie TLS z weryfikacją certyfikatu, osobne konto aplikacji o ograniczonych uprawnieniach oraz automatyczny import danych przy pierwszym uruchomieniu (6.3). Pozostawiono domyślne parametry wydajnościowe bez nakładania limitów zasobów na kontenery. Parametry sprzętowe środowiska testowego podano w 7.1.

W obu wariantach wykorzystano asynchroniczne sterowniki dla języka Python 3.14:
- Neo4j: `neo4j` 6.2.0 (protokół Bolt),
- PostgreSQL: `psycopg` 3.3.9 z pulą połączeń `psycopg-pool` 3.3.3.

6.2 Model relacyjny

![[PostgreSQL@localhost - usos - public 1.png]]

Ze względu na dużą liczbę tabel diagram wygenerowany przez narzędzie DBeaver jest nieczytelny.

6.2.1 Przekształcenie grafu w tabele

Schemat relacyjny zaprojektowano w trzeciej postaci normalnej (3NF), odwzorowując model grafowy z 4.3. Większość typów węzłów przeniesiono wprost – każdej etykiecie odpowiada tabela, a właściwościom kolumny. Wyjątkiem są osoby (6.2.2) oraz grupy zajęciowe: słowo `group` jest w SQL zastrzeżone, dlatego etykiecie `Group` odpowiada tabela `class_group`.

Krawędzie odwzorowano przy użyciu kluczy obcych, zgodnie z ich kardynalnością (4.3.6):
- relacje N:1 i 1:N zapisano jako kolumnę z kluczem obcym po stronie „wielu”, np. `programme.faculty_id` (`OFFERED_BY`) czy `class_group.group_type_id` (`OF_TYPE`),
- relacje N:M wydzielono do tabel łączących z kluczem głównym złożonym z dwóch kluczy obcych (`term_subject`, `teaches`, `works_at`, `enrolled`, `opens`). Tabela `registered_in` przechowuje dodatkowo datę zapisu (`registered_at`), a `assigned` kolumnę potrzebną do wymuszenia ograniczenia z 6.2.3,
- opcjonalne relacje N:1 (`TAUGHT_IN`, `IN_ROOM`) zapisano w osobnych tabelach (`taught_in`, `in_room`) z kluczem głównym będącym kluczem obcym do tabeli nadrzędnej, aby uniknąć kolumn dopuszczających wartość `NULL`.

Z tego samego powodu w osobnych tabelach umieszczono opcjonalne właściwości (`person_photo`, `subject_ects`, `opinion_content`) oraz ocenę z krawędzi `REGISTERED_IN` (`grade`), gdzie brak wartości odpowiada brakowi wiersza. Łącznie schemat obejmuje 31 tabel.

6.2.2 Osoby i role bez wieloetykietowości

Ponieważ w modelu relacyjnym jeden wiersz nie może mieć wielu etykiet, dane wspólne (`Person`) umieszczono w tabeli `person`, a każdą pozostałą etykietę osoby (`Student`, `Teacher`, `Admin`, `User` jako `app_user` oraz `Inactive`) w osobnej tabeli. Klucz główny takiej tabeli jest zarazem kluczem obcym do tabeli nadrzędnej, więc osoba pełniąca kilka ról ma odpowiadające sobie wiersze w kilku tabelach.

Taki klucz obcy pełni funkcję analogiczną do etykiety implikowanej – wiersz roli nie powstanie bez wpisu w `person`, co w Neo4j wymagało obejścia błędu 22NC4 za pomocą instrukcji `CONSTRAINT` (5.3.1). W tabeli `inactive` klucz obcy odnosi się bezpośrednio do `app_user`, dzięki czemu baza sama pilnuje, by dezaktywacja dotyczyła wyłącznie istniejącego konta (w grafie ograniczenie to wymusza API, 5.3.1). Opcja `ON DELETE CASCADE` zapewnia ponadto automatyczne skasowanie wpisu w `inactive` przy usunięciu konta.

Rozbicie ról na osobne tabele wymusza jednak stosowanie złączeń. Przykładowo zapytanie logowania (por. 5.4.2) musi sprawdzić dezaktywację oraz każdą rolę osobnym `LEFT JOIN`:

```sql
SELECT
  u.passwd_hash, u.email, u.idx,
  i.idx IS NOT NULL AS inactive,
  a.idx IS NOT NULL AS admin,
  t.idx IS NOT NULL AS teacher,
  s.idx IS NOT NULL AS student
FROM app_user u
LEFT JOIN inactive i ON i.idx = u.idx
LEFT JOIN admin a ON a.idx = u.idx
LEFT JOIN teacher t ON t.idx = u.idx
LEFT JOIN student s ON s.idx = u.idx
WHERE u.email = %(email)s
```

6.2.3 Ograniczenia wymuszane przez bazę relacyjną

Wiele reguł dziedzinowych, które w wariancie grafowym sprawdza API lub walidacja Pydantic, w PostgreSQL udało się przenieść bezpośrednio do schematu bazy. Zestawiono je w poniższej tabeli.

| Reguła | Neo4j | PostgreSQL |
|---|---|---|
| instancja przedmiotu bez właściwości | pominięta w typie grafu (22NC2, 5.3.1) | tabela `subject_instance` z kluczem `(subject_code, cycle_id)` |
| jedna instancja na parę przedmiot–cykl (4.3.2) | API | ten sam klucz główny |
| przynależność formy zajęć do jednej instancji (4.3.2) | API | klucz obcy `NOT NULL` w `group_type` |
| unikalność numeru grupy w obrębie formy zajęć (4.3.3) | brak możliwości zapisu (klucz obejmuje krawędź) | `UNIQUE (group_type_id, number)` |
| obowiązkowe powiązanie, np. forma zajęć grupy (4.3.7) | API | klucz obcy `NOT NULL` |
| kardynalność po stronie „jeden”, np. jedna sala dla grupy (4.3.7) | API | pojedyncza kolumna klucza obcego lub klucz główny (`in_room`, `taught_in`) |
| dozwolone wartości (dzień tygodnia, `pnp`, semestr Z/L, oceny, 5.3.1) | Pydantic | `CHECK` |
| dezaktywacja wyłącznie istniejącego konta (5.3.1) | API | klucz obcy `inactive` → `app_user` (6.2.2) |
| jedna opinia na trójkę student–grupa–prowadzący | API i blokada (5.5.10) | `UNIQUE (student_idx, group_id, teacher_idx)` |
| najwyżej jedna tura w ramach jednych zapisów (4.3.6) | API | `UNIQUE (student_idx, registration_id)` w `assigned` |
*Reguły modelu wymuszane przez bazę relacyjną*

Wymuszenie ostatniej reguły wymagało niewielkiej denormalizacji: w tabeli `assigned` zapisano dodatkowo identyfikator zapisów (`registration_id`), mimo że wynika on z samej tury. Zgodność obu kolumn gwarantuje złożony klucz obcy `(turn_id, registration_id)` do `registration_turn`, co pozwala nałożyć ograniczenie unikalności na parę `(student_idx, registration_id)`.

Części reguł nie da się jednak zapisać prostymi ograniczeniami również w SQL – dotyczy to sumowania się wag form zajęć do 1 oraz wykrywania kolizji sal (4.3.3), które wymagałyby wyzwalaczy. Z kolei warunek, by opinia dotyczyła prowadzącego przypisanego do danej grupy, można by wymusić złożonym kluczem obcym do `teaches`, jednak świadomie z niego zrezygnowano, gdyż zablokowałby on usunięcie przypisania prowadzącego do grupy mającej już opinie.

Ponieważ PostgreSQL indeksuje automatycznie wyłącznie klucze główne i kolumny `UNIQUE`, indeksy na kluczach obcych wykorzystywanych w porównywanych zapytaniach dodano ręcznie.

6.3 Import danych i konfiguracja bazy

W odróżnieniu od Neo4j, które wymagało osobnego serwisu `init` (5.1.4), oficjalny obraz PostgreSQL ma wbudowany mechanizm inicjalizacji. Przy pierwszym starcie na pustym wolumenie wykonuje alfabetycznie skrypty z katalogu `/docker-entrypoint-initdb.d` [CYTOWANIE: https://hub.docker.com/_/postgres]. Zamontowano tam trzy pliki: `01_schema.sql` (schemat i indeksy), `02_import.sql` (import danych) oraz `03_security.sh` (konto API). Ponieważ skrypty uruchamiają się jednorazowo, modyfikacja schematu, danych lub hasła z `.env` wymaga usunięcia wolumenu `pg_data` (w Neo4j skrypt `init_db.py` aktualizuje hasło przy każdym starcie, 5.1.4).

Dane początkowe pochodzą z tych samych plików CSV co w wariancie grafowym, ale przekształcono je wcześniej do układu tabel z 6.2.1 (katalog `sql/data/`). Skrypt `02_import.sql` wczytuje je w jednej transakcji instrukcjami `COPY` w kolejności wynikającej z zależności kluczy obcych:

```sql
COPY person       FROM '/data/person.csv'       WITH (FORMAT csv, HEADER match);
COPY person_photo FROM '/data/person_photo.csv' WITH (FORMAT csv, HEADER match);
```

Opcja `HEADER match` dodatkowo weryfikuje zgodność nagłówków pliku z nazwami kolumn w tabeli [CYTOWANIE: https://www.postgresql.org/docs/current/sql-copy.html].

Konto API tworzone w `03_security.sh` otrzymuje wyłącznie uprawnienia `SELECT`, `INSERT`, `UPDATE` i `DELETE` na tabelach. Nie ma prawa modyfikować schematu ani przypisanej roli `pg_read_server_files` (odpowiednik `DENY LOAD` w Neo4j). Nazwę i hasło konta przekazano jako zmienne narzędzia `psql`:

```sql
CREATE ROLE :"user" LOGIN PASSWORD :'pw';
```

Narzędzie `psql` automatycznie ujmuje takie zmienne w odpowiednie znaki ograniczające (`:"user"` jako identyfikator, `:'pw'` jako literał) i zabezpiecza znaki specjalne [CYTOWANIE: https://www.postgresql.org/docs/current/app-psql.html]. Dzięki temu znaki takie jak apostrof w haśle nie powodują błędu ani wstrzyknięcia SQL, więc nie trzeba było pisać osobnego skryptu w Pythonie jak dla `cypher-shell` (5.1.4).

Szyfrowanie połączeń skonfigurowano analogicznie do Neo4j: serwer korzysta z własnego certyfikatu (5.1.1), a API łączy się w trybie `sslmode=verify-full` (weryfikacja podpisu i nazwy hosta). W pliku `pg_hba.conf` zablokowano połączenia sieciowe bez TLS, ustawiając minimalną wersję protokołu na TLS 1.3 i uwierzytelnianie haseł metodą SCRAM-SHA-256.

Przy uruchamianiu kontenera należało uwzględnić jeszcze dwie kwestie techniczne. Po pierwsze, PostgreSQL nie akceptuje klucza prywatnego z uprawnieniami odczytu dla innych użytkowników, natomiast zamontowany plik ma prawa `644` (5.1.1); skrypt `start.sh`, uruchamiany przed właściwym skryptem startowym obrazu, kopiuje więc klucz z uprawnieniami `600`. Po drugie, test stanu (`pg_isready -h 127.0.0.1`) łączy się po TCP. Ponieważ w trakcie inicjalizacji tymczasowa instancja nasłuchuje wyłącznie na gnieździe Unix, test zwraca wynik pozytywny dopiero po zakończeniu importu, co gwarantuje, że serwis `app` nie wystartuje przed załadowaniem danych.

6.4 Backend relacyjny

Implementacja relacyjna znajduje się w katalogu `app/relation_backend/` i powiela układ modułów backendu grafowego (`database.py`, `query.py`, `errors.py`, `routers/`). Obejmuje osiem punktów końcowych dobranych tak, by reprezentowały zapytania różnej złożoności (7.4.2): logowanie, katalog przedmiotów, listę opinii, grupy dostępne w zapisach, zapis na grupę, dane studenta ze średnią, listę studentów w grupie oraz wystawienie oceny. Poza modelami i warstwą uwierzytelniania (`require`, `Caller`, 5.5.6–5.5.7) oba backendy współdzielą funkcje dziedzinowe, takie jak `average_grade()` (5.5.5), a wydawane tokeny JWT są między nimi wymienne.

Różnice względem wersji grafowej wynikają bezpośrednio ze sterownika i silnika bazy:
- Połączenia udostępnia współdzielona pula `psycopg_pool` (analogicznie do sterownika Neo4j w 5.5.3). Każde żądanie działa w jednej transakcji, którą zależność `get_conn()` zatwierdza po zakończeniu obsługi lub wycofuje przy wyjątku (w 5.5.3 pojedyncze zapytania korzystają z transakcji automatycznych).
- Funkcje `run()` i `one()` zachowują sygnatury z 5.5.5 i przekazują parametry osobno od treści zapytania (`%(name)s`). Ponieważ `psycopg` zwraca standardowe typy Pythona (`datetime`, `Decimal`), nie ma potrzeby stosowania funkcji `native()`.
- Moduł `errors.py` obsługuje wyjątki `psycopg` analogicznie do 5.5.2: naruszenie ograniczenia (`IntegrityError`) zwraca kod 409, błędna wartość (`DataError`) kod 400, a pozostałe błędy kod 500.

Kontrola dostępu oparta na relacjach (ReBAC, 5.5.7) odzwierciedla te same zależności co w grafie, przy czym przejścia po krawędziach odpowiadają tu złączeniom tabel – na przykład przy sprawdzaniu, czy prowadzący uczy danego studenta:

```sql
SELECT ri.student_idx AS idx
FROM teaches te
JOIN registered_in ri ON ri.group_id = te.group_id
WHERE te.teacher_idx = %(teacher_idx)s AND ri.student_idx = %(student_idx)s
LIMIT 1
```

Zgodność odpowiedzi obu implementacji zweryfikowano testem z 7.4.1.

6.4.1 Współbieżność w PostgreSQL

Domyślnym poziomem izolacji w PostgreSQL, podobnie jak w Neo4j, jest *read committed*, jednak jego realizacja różni się istotnym szczegółem. Każda instrukcja SQL widzi migawkę (ang. *snapshot*) danych z momentu swojego rozpoczęcia. Jeżeli transakcja czekała na blokadę wiersza, po jej zwolnieniu baza ponownie odczytuje tylko ten konkretny wiersz, podczas gdy pozostałe dane – na przykład liczba zapisanych do grupy – nadal pochodzą ze starej migawki [CYTOWANIE: https://www.postgresql.org/docs/current/transaction-iso.html].

Z tego powodu przeniesienie wzorca z 5.5.10, czyli połączenie blokady i sprawdzenia warunków w jednym zapytaniu, nie chroni przed przepełnieniem grupy (7.3.2):

```sql
WITH locked AS (
  SELECT id, capacity FROM class_group WHERE id = %(group_id)s FOR UPDATE
)
INSERT INTO registered_in (student_idx, group_id)
SELECT %(student_idx)s, id FROM locked
WHERE (SELECT count(*) FROM registered_in WHERE group_id = %(group_id)s) < locked.capacity
```

*Blokada i sprawdzenie w jednej instrukcji – wzorzec z 5.5.10 przeniesiony do SQL*

Zapis na grupę rozbito więc na trzy instrukcje wykonywane w ramach jednej transakcji (6.4):
1. `SELECT ... FOR UPDATE` blokuje wiersz studenta.
2. `SELECT ... FOR UPDATE OF g` blokuje wiersz grupy pod warunkiem, że trwa tura studenta w zapisach otwierających tę grupę; brak zwróconego wiersza oznacza odmowę (kod 403), dzięki czemu zapytanie pełni jednocześnie rolę sprawdzenia ReBAC.
3. Kolejna instrukcja, działająca już na nowej migawce, sprawdza warunki zapisu i wstawia wiersz do `registered_in` (odpowiednik kwerendy `_REGISTER` bez linii `SET`).

Aby zapobiec zakleszczeniom, blokady zakłada się w tej samej kolejności co w grafie (najpierw student, potem grupa). SQL oferuje przy tym jawną składnię blokady wiersza (`FOR UPDATE`), dzięki czemu zbędny jest pozorny zapis jak w języku Cypher (`SET g.capacity = g.capacity`). PostgreSQL udostępnia także poziom izolacji *serializable*, jednak wymaga on obsługi i ponawiania transakcji odrzuconych przez bazę, dlatego pozostano przy jawnych blokadach.

Poprawność tego rozwiązania oraz nieskuteczność wariantu jednoinstrukcyjnego potwierdził test współbieżności (7.3.2).
