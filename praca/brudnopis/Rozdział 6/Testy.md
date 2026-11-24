7.1 Środowisko i organizacja testów

Wszystkie testy funkcjonalne, bezpieczeństwa oraz pomiary wydajnościowe przeprowadzono lokalnie na komputerze z procesorem AMD Ryzen 7 5800X (8 rdzeni, 16 wątków, taktowanie do 4,85 GHz), 16 GB pamięci RAM oraz dyskiem SSD NVMe ADATA XPG SX8200 Pro 512 GB, pracującym pod kontrolą systemu Arch Linux (jądro 7.2.11) z uruchomionym środowiskiem Docker 29.9.2. Cały stos usług działał w kontenerach zarządzanych przez Docker Compose (5.1).

Zakres testów wyznaczono na podstawie wymagań z rozdziału 3. Każdy przypadek zaimplementowano jako niezależny skrypt w języku Python w katalogu `tests/`, uruchamiany zbiorczo skryptem `tests/run_all.py`, który zapisuje wyniki do katalogu `tests/wyniki/` i sygnalizuje niezgodności niezerowym kodem zakończenia. Żądania kierowano z hosta do działającego API przez protokół HTTPS z weryfikacją certyfikatu lokalnego CA. Operacje pomocnicze – przygotowanie danych testowych, weryfikację stanu bazy oraz generowanie tokenów JWT podpisanych kluczem API dla kont z danych początkowych – wykonywano w kontenerze `app` z użyciem tych samych kont bazodanowych, z których korzysta API. W testach samego logowania używano właściwych haseł. Obiekty tworzone na potrzeby testów oznaczano prefiksem `test-` i usuwano po zakończeniu przebiegu, a tymczasowe modyfikacje danych początkowych cofano. Wszystkie opisane poniżej testy zakończyły się wynikiem zgodnym z oczekiwanym.

7.2 Uwierzytelnianie i kontrola dostępu

7.2.1 Kontrola dostępu i kolejność sprawdzeń

Poprawność kontroli dostępu opartej na rolach (RBAC) oraz relacjach (ReBAC) zweryfikowano skryptem `tests/test_permissions.py`. Listę 59 punktów końcowych backendu grafowego pobrano ze specyfikacji OpenAPI udostępnianej przez API (5.4), a oczekiwane uprawnienia zdefiniowano niezależnie od kodu aplikacji na podstawie macierzy z tabel 3.1–3.3. Każdy punkt końcowy wywołano bez tokenu oraz z uprawnieniami studenta, prowadzącego, administratora i osoby łączącej role studenta i prowadzącego (studentowi o indeksie 279413 tymczasowo nadano etykietę `Teacher` oraz przypisano jedną grupę). Aby wywołania uprawnione nie modyfikowały danych, żądania zapisujące wysyłano z niepoprawną treścią (kod 422) albo z identyfikatorami nieistniejących zasobów (kod 404). W tabeli 7.1 zestawiono uzyskane wyniki.

**Tab. 7.1:** Wyniki testu kontroli dostępu opartej na rolach (RBAC) dla 59 punktów końcowych (291 żądań)

| Moduł | Punkty końcowe | Bez tokenu | Student | Prowadzący | Administrator | Student i prowadzący |
| --- | ---: | :---: | :---: | :---: | :---: | :---: |
| public (logowanie) | 1 | dostęp | – | – | – | – |
| catalogue | 10 | 401 | dostęp | dostęp | dostęp | dostęp |
| student | 10 | 401 | dostęp | 403 | 403 | dostęp |
| teacher | 4 | 401 | 403 | dostęp | dostęp¹ | dostęp |
| admin | 34 | 401 | 403 | 403 | dostęp | 403 |

*¹ Z wyjątkiem listy własnych grup (`GET /me/groups`), dostępnej wyłącznie dla roli prowadzącego.*

W drugiej części testu sprawdzono 16 scenariuszy kontroli dostępu opartej na relacjach (ReBAC, 4.4.2), w których rola użytkownika pozwalała na wywołanie punktu końcowego, a o dostępie decydowała ścieżka w grafie. Dla żądań z poprawną treścią potwierdzono, że:
- prowadzący odczytuje listę studentów własnej grupy i szczegóły nauczanego studenta (200), natomiast próby odczytu cudzej grupy, ocenienia studenta spoza własnej grupy lub wglądu w dane nienauczanego studenta kończą się kodem 403,
- administrator uzyskuje dostęp do dowolnej grupy i dowolnego studenta (200),
- student ma dostęp do własnych zapisów i odbytych semestrów (200), ale otrzymuje kod 403 przy próbie odczytu danych innego studenta, zapisów bez przypisanej tury, cyklu bez uczestnictwa oraz przy wystawianiu opinii o grupie, do której nie należy,
- użytkownik łączący role studenta i prowadzącego korzysta z uprawnień obu ról dla własnych zasobów (200), przy zachowaniu odmowy dostępu do cudzej grupy (403).

Wyniki obu części testu potwierdzają spełnienie wymagań z 3.1: o dostępie rozstrzyga warstwa API, a użytkownik wielorolowy dysponuje sumą uprawnień swoich ról.

Dodatkowo skryptem `tests/test_check_order.py` zweryfikowano kolejność weryfikacji uprawnień i walidacji treści żądania (kroki 3 i 4 w 5.5.8). Wysłano trzy niepoprawne żądania: ocenę 4,2 (`PUT /groups/{group_id}/students/{student_idx}/grade`), wydział bez pełnej nazwy (`POST /admin/faculties`) oraz grupę z dniem tygodnia równym 9 (`POST /admin/groups`). Wywołania bez tokenu, z tokenem studenta oraz z tokenem administratora zwróciły kolejno kody 401, 403 i dopiero 422. Komunikaty walidacyjne pozostają zatem ukryte przed osobami bez uprawnień.

7.2.2 Weryfikacja tokenów JWT i czas odpowiedzi logowania

Odporność weryfikacji tokenów JWT (5.5.6) sprawdzono w 17 przypadkach testowych (`tests/test_jwt.py`), wysyłając żądania do punktu końcowego administratora `GET /admin/people/next-idx`. Tokeny kontrolne zachowały się zgodnie z oczekiwaniami: token administratora zwrócił kod 200, a token studenta kod 403 (`Forbidden`). Wszystkie próby manipulacji odrzucono kodem 401:
- token studenta z dopisaną rolą `Admin` przy pierwotnym podpisie, token z algorytmem `none` bez podpisu, token podpisany innym kluczem oraz token podpisany właściwym kluczem algorytmem HS512 (`Invalid token`),
- token wygasły, pozbawiony roszczeń `exp`, `iat` lub `sub`, uszkodzony albo zawierający nieprawidłową strukturę ról (`Invalid token`),
- token wydany przed uruchomieniem procesu API (`Token revoked`),
- brak nagłówka `Authorization` lub schemat inny niż `Bearer` (`Not authenticated`).

Odrzucenie tokenu podpisanego algorytmem HS512 mimo użycia właściwego klucza API dowodzi, że o akceptowanym algorytmie podpisu rozstrzyga wyłącznie konfiguracja serwera.

