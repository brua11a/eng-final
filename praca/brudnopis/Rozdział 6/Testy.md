zrob pod koniec na szybko


7.1 Środowisko testowe

Wszystkie testy i pomiary wykonano na jednej maszynie, z całym środowiskiem uruchomionym w Docker Compose (5.1):
- procesor: AMD Ryzen 7 5800X (8 rdzeni, 16 wątków, do 4,85 GHz),
- pamięć RAM: 16 GB,
- dysk: SSD NVMe ADATA XPG SX8200 Pro 512 GB,
- system: Arch Linux (jądro 7.2.11), Docker 29.9.2.

7.2 Uwierzytelnianie i kontrola dostępu

7.2.1 Atak czasowy na logowanie

Test `tests/test_login_timing.py` mierzy czas odpowiedzi `POST /api/login` dla istniejącego konta z poprawnym hasłem, istniejącego konta z błędnym hasłem oraz nieistniejącego konta. Przed poprawką opisaną w 5.5.6 odpowiedź dla nieistniejącego konta przychodziła po ok. 4 ms, a dla istniejącego konta z błędnym hasłem po ok. 184 ms, co jednoznacznie zdradzało istnienie konta. Po wprowadzeniu skrótu zastępczego czasy wszystkich trzech przypadków są takie same.

| Przypadek | Kod | Mediana przed poprawką [ms] | Mediana po poprawce [ms] |
| --- | :---: | ---: | ---: |
| istniejące konto, poprawne hasło | 200 | 185,1 | 183,6 |
| istniejące konto, błędne hasło | 401 | 183,7 | 183,3 |
| nieistniejące konto | 401 | 4,0 | 183,2 |

*Czas odpowiedzi `POST /api/login`, 30 prób na przypadek*

7.2.2 Kolejność sprawdzeń w punkcie końcowym

Punkt końcowy sprawdza token i rolę (krok 3 w 5.5.8) przed walidacją treści żądania (krok 4). Sprawdzono to na `PUT /groups/{group_id}/students/{student_idx}/grade` z niepoprawną oceną 4.2: żądanie bez tokenu kończy się kodem 401, z tokenem studenta – 403, a dopiero z tokenem administratora – 422. Walidacja treści nie zdradza więc nic użytkownikowi bez uprawnień.

7.2.3 Cykl życia konta

Dezaktywację i usunięcie konta (5.5.9) sprawdzono na studencie 285904, który w danych początkowych nie ma konta:

| Krok | Odpowiedź |
| --- | --- |
| `POST /admin/users` – utworzenie konta | 201 |
| `POST /login` | 200, token |
| `PATCH /admin/users/285904` z `{"active": false}` | 200 |
| `POST /login` | 403 `Account inactive` |
| żądanie z tokenem wydanym przed dezaktywacją | 401 `Token revoked` |
| `PATCH /admin/users/285904` z `{"active": true}`, potem `POST /login` | 200, 200 |
| `DELETE /admin/users/285904` | 204 |
| `POST /login` | 401 `Invalid email or password` |
| `GET /students/285904` (administrator) | 200 – dane osoby nadal są w grafie |
| `DELETE /admin/users/A001` (własne konto administratora) | 409 `Cannot remove your own account` |

*Cykl życia konta użytkownika*

W piątym wierszu widać działanie unieważniania tokenów: token wydany przed dezaktywacją zostaje odrzucony od razu, mimo że nie wygasł. Przed wprowadzeniem mechanizmu unieważniania to samo żądanie kończyło się kodem 200, a token działał aż do wygaśnięcia, czyli nawet przez 12 godzin.

7.2.4 Odebranie roli a wcześniej wydany token

Odebranie roli unieważnia tokeny osoby (5.5.10), ponieważ punkty końcowe administratora sprawdzają wyłącznie rolę zapisaną w tokenie. Sprawdzono to na studencie 279413, któremu nadano rolę `Admin`, a po zalogowaniu ją odebrano:

| Krok | Bez unieważniania | Z unieważnianiem |
| --- | --- | --- |
| `GET /admin/people/next-idx` przed odebraniem roli | 200 | 200 |
| `GET /admin/people/next-idx` po odebraniu roli, stary token | 200 | 401 `Token revoked` |
| `PATCH /admin/users/281056` z `{"active": false}`, stary token | 200 | 401 `Token revoked` |
| ponowne logowanie, `GET /admin/people/next-idx` | 403 | 403 |

*Odebranie roli `Admin` a wcześniej wydany token*

