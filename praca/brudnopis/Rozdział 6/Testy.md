zrob pod koniec na szybko


7.1 Środowisko testowe

Wszystkie testy i pomiary wykonano lokalnie na tym samym komputerze, z całym środowiskiem uruchomionym przez Docker Compose (5.1):
- procesor: AMD Ryzen 7 5800X (8 rdzeni, 16 wątków, do 4,85 GHz),
- pamięć RAM: 16 GB,
- dysk: SSD NVMe ADATA XPG SX8200 Pro 512 GB,
- system: Arch Linux (jądro 7.2.11), Docker 29.9.2.

7.2 Uwierzytelnianie i kontrola dostępu

7.2.1 Atak czasowy na logowanie

Skrypt `tests/test_login_timing.py` mierzy czas odpowiedzi punktu końcowego `POST /api/login` w trzech przypadkach: dla istniejącego użytkownika z poprawnym hasłem, z błędnym hasłem oraz dla nieistniejącego adresu. Wyniki zestawiono w poniższej tabeli. Przed poprawką z 5.5.6 żądanie z nieistniejącym adresem kończyło się po ok. 4 ms, natomiast dla istniejącego konta z błędnym hasłem po ok. 184 ms, co pozwalało wykryć obecność adresu w bazie. Po wprowadzeniu skrótu zastępczego czasy odpowiedzi we wszystkich trzech przypadkach są praktycznie jednakowe.

| Przypadek | Kod | Mediana przed poprawką [ms] | Mediana po poprawce [ms] |
| --- | :---: | ---: | ---: |
| istniejące konto, poprawne hasło | 200 | 185,1 | 183,6 |
| istniejące konto, błędne hasło | 401 | 183,7 | 183,3 |
| nieistniejące konto | 401 | 4,0 | 183,2 |

*Czas odpowiedzi `POST /api/login`, 30 prób na przypadek*

7.2.2 Kolejność sprawdzeń w punkcie końcowym

Weryfikacja tokenu i roli (krok 3 w 5.5.8) następuje przed walidacją treści żądania (krok 4). Sprawdzono to na przykładzie `PUT /groups/{group_id}/students/{student_idx}/grade`, wysyłając niepoprawną ocenę 4.2: żądanie bez tokenu zwróciło kod 401, z tokenem studenta – 403, a dopiero z tokenem administratora – 422. Potwierdza to, że komunikaty walidacji nie są ujawniane użytkownikom bez uprawnień.

7.2.3 Cykl życia konta

Działanie operacji na kontach (5.5.9) zweryfikowano na przykładzie studenta o indeksie 285904, który w danych początkowych nie ma konta. Przebieg testu przedstawiono w poniższej tabeli.

| Krok | Odpowiedź |
| --- | --- |
| `POST /admin/users` – utworzenie konta | 201 |
| `POST /login` | 200, token |
| `PATCH /admin/users/285904` z `{"active": false}` | 200 |
| `POST /login` | 403 `Account inactive` |
| żądanie z tokenem wydanym przed dezaktywacją | 401 `Token revoked` |
| `PATCH /admin/users/285904` z `{"active": true}`, następnie `POST /login` | 200, 200 |
| `DELETE /admin/users/285904` | 204 |
| `POST /login` | 401 `Invalid email or password` |
| `GET /students/285904` (administrator) | 200 – dane osoby pozostają w bazie |
| `DELETE /admin/users/A001` (własne konto administratora) | 409 `Cannot remove your own account` |

*Cykl życia konta użytkownika*

Piąty wiersz potwierdza natychmiastowe unieważnianie tokenów po dezaktywacji konta. Przed dodaniem tego mechanizmu (5.5.6) to samo żądanie kończyło się kodem 200 aż do wygaśnięcia tokenu.

7.2.4 Odebranie roli a wcześniej wydany token

Unieważnianie tokenów po odebraniu roli administratora (5.5.10) sprawdzono na przykładzie studenta o indeksie 279413, któremu nadano rolę `Admin`, a po zalogowaniu ją cofnięto. Wyniki zestawiono w poniższej tabeli.

| Krok | Bez unieważniania | Z unieważnianiem |
| --- | --- | --- |
| `GET /admin/people/next-idx` przed odebraniem roli | 200 | 200 |
| `GET /admin/people/next-idx` po odebraniu roli, stary token | 200 | 401 `Token revoked` |
| `PATCH /admin/users/281056` z `{"active": false}`, stary token | 200 | 401 `Token revoked` |
| ponowne logowanie, `GET /admin/people/next-idx` | 403 | 403 |

*Odebranie roli `Admin` a wcześniej wydany token*

Bez tego mechanizmu użytkownik pozbawiony uprawnień administracyjnych mógłby aż do wygaśnięcia tokenu wywoływać punkty końcowe administratora, w tym dezaktywować cudze konta.

7.3 Współbieżność

7.3.1 Backend grafowy

Działanie blokad podczas zapisów na zajęcia (5.5.10) zweryfikowano skryptem `tests/test_concurrent_registration.py`. Tworzy on w bazie tymczasową rejestrację z aktywną turą oraz grupy, wysyła równoległe żądania zwalniane wspólną barierą wątków, a na koniec usuwa wprowadzone dane. W scenariuszu kontrolnym C tę samą kwerendę uruchomiono bez linii `SET` wymuszających blokadę, natomiast scenariusz D sprawdza blokadę przy jednoczesnym odbieraniu ról. Wyniki z trzech uruchomień przedstawiono w poniższej tabeli.