Odporność punktu końcowego `POST /api/login` na atak czasowy (5.5.6) zmierzono skryptem `tests/test_login_timing.py`, wykonując po 30 prób dla każdego z trzech przypadków: istniejącego konta z poprawnym hasłem, istniejącego konta z błędnym hasłem oraz nieistniejącego adresu e-mail. W tabeli 7.2 zestawiono mediany czasu odpowiedzi przed wprowadzeniem skrótu zastępczego i po zmianie.

**Tab. 7.2:** Mediana czasu odpowiedzi punktu końcowego `POST /api/login` (30 prób na przypadek)

| Przypadek | Kod | Mediana przed poprawką [ms] | Mediana po poprawce [ms] |
| --- | :---: | ---: | ---: |
| istniejące konto, poprawne hasło | 200 | 185,1 | 182,9 |
| istniejące konto, błędne hasło | 401 | 183,7 | 182,7 |
| nieistniejące konto | 401 | 4,0 | 182,7 |

Przed wprowadzeniem skrótu zastępczego odpowiedź dla nieistniejącego adresu przychodziła po ok. 4 ms wobec 183,7 ms dla błędnego hasła, co umożliwiało wykrycie obecności adresu w bazie. Po poprawce mediany dla wszystkich trzech przypadków są praktycznie równe (ok. 183 ms). W tym samym teście zweryfikowano obsługę haseł przekraczających 72-bajtowy limit biblioteki bcrypt (5.5.6): przed dodaniem walidatora żądanie `POST /api/admin/users` z 73-bajtowym hasłem wywoływało nieobsłużony wyjątek i kod 500, natomiast po poprawce zwraca kod 422 ze wskazaniem pola `passwd`.

7.2.3 Cykl życia konta i unieważnianie tokenów

Działanie operacji administracyjnych na kontach (5.5.9) zweryfikowano skryptem `tests/test_account_lifecycle.py` na przykładzie studenta o indeksie 285904, niemającego konta w danych początkowych. Przeprowadzono pełną sekwencję operacji: utworzenie konta (`POST /admin/users`, kod 201), logowanie i dostęp do `GET /me/enrolments` (200), dezaktywację (`PATCH /admin/users/285904` z `{"active": false}`, kod 200), próbę ponownego logowania (403 `Account inactive`) oraz użycie wcześniej wydanego tokenu (401 `Token revoked`). Następnie konto ponownie aktywowano i potwierdzono możliwość logowania (200), po czym je usunięto (`DELETE /admin/users/285904`, kod 204). Po usunięciu logowanie zwróciło kod 401 (`Invalid email or password`), natomiast dane osobowe studenta pozostały dostępne dla administratora pod `GET /students/285904` (200). Potwierdzono również blokadę usunięcia własnego konta administratora (`DELETE /admin/users/A001`, kod 409 `Cannot remove your own account`).

Osobno zbadano skutki odebrania roli administratora (`tests/test_role_revocation.py`, 5.5.10). Studentowi 279413 nadano rolę `Admin`, pobrano token, a następnie inny administrator odebrał mu tę rolę. W tabeli 7.3 zestawiono zachowanie systemu przed wdrożeniem mechanizmu unieważniania tokenów (5.5.6) oraz po jego wprowadzeniu.

**Tab. 7.3:** Dostęp do punktów końcowych administratora po odebraniu roli `Admin`

| Krok | Bez unieważniania | Z unieważnianiem |
| --- | :---: | :---: |
| `GET /admin/people/next-idx` przed odebraniem roli | 200 | 200 |
| `GET /admin/people/next-idx` po odebraniu roli (stary token) | 200 | 401 `Token revoked` |
| `PATCH /admin/users/281056` z `{"active": false}` (stary token) | 200 | 401 `Token revoked` |
| ponowne logowanie i `GET /admin/people/next-idx` | 403 | 403 |

Bez mechanizmu unieważniania dotychczasowy token zachowywał ważność aż do wygaśnięcia, umożliwiając wywoływanie punktów końcowych administratora i dezaktywację cudzych kont. Po wprowadzeniu unieważniania API natychmiast odrzuca stary token kodem 401, a token uzyskany przy ponownym logowaniu zawiera już wyłącznie rolę `Student`.

7.3 Współbieżność

Skuteczność blokad przy równoległych zapisach do grup oraz modyfikacjach ról i opinii (5.5.10, 6.4.1) sprawdzono skryptami `tests/test_concurrent_registration.py` (Neo4j) oraz `tests/test_concurrent_registration_rel.py` (PostgreSQL). W obu środowiskach utworzono tymczasową rejestrację z aktywną turą oraz grupy testowe, a równoległe żądania wysyłano z wątków synchronizowanych wspólną barierą. Scenariusze kontrolne bez blokad (C w Neo4j oraz C1 i C2 w PostgreSQL) wykonano bezpośrednio przez sterowniki w osobnych połączeniach; w wariancie relacyjnym transakcje utrzymywano otwarte przez 100 ms przed zatwierdzeniem, aby wymusić jednoczesne wykonanie instrukcji. Scenariusz D pominięto w wariancie relacyjnym, ponieważ backend ten nie obsługuje zarządzania rolami. W tabeli 7.4 zestawiono wyniki z trzech niezależnych uruchomień.

**Tab. 7.4:** Wyniki testów współbieżności dla backendu grafowego i relacyjnego (trzy uruchomienia, identyczne wyniki)

| Scenariusz | Żądania | Neo4j (odpowiedzi / stan bazy) | PostgreSQL (odpowiedzi / stan bazy) |
| --- | ---: | --- | --- |
| A: 10 studentów, grupa z 3 miejscami | 10 | 3 × 204, 7 × 409 `Group is full` / 3 zapisanych | 3 × 204, 7 × 409 `Group is full` / 3 zapisanych |
| B: 5 studentów, każdy jednocześnie do 2 grup tego samego typu | 10 | 5 × 204, 5 × 409 (konflikt typu) / każdy w 1 grupie | 5 × 204, 5 × 409 (konflikt typu) / każdy w 1 grupie |
| C / C1 (kontrola): jak A, zapytanie bez blokad | 10 | 10 × `ok` / **10 zapisanych** | 10 × `ok` / **10 zapisanych** |
| C2 (kontrola): jak A, blokada i sprawdzenie w jednej instrukcji SQL | 10 | – | 10 × `ok` / **10 zapisanych** |
| D: jednoczesne odebranie obu ról osobie z rolami `Teacher` i `Student` | 2 | 1 × 200, 1 × 409 `Cannot remove last role` / 1 rola | – |

W scenariuszach docelowych A, B i D oba backendy zachowały wszystkie ograniczenia dziedzinowe. Wyniki scenariuszy kontrolnych C i C1 dowodzą, że przy domyślnym poziomie izolacji *read committed* pojedyncze zapytanie bez jawnych blokad dopuszcza przepełnienie grupy (10 zapisanych na 3 miejsca). Wynik wariantu C2 potwierdza ponadto specyfikę migawek w PostgreSQL (6.4.1): umieszczenie blokady `FOR UPDATE` i sprawdzenia liczby miejsc w tej samej instrukcji SQL również prowadzi do zapisania wszystkich 10 studentów, co uzasadnia rozbicie zapisu na osobne instrukcje w jednej transakcji. Analogiczną ochronę przy współbieżnym wystawianiu opinii sprawdzono w ramach testu z 7.4: spośród 10 jednoczesnych, identycznych żądań jednego studenta utworzono dokładnie jedną opinię (201), a 9 pozostałych odrzucono kodem 409.