Bez unieważniania osoba pozbawiona roli administratora mogła więc przez kolejne godziny dezaktywować konta innych użytkowników.

7.3 Współbieżność

7.3.1 Backend grafowy

Blokady w zapisie na grupę (5.5.10) sprawdzono testem `tests/test_concurrent_registration.py`. Test tworzy w bazie tymczasową rejestrację z trwającą turą i grupy testowe, wysyła żądania jednocześnie (wątki zwalniane wspólną barierą), a po zakończeniu usuwa dane testowe. W scenariuszu kontrolnym C tę samą kwerendę wykonano bez dwóch linii `SET`. Scenariusz D sprawdza blokadę przy odbieraniu ról.

| Scenariusz | Żądania | Odpowiedzi | Stan bazy |
| --- | ---: | --- | --- |
| A: 10 studentów, grupa z 3 miejscami | 10 | 3 × 204, 7 × 409 `Group is full` | 3 zapisanych |
| B: 5 studentów, każdy jednocześnie do 2 grup tego samego typu | 10 | 5 × 204, 5 × 409 (inna grupa tego typu) | każdy student w 1 grupie |
| C: jak A, kwerenda bez blokad | 10 | 10 × `ok` | **10 zapisanych** |
| D: jednoczesne odebranie obu ról osobie z rolami `Teacher` i `Student` | 2 | 1 × 200, 1 × 409 `Cannot remove last role` | osobie została jedna rola |

*Wyniki testu współbieżnych zapisów (trzy uruchomienia, identyczne wyniki)*

Scenariusz C potwierdza, że pojedyncza kwerenda bez jawnych blokad nie chroni przed przepełnieniem – do grupy z 3 miejscami zapisało się wówczas wszystkich 10 studentów.

7.3.2 Backend relacyjny

Blokady w zapisie na grupę w backendzie relacyjnym (6.4.1) sprawdzono testem `tests/test_concurrent_registration_rel.py`, odpowiednikiem testu z 7.3.1. Scenariusze A i B są takie same jak tam. Zamiast scenariusza kontrolnego C wykonano dwa: C1 – samo zapytanie sprawdzające i wstawiające zapis, bez blokad, oraz C2 – blokada i sprawdzenie warunków w jednej instrukcji. Scenariusz D nie ma odpowiednika, ponieważ backend relacyjny nie implementuje odbierania ról. Scenariusze kontrolne wykonano bezpośrednio przez sterownik, każde żądanie w osobnym połączeniu. Każda transakcja pozostawała otwarta przez 100 ms przed zatwierdzeniem, tak by żądania na pewno się nakładały.

| Scenariusz | Żądania | Odpowiedzi | Stan bazy |
| --- | ---: | --- | --- |
| A: 10 studentów, grupa z 3 miejscami | 10 | 3 × 204, 7 × 409 `Group is full` | 3 zapisanych |
| B: 5 studentów, każdy jednocześnie do 2 grup tego samego typu | 10 | 5 × 204, 5 × 409 (inna grupa tego typu) | każdy student w 1 grupie |
| C1: jak A, zapytanie bez blokad | 10 | 10 × `ok` | **10 zapisanych** |
| C2: jak A, blokada i sprawdzenie w jednej instrukcji | 10 | 10 × `ok` | **10 zapisanych** |

*Wyniki testu współbieżnych zapisów w backendzie relacyjnym (trzy uruchomienia, identyczne wyniki)*

Scenariusz C2 potwierdza, że w PostgreSQL blokada założona w tej samej instrukcji co sprawdzenie warunków nie wystarcza. Do grupy z 3 miejscami zapisało się wtedy wszystkich 10 studentów, tak jak bez żadnych blokad.

7.4 Porównanie z modelem relacyjnym

7.4.1 Zgodność backendów

Zgodność backendu relacyjnego (6.4) z grafowym sprawdza skrypt `bench/compare.py`. Wysyła on te same żądania, z tym samym tokenem, na `/api/...` i `/api/rel/...`, a następnie porównuje kody odpowiedzi i treść JSON. Wszystkie 13 przypadków, w tym odpowiedzi błędne 401, 403 i 422, daje identyczne wyniki.

7.4.2 Metodyka pomiarów

Porównano zapytania obu backendów (6.4), podzielone na cztery klasy:
- proste: logowanie oraz dwa sprawdzenia ReBAC – czy prowadzący uczy grupę i czy student ma turę w zapisach,
- średnie: studenci w grupie, opinie o prowadzącym, grupy dostępne w zapisach,
- trudne: oceny studenta potrzebne do wyznaczenia średniej, katalog przedmiotów,
- zapis: wystawienie oceny.