| Scenariusz | Żądania | Odpowiedzi | Stan bazy |
| --- | ---: | --- | --- |
| A: 10 studentów, grupa z 3 miejscami | 10 | 3 × 204, 7 × 409 `Group is full` | 3 zapisanych |
| B: 5 studentów, każdy jednocześnie do 2 grup tego samego typu | 10 | 5 × 204, 5 × 409 (inna grupa tego typu) | każdy student w 1 grupie |
| C: jak A, kwerenda bez blokad | 10 | 10 × `ok` | **10 zapisanych** |
| D: jednoczesne odebranie obu ról osobie z rolami `Teacher` i `Student` | 2 | 1 × 200, 1 × 409 `Cannot remove last role` | pozostała jedna rola |

*Wyniki testu współbieżnych zapisów (trzy uruchomienia, identyczne wyniki)*

Scenariusz C potwierdza, że pojedyncza kwerenda bez jawnych blokad nie chroni przed przepełnieniem – do grupy z 3 miejscami zapisało się wówczas 10 studentów.

7.3.2 Backend relacyjny

Analogiczny test dla wariantu relacyjnego (6.4.1) zaimplementowano w skrypcie `tests/test_concurrent_registration_rel.py`. Scenariusze A i B powtarzają przypadki z 7.3.1, pominięto natomiast scenariusz D, ponieważ backend relacyjny nie obsługuje odbierania ról. Przypadek kontrolny rozdzielono na dwa warianty: C1 (zapytanie bez blokad) oraz C2 (blokada i sprawdzenie warunków w jednej instrukcji). Oba wykonano bezpośrednio przez sterownik w osobnych połączeniach, utrzymując każdą transakcję otwartą przez 100 ms przed zatwierdzeniem, aby wymusić jednoczesne wykonanie zapytań. Wyniki zestawiono w poniższej tabeli.

| Scenariusz | Żądania | Odpowiedzi | Stan bazy |
| --- | ---: | --- | --- |
| A: 10 studentów, grupa z 3 miejscami | 10 | 3 × 204, 7 × 409 `Group is full` | 3 zapisanych |
| B: 5 studentów, każdy jednocześnie do 2 grup tego samego typu | 10 | 5 × 204, 5 × 409 (inna grupa tego typu) | każdy student w 1 grupie |
| C1: jak A, zapytanie bez blokad | 10 | 10 × `ok` | **10 zapisanych** |
| C2: jak A, blokada i sprawdzenie w jednej instrukcji | 10 | 10 × `ok` | **10 zapisanych** |

*Wyniki testu współbieżnych zapisów w backendzie relacyjnym (trzy uruchomienia, identyczne wyniki)*

Scenariusz C2 potwierdza, że w PostgreSQL blokada założona w tej samej instrukcji co sprawdzenie warunków nie zapobiega przepełnieniu – do grupy z 3 miejscami zapisało się wówczas 10 studentów, tak samo jak w wariancie bez blokad.

7.4 Porównanie z modelem relacyjnym

7.4.1 Zgodność backendów

Zgodność backendu relacyjnego (6.4) z grafowym weryfikuje skrypt `bench/compare.py`. Kieruje on identyczne żądania z tym samym tokenem JWT pod prefiksy `/api` oraz `/api/rel`, a następnie porównuje kody statusu i treść odpowiedzi JSON. We wszystkich 13 przypadkach testowych – łącznie z kodami błędów 401, 403 i 422 – obie implementacje zwróciły identyczne wyniki.

7.4.2 Metodyka pomiarów

Porównano zapytania obu backendów (6.4) podzielone na cztery klasy:
- proste: logowanie oraz dwa sprawdzenia ReBAC (czy prowadzący uczy grupę i czy student ma turę w zapisach),
- średnie: studenci w grupie, opinie o prowadzącym, grupy dostępne w zapisach,
- trudne: oceny studenta do wyznaczenia średniej, katalog przedmiotów,
- zapis: wystawienie oceny.

Zapisu na grupę nie uwzględniono w pomiarach wydajności, ponieważ wymaga aktywnej tury zapisów, a jego poprawność zweryfikowano osobno (7.3.2).

Dla każdego zapytania zarejestrowano:
- złożoność kwerendy: liczbę wzorców krawędzi (Cypher), liczbę złączeń i podzapytań (SQL) oraz długość tekstu zapytania,
- czas wykonania po stronie sterownika (od wysłania zapytania do pobrania wszystkich wierszy): medianę i 95. percentyl z 50 pomiarów poprzedzonych 10 próbami rozgrzewkowymi,
- czas wykonania podawany przez silnik bazy: w Neo4j sumę `result_available_after` i `result_consumed_after`, w PostgreSQL czas wykonania z `EXPLAIN ANALYZE` (z czasem planowania podanym osobno),
- koszt operacji w bazie: w Neo4j sumę odczytów magazynu danych (*db hits*) z `PROFILE`, w PostgreSQL liczbę stron bufora (trafień i odczytów) z `EXPLAIN (ANALYZE, BUFFERS)`; ze względu na różne jednostki wartości te porównuje się wyłącznie w obrębie jednej bazy,
- czas pełnego żądania HTTP (TLS, FastAPI, walidacja, zapytanie i serializacja), czyli opóźnienie po stronie klienta: medianę i 95. percentyl z 200 żądań poprzedzonych 20 próbami rozgrzewkowymi na jednym połączeniu (dla logowania ograniczono się do 20 żądań ze względu na dominujący czas funkcji bcrypt, 5.5.6).

Zapytania bazodanowe wykonuje skrypt `bench/db_profile.py` uruchamiany w kontenerze `app`, dzięki czemu oba sterowniki łączą się z bazami tak samo jak API. Każdy pomiar odbywa się w jawnej transakcji, a operacje zapisu są wycofywane, by nie modyfikować danych. Żądania HTTP wysyła z hosta skrypt `bench/http_bench.py`. Wszystkie pomiary przeprowadzono po wstępnym rozgrzaniu pamięci podręcznej obu baz.

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