7.4 Logika dziedzinowa

Weryfikacja logiki dziedzinowej objęła wyznaczanie średniej ocen, obsługę tur zapisów wraz ze strefą czasową oraz reguły wystawiania opinii.

Poprawność funkcji `average_grade()` (3.2, 5.5.5) sprawdzono 11 testami jednostkowymi w skrypcie `tests/test_average_grade.py`, porównując zwracane wyniki z wartościami obliczonymi ręcznie. Testy objęły pojedynczą formę zajęć (4,0), średnią ważoną form (`0,7 · 5,0 + 0,3 · 4,0 = 4,7`) oraz sprowadzenie oceny z przedmiotu do 2,0 przy ocenie negatywnej z jednej z form (mimo że zwykła średnia ważona wynosiłaby 4,1). Zweryfikowano także ważenie punktami ECTS (`(5 · 4,0 + 2 · 5,0) / 7 = 4,286`), wybór późniejszego podejścia przy poprawie przedmiotu (z uwzględnieniem kolejności semestru letniego po zimowym tego samego roku), pomijanie niepełnych podejść i przedmiotów bez punktów ECTS, brak wyniku przy braku pełnych podejść, obsługę dwóch grup tej samej formy w jednym podejściu oraz normalizację wag niesumujących się do 1. Na koniec przeprowadzono test integracyjny przez API: po wystawieniu studentowi brakującej oceny 3,0 w przedmiocie z ocenionymi pozostałymi formami punkt końcowy `GET /students/{student_idx}` zwrócił średnią 3,75, zgodną z wynikiem funkcji jednostkowej.

Obsługę tur zapisów i strefy czasowej (3.2, 4.3.4, 5.5.10) zweryfikowano skryptem `tests/test_registration_turn.py`, tworząc przez API tury wczorajszą, trwającą obecnie i jutrzejszą oraz osobną rejestrację z inną grupą. W trakcie aktywnej tury potwierdzono zapis (204), idempotentność ponownego zapisu do tej samej grupy (204, 4.5.2), wypis (204), kod 404 przy wypisie z grupy bez zapisu oraz kod 403 przy próbie zapisu do grupy z cudzej rejestracji. Po zakończeniu tury zarówno zapis, jak i wypis (dla studenta zapisanego wcześniej dziekańsko) zwróciły kod 403; ten sam kod otrzymano dla tury przyszłej. Zweryfikowano także zapisywanie godzin tur jako `LOCAL TIME` mimo podania przez klienta przesunięcia `+01:00` oraz wyrażenie łączące datę i godzinę w strefie `Europe/Warsaw` w kwerendach `_REGISTER` i `_DEREGISTER`. W tabeli 7.5 zestawiono moment rozpoczęcia tury o 8:00 w różnych dniach roku względem dawnej implementacji ze stałym przesunięciem.

**Tab. 7.5:** Początek tury zapisów wyznaczonej na godzinę 8:00 w strefie `Europe/Warsaw`

| Data | Czas lokalny ze strefą (obecnie) | Stałe przesunięcie `+01:00` (dawniej) |
| --- | :---: | :---: |
| 2026-01-15 | 08:00+01:00 | 08:00 |
| 2026-03-28 | 08:00+01:00 | 08:00 |
| 2026-03-29 (zmiana na czas letni) | 08:00+02:00 | **09:00** |
| 2026-07-01 | 08:00+02:00 | **09:00** |
| 2026-10-24 | 08:00+02:00 | **09:00** |
| 2026-10-25 (zmiana na czas zimowy) | 08:00+01:00 | 08:00 |

W obecnej wersji tura rozpoczyna się o 8:00 czasu polskiego niezależnie od zmiany czasu, co eliminuje godzinne opóźnienie występujące wcześniej w okresie czasu letniego (5.5.10).

Reguły wystawiania i odczytu opinii (3.4, 3.5, 4.3.5) sprawdzono skryptem `tests/test_opinions.py` na tymczasowej grupie z dwoma prowadzącymi i trzema studentami. Potwierdzono odrzucenie ocen spoza skali (7,0 i 4,2) oraz komentarzy dłuższych niż 1000 znaków (kod 422), a także odmowę dostępu dla studenta niezapisanego do grupy i dla prowadzącego nieprzypisanego do tej grupy (403 `Teacher does not teach this group`). Poprawna opinia zwróciła kod 201, powtórzenie dla tej samej pary grupa–prowadzący kod 409 (`Opinion already exists`), a wpisy dotyczące drugiego prowadzącego lub wystawione przez innego studenta przyjęto kodem 201. Przetestowano również 10 jednoczesnych, identycznych żądań jednego studenta (1 × 201, 9 × 409). Odczyt opinii przez prowadzącego (`GET /opinions?group_id=...`) zwrócił wszystkie cztery wpisy bez identyfikatorów autorów i z samą datą wystawienia, potwierdzając pseudonimizację.

7.5 Integralność danych i uprawnienia kont bazodanowych

7.5.1 Ograniczenia schematu

Skryptem `tests/test_schema_constraints.py` sprawdzono egzekwowanie ograniczeń schematu bezpośrednio na poziomie bazy Neo4j, z pominięciem warstwy API i przy użyciu konta aplikacji. Każda z 14 prób zapisu niepoprawnych danych wykonywała się w osobnej, zatwierdzanej transakcji, ponieważ część ograniczeń (w tym istnienie właściwości) Neo4j weryfikuje przy zatwierdzaniu. Wszystkie 14 prób odrzucono na poziomie bazy, a odpowiadające im kody błędów GQL (ang. *Graph Query Language*) z podziałem na rodzaje ograniczeń z 4.3.7 zestawiono w tabeli 7.6.

**Tab. 7.6:** Niepoprawne operacje zapisu odrzucone bezpośrednio przez bazę Neo4j (14 przypadków)

| Kod GQL | Rodzaj ograniczenia | Przetestowane naruszenia |
| :---: | --- | --- |
| 22N78 | typ właściwości | dzień tygodnia, godzina zajęć lub ocena na krawędzi `REGISTERED_IN` zapisane jako tekst |
| 22N77 | istnienie właściwości | grupa bez limitu miejsc, konto `Inactive` bez momentu dezaktywacji, krawędź `REGISTERED_IN` bez `registered_at` |
| 22N79 | unikalność i klucze | duplikat identyfikatora grupy, adresu e-mail, pary (budynek, numer sali), pary (rok, semestr) oraz trójki (imię, nazwisko, telefon) |
| 22NB3 | etykieta implikowana | węzeł `Student` bez etykiety i wymaganych właściwości `Person` |
| 22NB4 | typy węzłów na końcach krawędzi | krawędź `TEACHES` wychodząca od studenta, krawędź `IN_ROOM` prowadząca do przedmiotu |