Zapisu na grupę nie mierzono, ponieważ wymaga trwającej tury zapisów, a jego poprawność sprawdzono osobno (7.3.2).

Dla każdego zapytania zebrano:
- złożoność kwerendy: liczbę wzorców krawędzi (Cypher), liczbę złączeń i podzapytań (SQL) oraz długość tekstu zapytania,
- czas zapytania mierzony przez sterownik, od wysłania zapytania do pobrania wszystkich wierszy – medianę i 95. percentyl z 50 wykonań poprzedzonych 10 wykonaniami rozgrzewkowymi,
- czas raportowany przez bazę: w Neo4j sumę `result_available_after` i `result_consumed_after`, w PostgreSQL czas wykonania z `EXPLAIN ANALYZE`, z czasem planowania podanym osobno,
- pracę bazy: w Neo4j sumę operacji na magazynie danych (*db hits*) z `PROFILE`, w PostgreSQL liczbę stron bufora (trafień i odczytów) z `EXPLAIN (ANALYZE, BUFFERS)`. Jednostki są różne, więc wartości te porównuje się wyłącznie w obrębie jednej bazy,
- czas całego żądania HTTP – TLS, FastAPI, walidacja, zapytanie i serializacja – czyli opóźnienie widziane przez klienta. Podano medianę i 95. percentyl z 200 żądań poprzedzonych 20 rozgrzewkowymi, wysyłanych kolejno jednym połączeniem. Logowanie wykonano 20 razy, ponieważ jego czas wyznacza głównie funkcja bcrypt (5.5.6).

Zapytania do baz wykonuje skrypt `bench/db_profile.py`, uruchamiany w kontenerze `app`, więc oba sterowniki łączą się z bazami tą samą drogą co API. Każde wykonanie odbywa się w jawnej transakcji, a transakcje z zapisem są wycofywane, by pomiar nie zmieniał danych. Żądania HTTP wysyła z hosta skrypt `bench/http_bench.py`. Wszystkie pomiary dotyczą stanu rozgrzanego, w którym dane znajdują się w pamięci podręcznej obu baz.

- // skala danych: dane początkowe są za małe (29 studentów, 129 grup) – czasy zdominowane przez stały narzut protokołu; GENERATOR DANYCH w kilku skalach (np. ×1, ×10, ×100) w tym samym formacie CSV – do zrobienia

7.4.3 Wyniki
- // tabela: zapytanie | klasa | przejścia (Cypher) | JOIN (SQL) | czas Neo4j | czas PostgreSQL | db hits | bufory
- // wykres: czas vs skala danych dla każdej klasy zapytań
- // UWAGA: poniższe wstępne wyniki pochodzą sprzed rozbicia tabel bez NULL (6.2.1) – liczby złączeń i czasy się zmienią, pomiary do powtórzenia
- wstępne wyniki na danych początkowych (do zastąpienia wynikami w kilku skalach):
  - czas zapytania (sterownik): Neo4j ok. 1,6–2,1 ms dla prostych i średnich, PostgreSQL ok. 0,1–0,25 ms; katalog przedmiotów 8,6 ms vs 5,3 ms
  - żądanie HTTP: Neo4j 2,3–3,3 ms, PostgreSQL ok. 1,0–1,3 ms; katalog 10,4 ms vs 7,3 ms; logowanie ok. 180 ms w obu (bcrypt)
  - złożoność: logowanie 0 przejść vs 3 JOIN; grupy w zapisach 8 przejść vs 5 JOIN; katalog 16 wzorców krawędzi vs 9 JOIN + podzapytania
  - sprawdzenie tury studenta: 79 db hits vs 1 blok bufora – efekt denormalizacji `assigned.registration_id`
- // interpretacja: stały narzut Bolt/transakcji w Neo4j vs PostgreSQL; jak zmienia się przy większych danych

7.4.4 Wnioski z porównania
- // czytelność zapytań: Cypher krótszy przy ścieżkach, SQL przy prostych odczytach
- // integralność: model relacyjny wymusza więcej reguł w samej bazie (klucze złożone, CHECK, kardynalność)
- // wydajność: do uzupełnienia po pomiarach w kilku skalach
- // nawiązać do wniosków z rozdziału 8 („konceptualizować grafowo, implementować relacyjnie”)