W drugiej części skryptu potwierdzono granice możliwości `GRAPH TYPE` omówione w 4.3.7 i 5.3.1. Baza przyjęła 10 celowo niepoprawnych zapisów dotyczących reguł egzekwowanych dopiero przez walidację Pydantic lub logikę API. Obejmowały one wartości spoza dozwolonego zakresu (dzień tygodnia, parzystość tygodni, skala ocen), naruszenia kardynalności powiązań (grupa bez formy zajęć lub w dwóch salach, powtórzony numer grupy w formie zajęć, druga instancja przedmiotu w tym samym cyklu, student w dwóch turach jednej rejestracji), niesumujące się wagi form zajęć oraz etykietę `Inactive` bez etykiety `User`. Odpowiadające im ograniczenia w modelu relacyjnym zestawiono wcześniej w tabeli z 6.2.3.

7.5.2 Uprawnienia kont bazodanowych

Zgodność konfiguracji kont bazodanowych API z zasadą najmniejszych uprawnień (3.3, 4.4.3, 6.3) zweryfikowano skryptem `tests/test_db_privileges.py`. Wszystkie próby wykonywano w wycofywanych transakcjach, uznając odmowę wyłącznie wtedy, gdy komunikat bazy jednoznacznie wskazywał brak uprawnień. Zestawienie wyników dla obu baz przedstawiono w tabeli 7.7.

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

W trakcie testu ochrony przed atakiem SSRF (ang. *Server-Side Request Forgery*) zauważono szczegół implementacyjny Neo4j: dla polecenia `LOAD CSV` z adresem w nieistniejącej domenie baza zgłasza błąd sieci przed sprawdzeniem uprawnienia `LOAD`. Dla każdego adresu dającego się rozwiązać – w tym usług w sieci Dockera – uprawnienie jest blokowane przed wysłaniem żądania HTTP, jednak samo zapytanie DNS (ang. *Domain Name System*) może się wykonać.

7.6 Szyfrowanie połączeń

Poprawność konfiguracji TLS (5.1.1, 6.3) zweryfikowano w dwóch etapach: testem konfiguracji portów (`tests/test_tls_config.py`) oraz analizą przechwyconego ruchu sieciowego (`tests/test_tls_capture.py`).

W pierwszym etapie dla każdego portu opublikowanego na hoście sprawdzono nawiązanie połączenia TLS z weryfikacją certyfikatu i nazwy hosta, reakcję na obcą nazwę hosta oraz odpowiedź na nieszyfrowane żądanie. Dla protokołów Bolt i PostgreSQL początkowe komunikaty protokołu (uzgodnienie wersji Bolt oraz pakiety `SSLRequest` i `StartupMessage`) wysłano bezpośrednio przez gniazda TCP, aby uniknąć odrzucenia połączenia po stronie sterownika. Wyniki zestawiono w tabeli 7.8.

**Tab. 7.8:** Wyniki weryfikacji konfiguracji TLS dla portów opublikowanych na hoście

| Port | Usługa | Wersja TLS | Obca nazwa hosta | Żądanie bez TLS |
| ---: | --- | :---: | :---: | --- |
| 5173 | nginx | TLS 1.3 | odrzucona | `400 Bad Request` |
| 8000 | API | TLS 1.3 | odrzucona | połączenie zamknięte bez odpowiedzi |
| 7473 | konsola Neo4j | TLS 1.3 | odrzucona | odpowiedź wyłącznie w protokole TLS |
| 7687 | Neo4j (Bolt) | TLS 1.3 | odrzucona | połączenie zamknięte bez odpowiedzi |
| 5432 | PostgreSQL | TLS 1.3 | odrzucona | `pg_hba.conf rejects connection … no encryption` |

Wszystkie porty opublikowano wyłącznie na interfejsie `127.0.0.1` (5.1.6). Wewnątrz sieci Dockera (z kontenera `app`) potwierdzono ponadto odrzucenie połączeń z bazami pod adresem IP zamiast nazwy z certyfikatu (`SSLCertVerificationError` w Neo4j oraz niezgodność nazwy hosta w PostgreSQL) i odrzucenie połączeń jawnych (`bolt://`, `sslmode=disable`). Ponieważ wymaganie z 3.3 dotyczy samego szyfrowania ruchu, połączenia TLS 1.2 raportowano informacyjnie: wersję 1.3 jako minimalną wymuszają PostgreSQL (6.3) oraz połączenie nginx z API (5.1.6), natomiast nginx od strony przeglądarki, API i Neo4j akceptują również TLS 1.2.

Aby potwierdzić brak jawnych danych w przesyłanym ruchu, nagrano pakiety na wszystkich czterech połączeniach systemu (4.1) programem `tcpdump` uruchomionym w pomocniczym kontenerze dołączonym do przestrzeni sieciowej kontenerów `frontend` i `app` (`--net container:…`), bez modyfikowania kontenerów aplikacji. Podczas rejestracji ruchu wysłano przez nginx żądanie logowania oraz dwa zapytania o przedmioty z losowym znacznikiem w parametrze `name` (do backendu grafowego i relacyjnego). Dodatkowo otwarto z kontenera `app` nowe połączenia z obiema bazami w celu zarejestrowania uzgadniania TLS. Nagrania przeanalizowano narzędziem `tshark` [CYTOWANIE: https://www.wireshark.org/docs/man-pages/tshark.html], przeszukując surowe segmenty TCP pod kątem hasła, adresu e-mail, znacznika, prefiksu tokenu JWT oraz fragmentów `MATCH (` i `SELECT `. Wyniki zestawiono w tabeli 7.9.

**Tab. 7.9:** Wyniki analizy przechwyconego ruchu sieciowego na połączeniach systemu

| Połączenie | Wersja TLS | Rekordy TLS z danymi | Jawnie widoczne wartości |
| --- | :---: | ---: | --- |
| przeglądarka → nginx | TLS 1.3 | 22 | brak |
| nginx → API | TLS 1.3 | 23 | brak |
| API → Neo4j | TLS 1.3 | 24 | brak |
| API → PostgreSQL | TLS 1.3 | 25 | brak |

W ramach próby kontrolnej klient testowy zapisał klucze sesji TLS za pomocą mechanizmu `SSLKEYLOGFILE` [CYTOWANIE: https://docs.python.org/3/library/ssl.html#ssl.SSLContext.keylog_filename]. Po odszyfrowaniu nimi nagrania połączenia przeglądarki z serwerem nginx program `tshark` odczytał wszystkie trzy żądania wraz z hasłem, adresem e-mail i znacznikiem, co potwierdza obecność danych w przechwyconym ruchu oraz skuteczność ich szyfrowania (rys. 7.1).

*[Zrzut ekranu: to samo nagranie w programie Wireshark bez kluczy sesji i z kluczami sesji]*

**Rys. 7.1:** Przechwycone połączenie w programie Wireshark bez kluczy sesji oraz po odszyfrowaniu

7.7 Uruchomienie środowiska od zera

Wymaganie przenośności (3.3) oraz poprawność instrukcji wdrożeniowej zweryfikowano skryptem `tests/test_fresh_start.py` na świeżym klonie repozytorium, uruchamianym jako osobny projekt Docker Compose z pustymi wolumenami (główne środowisko zatrzymywano na czas testu). Po skopiowaniu pliku `.env`, wygenerowaniu certyfikatów skryptem `certs.sh` i uruchomieniu polecenia `docker compose up --build` aplikacja umożliwiła logowanie przez serwer nginx po 50 s. W bazach znalazły się pełne dane początkowe: 563 węzły i 1 448 krawędzi w Neo4j oraz 32 tabele z 1 635 wierszami w PostgreSQL.

Następnie zweryfikowano powtarzalność inicjalizacji i reakcję na zmianę haseł w pliku `.env`. Po restarcie kontenerów (`down`, `up`) i ponownym uruchomieniu importu liczby węzłów, krawędzi i wierszy pozostały niezmienione, co potwierdza idempotentność instrukcji `MERGE` (5.3.2). Zmiana zmiennej `NEO4J_APP_PASSWORD` i ponowny start przebiegły poprawnie dzięki wykonywaniu `CREATE OR REPLACE USER` przy każdym uruchomieniu (5.1.4). Z kolei zmiana `PG_APP_PASSWORD` bez usunięcia wolumenu `pg_data` uniemożliwiła uruchomienie API (`password authentication failed`). Wynika to z jednorazowego uruchamiania skryptów inicjalizacyjnych w obrazie PostgreSQL (6.3) oraz ze współdzielenia jednego procesu przez oba backendy (5.5.2).

7.8 Porównanie z modelem relacyjnym

7.8.1 Zgodność backendów i metodyka pomiarów

Zgodność semantyczną obu implementacji zweryfikowano skryptem `bench/compare.py`, kierując identyczne żądania z tym samym tokenem JWT pod prefiksy `/api` oraz `/api/rel`. We wszystkich 13 przypadkach – obejmujących także błędy 401, 403 i 422 – uzyskano identyczne kody statusu i treść JSON. Przed porównaniem sprowadzano znaczniki czasu do strefy UTC, ponieważ Neo4j zachowuje oryginalne przesunięcie strefy (np. `2025-10-01T00:00:00+02:00`), podczas gdy PostgreSQL zwraca typ `timestamptz` w strefie sesji (`2025-09-30T22:00:00Z`) [CYTOWANIE: https://www.postgresql.org/docs/current/datatype-datetime.html].

Pomiary wydajności objęły siedem z ośmiu punktów końcowych zaimplementowanych w obu backendach (6.4):
- `POST /login` (1 zapytanie: odczyt konta oraz weryfikacja hasła w bcrypt),
- `GET /subjects` (2 zapytania: agregacja katalogu po całym zbiorze danych),
- `GET /opinions?teacher_idx=…` (1 zapytanie: odczyt opinii o prowadzącym),
- `GET /me/registrations/{id}/groups` (2 zapytania: sprawdzenie ReBAC i lista otwartych grup),
- `GET /groups/{id}/students` (2 zapytania: sprawdzenie ReBAC i lista studentów grupy),
- `GET /students/{idx}` (3 zapytania: sprawdzenie ReBAC, dane studenta i oceny do średniej),
- `PUT /groups/{id}/students/{idx}/grade` (2 zapytania: sprawdzenie ReBAC i zapis bieżącej oceny bez zmiany stanu danych).

Zapis na grupę pominięto ze względu na wymóg trwającej tury i zweryfikowano osobno w 7.3.

Aby oddzielić czas pracy bazy od narzutu kolejnych elementów stosu, każde żądanie zmierzono w pięciu warstwach:
1. **silnik** – wykonanie zapytań w bazie: suma czasów operatorów z `PROFILE` (Neo4j) oraz `Execution Time` z `EXPLAIN (ANALYZE, TIMING OFF)` (PostgreSQL),
2. **sterownik** – wysłanie tych samych zapytań sterownikiem z pobraniem wszystkich wierszy (w kontenerze `app`),
3. **FastAPI** – wywołanie aplikacji wewnątrz procesu bez sieci i TLS, z uwierzytelnianiem, walidacją i serializacją,
4. **HTTPS do API** – żądanie z hosta bezpośrednio do portu 8000,
5. **HTTPS przez nginx** – żądanie z hosta przez port 5173, analogicznie do ruchu z przeglądarki.

Skrypt `bench/measure.py` rejestrował dokładną treść i parametry zapytań podczas pojedynczego wywołania API (przez przechwycenie funkcji `run()`), a następnie powtarzał je w warstwach silnika i sterownika zgodnie ze sposobem pracy obu backendów: w Neo4j każde zapytanie w osobnej transakcji automatycznej (5.5.3), a w PostgreSQL wszystkie zapytania punktu końcowego w jednej transakcji (6.4). Każdy punkt końcowy mierzono 50 razy po 10 przebiegach rozgrzewkowych (dla `POST /login` wykonano 10 pomiarów ze względu na koszt funkcji bcrypt). W dalszej części przedstawiono mediany; pełne dane wraz z 95. percentylami zapisano w katalogu `bench/results/`.

W PostgreSQL wyłączono pomiar czasu dla pojedynczych operatorów (`TIMING OFF`), gdyż pełna instrumentacja zawyżała wynik katalogu przedmiotów o ok. 10%. W Neo4j jedynym źródłem czasu wykonania z rozdzielczością poniżej milisekundy jest `PROFILE`, przez co wyniki warstwy silnika Neo4j obejmują narzut profilowania; bardziej miarodajnym poziomem porównania są zatem warstwy od sterownika w górę. Oprócz czasu zbierano metryki diagnostyczne z `PROFILE` [CYTOWANIE: https://neo4j.com/docs/cypher-manual/current/planning-and-tuning/] oraz `EXPLAIN (ANALYZE, BUFFERS, MEMORY, SERIALIZE)` [CYTOWANIE: https://www.postgresql.org/docs/current/sql-explain.html]: pracę bazy (*db hits* w Neo4j oraz odczytane 8-kilobajtowe bloki bufora w PostgreSQL), trafienia pamięci podręcznej (*page cache* i *shared buffers*), zużycie pamięci, czas planowania, dokładność oszacowań liczności oraz zestaw użytych operatorów.

Ponieważ dane początkowe (29 studentów) są zbyt małe do badania skalowalności, skryptem `bench/generate.py` wygenerowano deterministycznie spójne zbiory danych w formatach obu baz dla 1 000, 3 000 i 10 000 studentów (tab. 7.10). Każdą skalę mierzono na świeżym środowisku Docker Compose z domyślnymi ustawieniami wydajnościowymi baz i bez limitów zasobów. Parametry zapytań punktowych dobierano tak, by zwracały zbliżoną liczbę wierszy (np. grupa ok. 16 studentów), dzięki czemu obserwowane zmiany odzwierciedlają wpływ rozmiaru bazy. Wyjątek stanowią katalog przedmiotów (168 wierszy dla 1 000 i 3 000 studentów, 336 dla 10 000) oraz lista opinii (odpowiednio 9 i 14 wierszy). We wszystkich pomiarach liczba chybień pamięci podręcznej wyniosła zero, więc cały zbiór mieścił się w pamięci RAM.

**Tab. 7.10:** Rozmiar wygenerowanych zbiorów danych w kolejnych skalach pomiarowych

| Studentów | Wydziałów | Grup | Zapisów na grupy | Węzłów | Krawędzi |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 29 (dane początkowe) | 2 | 129 | 215 | 563 | 1 448 |
| 1 000 | 2 | 1 248 | 28 000 | 4 265 | 40 846 |
| 3 000 | 2 | 2 688 | 84 000 | 8 607 | 114 052 |
| 10 000 | 4 | 9 216 | 280 000 | 27 065 | 378 121 |

7.8.2 Czas wykonania w warstwach i wpływ skali danych

W tabeli 7.11 zestawiono mediany czasu wykonania w pięciu warstwach dla największej skali (10 000 studentów), a na rysunku 7.2 przedstawiono udział poszczególnych warstw w całkowitym czasie żądania kierowanego przez serwer nginx.

**Tab. 7.11:** Mediana czasu wykonania żądania w kolejnych warstwach dla skali 10 000 studentów [ms]

| Punkt końcowy | Baza | Silnik | Sterownik | FastAPI | HTTPS do API | HTTPS przez nginx |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `POST /login` | Neo4j | 0,10 | 2,06 | 182,80 | 180,72 | 181,05 |
|  | PostgreSQL | 0,03 | 0,25 | 178,44 | 179,50 | 180,15 |
| `GET /subjects` | Neo4j | 184,04 | 219,00 | 225,80 | 225,43 | 224,95 |
|  | PostgreSQL | 103,55 | 86,05 | 89,63 | 92,47 | 92,59 |
| `GET /opinions` | Neo4j | 0,32 | 2,60 | 3,06 | 3,16 | 3,39 |
|  | PostgreSQL | 0,26 | 0,65 | 1,18 | 1,39 | 2,34 |
| `GET /me/registrations/{id}/groups` | Neo4j | 0,41 | 3,59 | 4,36 | 4,25 | 5,56 |
|  | PostgreSQL | 0,28 | 1,58 | 2,03 | 2,43 | 3,55 |
| `GET /groups/{id}/students` | Neo4j | 0,19 | 3,76 | 4,05 | 3,79 | 4,67 |
|  | PostgreSQL | 0,56 | 1,46 | 2,00 | 2,38 | 3,21 |
| `GET /students/{idx}` | Neo4j | 1,44 | 6,25 | 6,71 | 7,28 | 7,61 |
|  | PostgreSQL | 1,12 | 1,83 | 2,42 | 2,82 | 3,69 |
| `PUT /groups/{id}/students/{idx}/grade` | Neo4j | 0,14 | 2,44 | 2,92 | 2,85 | 3,89 |
|  | PostgreSQL | 0,05 | 0,80 | 1,14 | 1,31 | 1,96 |

![[narzut_10000.png]]

**Rys. 7.2:** Udział kolejnych warstw w czasie żądania przez serwer nginx dla skali 10 000 studentów

Z wyjątkiem katalogu przedmiotów samo wykonanie zapytań w silniku odpowiada za niewielką część całkowitego czasu żądania: w Neo4j od 4 do 19%, a w PostgreSQL od 3 do 30%. Największą różnicę między backendami wprowadza warstwa sterownika i protokołu komunikacyjnego. W Neo4j przejście od silnika do sterownika dodaje 1,2–2,3 ms na każde zapytanie (łącznie 2,3–4,8 ms dla punktów końcowych wykonujących 1–3 zapytania), natomiast w PostgreSQL jest to 0,2–0,7 ms. Wynika to z otwierania osobnej transakcji automatycznej dla każdego zapytania w protokole Bolt oraz konwersji typów funkcją `native()` (5.5.5). W PostgreSQL wszystkie zapytania żądania współdzielą jedną transakcję, a sterownik `psycopg` po kilku wykonaniach automatycznie przygotowuje zapytanie po stronie serwera, eliminując narzut ponownego planowania [CYTOWANIE: https://www.psycopg.org/psycopg3/docs/advanced/prepare.html].

Warstwa FastAPI (uwierzytelnianie, autoryzacja, walidacja i serializacja) wnosi w obu wariantach 0,3–0,8 ms, z wyjątkiem logowania, w którym ponad 98% czasu (ok. 178 ms) pochłania funkcja bcrypt. Komunikacja HTTPS z serwerem uvicorn dodaje do 0,6 ms, a pośrednictwo serwera nginx z drugim połączeniem TLS kolejne 0,2–1,3 ms (sporadycznie niższe mediany dla HTTPS niż dla pomiaru FastAPI w osobnym procesie mieszczą się w szumie pomiarowym rzędu 0,3 ms). W rezultacie żądania punktowe w wariancie grafowym trwają 1,5–2,1 raza dłużej niż w relacyjnym mimo zbliżonych czasów silników – dla listy studentów grupy silnik Neo4j okazał się nawet trzykrotnie szybszy od PostgreSQL (0,19 wobec 0,56 ms), jednak całe żądanie trwało o połowę dłużej.

Jedynym punktem końcowym zdominowanym przez silnik bazy jest katalog przedmiotów (`GET /subjects`), agregujący dane wszystkich przedmiotów i cykli (5.4.3). W tym przypadku PostgreSQL był 2,4 raza szybszy. Mediana dla warstwy silnika PostgreSQL (103,55 ms) przewyższa wynik warstwy sterownika (86,05 ms), ponieważ `EXPLAIN ANALYZE` planuje zapytanie przy każdym wywołaniu, podczas gdy sterownik wykorzystuje zapytanie przygotowane.

Wpływ wzrostu rozmiaru danych na czas żądania przez serwer nginx zestawiono w tabeli 7.12 oraz przedstawiono w skali logarytmicznej na rysunku 7.3. Na rysunku 7.4 porównano względny przyrost pracy obu baz względem skali 1 000 studentów.

**Tab. 7.12:** Mediana czasu żądania przez serwer nginx w zależności od liczby studentów [ms]

| Punkt końcowy | Baza | 29 | 1 000 | 3 000 | 10 000 |
| --- | --- | ---: | ---: | ---: | ---: |
| `GET /subjects` | Neo4j | 11,00 | 45,04 | 59,40 | 224,95 |
|  | PostgreSQL | 7,83 | 23,84 | 31,16 | 92,59 |
| `GET /opinions` | Neo4j | 3,12 | 2,92 | 3,32 | 3,39 |
|  | PostgreSQL | 1,86 | 1,86 | 2,05 | 2,34 |
| `GET /me/registrations/{id}/groups` | Neo4j | 3,65 | 3,81 | 4,57 | 5,56 |
|  | PostgreSQL | 2,09 | 2,02 | 3,33 | 3,55 |
| `GET /groups/{id}/students` | Neo4j | 3,05 | 4,46 | 4,48 | 4,67 |
|  | PostgreSQL | 1,86 | 2,03 | 2,90 | 3,21 |
| `GET /students/{idx}` | Neo4j | 4,42 | 7,51 | 7,54 | 7,61 |
|  | PostgreSQL | 2,08 | 2,95 | 3,04 | 3,69 |
| `PUT /groups/{id}/students/{idx}/grade` | Neo4j | 5,33 | 3,85 | 3,62 | 3,89 |
|  | PostgreSQL | 2,51 | 1,98 | 2,36 | 1,96 |

![[skala_czas.png]]

**Rys. 7.3:** Mediana czasu żądania przez serwer nginx (linia ciągła) i czasu silnika (linia przerywana) w zależności od liczby studentów

![[skala_praca.png]]

**Rys. 7.4:** Względna praca bazy odniesiona do skali 1 000 studentów: *db hits* (Neo4j) oraz odczytane bloki bufora (PostgreSQL)

Dziesięciokrotny wzrost liczby studentów (z 1 000 do 10 000) wydłużył czas zapytań punktowych najwyżej o ok. 75%, a dla zapisu oceny pozostał bez wpływu. Obie bazy odnajdują punkt startowy przez indeks (klucz węzła w Neo4j, klucz główny lub indeks na kluczu obcym w PostgreSQL) i przetwarzają jedynie lokalny podzbiór danych. W zapytaniach punktowych liczba odwołań *db hits* w Neo4j jest niemal stała (np. 185 i 210 dla listy studentów grupy; 78 i 87 dla zapisu oceny), ponieważ przejście po krawędziach nie zależy od całkowitej liczby węzłów w grafie. W PostgreSQL liczba odczytanych bloków rośnie ok. dwukrotnie wraz ze wzrostem głębokości indeksów B-drzewa, jednak przy małych wartościach nie wpływa to zauważalnie na czas odpowiedzi. Planista PostgreSQL dostosowuje przy tym plany wykonania do rozmiaru tabel: liczba przeglądów sekwencyjnych (`Seq Scan`) w zapytaniach punktowych spadła z 11 przy 1 000 studentów do 5 przy 10 000, ustępując operatorom `Index Only Scan` (wzrost z 7 do 14).

Odmiennie zachowuje się katalog przedmiotów (`GET /subjects`), dla którego czas silnika wzrósł siedmiokrotnie w Neo4j (z 26,3 do 184,0 ms) i sześciokrotnie w PostgreSQL (z 17,0 do 103,6 ms), częściowo przez podwojenie liczby przedmiotów w skali 10 000 studentów. Liczba odwołań *db hits* w Neo4j wzrosła jedenastokrotnie (z 70,8 tys. do 822,4 tys.), ponieważ każda komórka siatki uruchamia osobne podzapytanie `EXISTS` lub `COUNT` trawersujące krawędzie od przedmiotu do grup i zapisów (5.4.3). W PostgreSQL liczba odczytanych bloków wzrosła w tym czasie jedynie trzykrotnie (z 17 tys. do 53 tys.) dzięki złączeniom haszującym (`Hash Join`) po całych tabelach.

7.8.3 Diagnostyka zapytań

Zebrane metryki planów wykonania dla skali 10 000 studentów zestawiono w tabeli 7.13. Wartości pracy bazy wyrażono w odmiennych jednostkach (odwołania *db hits* w Neo4j, 8-kilobajtowe bloki bufora w PostgreSQL), dlatego należy je interpretować wyłącznie w obrębie jednego silnika.

**Tab. 7.13:** Wyniki diagnostyki zapytań dla skali 10 000 studentów (sumy po zapytaniach punktu końcowego)

| Punkt końcowy | Baza | Wzorce krawędzi / złączenia | Praca | Pamięć [kB] | Maks. błąd oszacowania |
| --- | --- | ---: | ---: | ---: | ---: |
| `POST /login` | Neo4j | 0 | 4 | 0 | 1 |
|  | PostgreSQL | 4 | 9 | 139 | 1 |
| `GET /subjects` | Neo4j | 16 | 822 410 | 168 | 3,3 |
|  | PostgreSQL | 10 | 53 363 | 1 025 | 4 |
| `GET /opinions` | Neo4j | 6 | 382 | 5 | 14 |
|  | PostgreSQL | 6 | 176 | 458 | 1 |
| `GET /me/registrations/{id}/groups` | Neo4j | 10 | 461 | 8 | 18 |
|  | PostgreSQL | 6 | 353 | 644 | 18 |
| `GET /groups/{id}/students` | Neo4j | 2 | 210 | 5 | 10 |
|  | PostgreSQL | 4 | 210 | 274 | 1,9 |
| `GET /students/{idx}` | Neo4j | 11 | 2 742 | 45 | 49 |
|  | PostgreSQL | 11 | 1 843 | 757 | 49 |
| `PUT /groups/{id}/students/{idx}/grade` | Neo4j | 2 | 87 | 1 | 10 |
|  | PostgreSQL | 0 | 14 | 42 | 1 |

Złożoność zapytań mierzona liczbą wzorców krawędzi w Cypher oraz złączeń w SQL jest zbliżona. Wyraźną różnicę widać w logowaniu, gdzie w Neo4j role stanowią etykiety jednego węzła (5.4.2), podczas gdy w PostgreSQL wymagają czterech złączeń `LEFT JOIN` (6.2.2). W zapisie oceny przewaga jest odwrotna: krawędź `REGISTERED_IN` w modelu relacyjnym stanowi tabelę z kluczem `(student_idx, group_id)`, dzięki czemu zapytanie obywa się bez złączeń. W katalogu przedmiotów Cypher zawiera 16 wzorców krawędzi, a SQL 10 złączeń i 6 podzapytań.

Zużycie pamięci w obu bazach mieści się w pojedynczych megabajtach (Neo4j raportuje pamięć wykonania `GlobalMemory`, natomiast PostgreSQL wlicza także pamięć planowania, która stanowi większość wykazanych wartości). Samo planowanie w PostgreSQL trwa 0,07–1,3 ms na punkt końcowy, czyli porównywalnie z wykonaniem zapytań punktowych, jednak mechanizm przygotowanych zapytań sterownika (7.8.2) pozwala pominąć ten koszt. Największy błąd oszacowania liczności (49-krotny w obu bazach) wystąpił w wieloetapowym zapytaniu o oceny studenta; statystyki planisty Neo4j bazują wyłącznie na liczebności etykiet i typów krawędzi, bez histogramów wartości właściwości [CYTOWANIE: https://neo4j.com/docs/cypher-manual/current/planning-and-tuning/execution-plans/].

Analiza planów ujawniła ponadto problem wydajnościowy w pierwotnej wersji zapytania `GET /opinions` w Neo4j (5.5.9). Warunek `$teacher_idx IS NULL OR t.idx = $teacher_idx` uniemożliwiał użycie indeksu w pojedynczym przechowywanym planie, wymuszając pełny przegląd węzłów `Opinion` (`NodeByLabelScan`). Skutkowało to 4,5-krotnym wzrostem pracy między skalami 1 000 i 10 000 oraz 692-krotnym błędem oszacowania liczności. Po rozdzieleniu zapytania na warianty rozpoczynane od węzła `Teacher` albo `Group` planista zastosował operator `NodeUniqueIndexSeek`. W skali 10 000 studentów praca spadła z 2 227 do 382 odwołań, błąd oszacowania z 692 do 14, czas silnika z 1,03 do 0,32 ms, a czas żądania przez nginx z 4,61 do 3,39 ms; praca rośnie teraz wyłącznie proporcjonalnie do liczby opinii o danym prowadzącym (247 przy 9 opiniach wobec 382 przy 14). W PostgreSQL analogiczny warunek nie powodował tego problemu, ponieważ planista optymalizuje zapytanie z uwzględnieniem konkretnych wartości parametrów i od początku korzystał z indeksu `opinion (teacher_idx)` [CYTOWANIE: https://www.postgresql.org/docs/current/sql-prepare.html].

7.8.4 Import, rozmiar baz oraz rozszerzenie sterownika Neo4j

W tabeli 7.14 zestawiono czasy pierwszego importu danych oraz rozmiar obu baz na dysku dla czterech skal, a na rysunku 7.5 przedstawiono zależność czasu importu od liczby studentów. Rozmiar bazy Neo4j zmierzono po wymuszeniu punktu kontrolnego (`CALL db.checkpoint()`), z pominięciem wstępnie przydzielonego dziennika transakcji (256 MB).

**Tab. 7.14:** Czas importu danych przy pierwszym uruchomieniu oraz rozmiar baz na dysku

| Studentów | Import Neo4j [s] | Import PostgreSQL [s] | Rozmiar Neo4j [MB] | Rozmiar PostgreSQL [MB] | w tym indeksy PostgreSQL [MB] |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 29 | 6,2 | 0,3 | 2,2 | 10,4 | 1,0 |
| 1 000 | 14,8 | 1,4 | 5,0 | 22,8 | 7,2 |
| 3 000 | 78,3 | 2,5 | 11,3 | 45,3 | 19,1 |
| 10 000 | 851,9 | 7,7 | 34,3 | 125,2 | 62,0 |

![[import.png]]

**Rys. 7.5:** Czas importu danych do obu baz w zależności od liczby studentów

Czas importu poleceniem `COPY` w PostgreSQL (6.3) rośnie liniowo względem liczby rekordów i przy 10 000 studentów wynosi 7,7 s. W Neo4j import wydłużył się do 851,9 s (ponad 14 minut), co wynika z przyjętej strategii wczytywania wszystkich plików instrukcjami `LOAD CSV` i `MERGE` w jednej transakcji (5.1.4): całość stanu pozostaje w pamięci, a każde `MERGE` poprzedza wyszukanie istniejącego elementu. Dla dużych zbiorów dokumentacja Neo4j zaleca podział na partie (`CALL { … } IN TRANSACTIONS`) albo import offline narzędziem `neo4j-admin database import` [CYTOWANIE: https://neo4j.com/docs/operations-manual/current/tools/neo4j-admin/neo4j-admin-import/], co jednak wyklucza atomowe powtarzanie importu przy każdym starcie kontenera. Pod względem zajętości dysku baza grafowa okazała się 3,6 raza mniejsza od relacyjnej (34,3 wobec 125,2 MB). Rozmiar PostgreSQL obejmuje ok. 7,5 MB katalogów systemowych, a połowę całości (62,0 MB) stanowią indeksy, głównie na tabelach łączących zastępujących krawędzie grafu.

Ze względu na istotny udział warstwy sterownika w czasie żądań Neo4j (7.8.2) sprawdzono dodatkowo oficjalne rozszerzenie `neo4j-rust-ext` w wersji 6.2.0.0 [CYTOWANIE: https://pypi.org/project/neo4j-rust-ext/], przenoszące kodowanie i dekodowanie formatu PackStream protokołu Bolt do kodu w języku Rust bez zmian w kodzie API. Skryptem `bench/rust_ext.py` zmierzono kolejno obrazy API bez rozszerzenia i z rozszerzeniem dla skal 1 000 oraz 10 000 studentów (tab. 7.15).

**Tab. 7.15:** Mediana czasu wykonania w Neo4j bez rozszerzenia `neo4j-rust-ext` i z nim [ms]

| Punkt końcowy | 1 000 studentów: sterownik | 1 000: FastAPI | 10 000 studentów: sterownik | 10 000: FastAPI |
| --- | ---: | ---: | ---: | ---: |
| `POST /login` | 2,15 → 0,78 | 181,50 → 181,03 | 1,87 → 1,62 | 181,78 → 183,38 |
| `GET /subjects` | 42,59 → 36,32 | 49,69 → 38,46 | 211,90 → 206,46 | 217,50 → 207,13 |
| `GET /opinions` | 2,17 → 1,31 | 2,79 → 1,55 | 2,33 → 2,37 | 3,06 → 2,99 |
| `GET /me/registrations/{id}/groups` | 2,22 → 1,60 | 2,59 → 1,92 | 3,29 → 2,56 | 4,05 → 3,16 |
| `GET /groups/{id}/students` | 3,23 → 2,32 | 3,85 → 2,93 | 3,40 → 2,83 | 4,05 → 3,36 |
| `GET /students/{idx}` | 5,49 → 4,33 | 6,09 → 5,26 | 5,60 → 5,16 | 6,46 → 5,97 |
| `PUT /groups/{id}/students/{idx}/grade` | 2,27 → 1,72 | 2,81 → 1,98 | 2,33 → 1,85 | 2,77 → 2,55 |

Rozszerzenie skróciło czas w warstwie sterownika dla zapytań punktowych o 0,4–0,9 ms (8–30%), a dla katalogu przedmiotów o 5–10 ms. Ponieważ wariant z rozszerzeniem mierzono jako drugi i w skali 1 000 studentów czas samego silnika również obniżył się o 15–25%, część poprawy należy przypisać rozgrzaniu bazy. Nawet z użyciem `neo4j-rust-ext` narzut sterownika Neo4j wynosi 1,1–3,6 ms ponad czas silnika wobec 0,2–1,3 ms w PostgreSQL. Główną przyczyną pozostaje liczba osobnych transakcji automatycznych przypadających na jedno żądanie API oraz konwersja typów w Pythonie (`native()`, 5.5.5); większy zysk wymagałby przebudowy backendu na jedną transakcję na żądanie.

7.8.5 Podsumowanie porównania

Przeprowadzone pomiary wykazują, że w większości operacji systemu (zapytania punktowe) oba silniki wykonują zapytania w czasie poniżej 1,5 ms, a o czasie odpowiedzi API decydują warstwy komunikacyjne i pośredniczące. W ujęciu końcowym backend relacyjny okazał się 1,5–2,1 raza szybszy przy zapytaniach punktowych (głównie dzięki tańszej komunikacji sterownika w jednej transakcji i przygotowanym zapytaniom) oraz 2,4 raza szybszy w agregującym zapytaniu katalogu przedmiotów.

Przewaga koncepcyjna modelu grafowego uwidoczniła się w niemal stałej liczbie odwołań *db hits* dla zapytań rozpoczynających się od jednego węzła, w mniejszym rozmiarze bazy na dysku oraz w krótszych zapytaniach wykorzystujących wieloetykietowość (np. logowanie). W badanym zakresie skali nie przełożyło się to jednak na przewagę czasową, ponieważ odpowiednie indeksy w PostgreSQL zapewniły równie dobre skalowanie. Jednocześnie baza relacyjna wymusza w samym schemacie większą liczbę ograniczeń dziedzinowych (6.2.3, 7.5.1) i pozwala na znacznie szybszy import dużych zbiorów danych.
