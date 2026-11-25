5.1 Technologie i środowisko
Środowisko składa się z kontenerów Docker. Część z nich to gotowy obraz, część wymagała własnego Dockerfile. Całością zarządza narzędzie Docker Compose. 

W celu zabezpieczenia ruchu pomiędzy kontenerami wprowadzono szyfrowanie TLS (2.2) zgodnie z dokumentacją: https://neo4j.com/docs/operations-manual/current/security/ssl-framework/. Dotyczy ono konsoli Neo4j i połączenia Bolt wystawianego przez bazę. Szyfrowane są również połączenia przeglądarki z serwerem nginx oraz serwera nginx z API. Z racji tego, że projekt nie zakłada produkcyjnego wdrożenia, nie wdrożono pełnoprawnego urzędu certyfikacji CA.

5.1.1 Certyfikaty

Szyfrowanie TLS w projekcie obejmuje cztery połączenia: protokół Bolt bazy Neo4j (port 7687), konsolę Neo4j wystawioną po HTTPS (port 7473), serwer nginx serwujący klienta webowego (port 443 w kontenerze, 5173 na hoście) oraz API, do którego nginx przekazuje żądania (port 8000). Szyfrowane jest również połączenie API z bazą PostgreSQL, wykorzystywaną w porównaniu z modelem relacyjnym (rozdział 6). Każdy z tych serwisów ma własną parę certyfikatu i klucza prywatnego. Wszystkie certyfikaty są podpisane tym samym lokalnym urzędem certyfikacji.

Do wygenerowania certyfikatów wykorzystano narzędzie mkcert [CYTOWANIE: https://github.com/FiloSottile/mkcert]. Tworzy ono na komputerze programisty lokalny urząd certyfikacji, a polecenie `mkcert -install` dodaje jego certyfikat główny do systemowego magazynu zaufanych certyfikatów oraz do magazynów przeglądarek. Certyfikaty podpisane przez to CA są przez przeglądarkę akceptowane bez ostrzeżeń, w przeciwieństwie do certyfikatów samopodpisanych (ang. *self-signed*), które każda przeglądarka oznacza jako niezaufane. Jednocześnie, w odróżnieniu od certyfikatów samopodpisanych, możliwa jest pełna weryfikacja certyfikatu po stronie klientów, łącznie ze sprawdzeniem nazwy hosta.

Certyfikaty generuje skrypt `certs.sh`, który należy uruchomić przed pierwszym `docker compose up`. Skrypt kopiuje do projektu certyfikat lokalnego CA, a następnie dla każdego serwisu wywołuje funkcję `cert`, generującą parę certyfikatu i klucza.

`mkcert -CAROOT` zwraca ścieżkę katalogu lokalnego CA. Do projektu kopiowany jest wyłącznie publiczny certyfikat główny `rootCA.pem`, zapisywany jako `ca.pem`. Klucz prywatny CA (`rootCA-key.pem`) nie opuszcza tego katalogu, więc nie trafia do żadnego kontenera. Plik `ca.pem` służy klientom do weryfikacji certyfikatu serwera.

Klucz prywatny lokalnego CA wymaga szczególnej ochrony. Polecenie `mkcert -install` dodaje certyfikat CA do magazynów zaufanych certyfikatów systemu i przeglądarek jako certyfikat główny. Certyfikat ten nie zawiera ograniczeń nazw (rozszerzenie *Name Constraints*) i jest ważny przez 10 lat. Wyciek pliku `rootCA-key.pem` pozwoliłby więc wystawić certyfikat dla dowolnej domeny, akceptowany na tej maszynie bez ostrzeżeń. Atakujący w pozycji pośrednika (ang. *Man-in-the-Middle*) mógłby wtedy odczytywać i modyfikować dowolny ruch HTTPS tego komputera, również niezwiązany z projektem. Dlatego klucz jest czytelny wyłącznie dla właściciela katalogu mkcert, a po zakończeniu pracy z projektem należy usunąć CA z magazynów poleceniem `mkcert -uninstall` [CYTOWANIE: https://github.com/FiloSottile/mkcert].

Funkcja `cert` tworzy dla wskazanego serwisu katalog `certificates/<serwis>/` z certyfikatem `public.crt` i kluczem prywatnym `private.key`. Pozostałe argumenty to nazwy hosta, zapisywane w polu Subject Alternative Name certyfikatu:
- Neo4j: `neo4j` – nazwa serwisu w Docker Compose, pod którą kontenery `init` i `app` łączą się z bazą (`bolt+s://neo4j:7687`). Docker udostępnia w sieci projektu wewnętrzny serwer DNS (ang. *Domain Name System*), który rozwiązuje nazwy serwisów na adresy IP (ang. *Internet Protocol*) kontenerów. Schemat `bolt+s` wymaga, by nazwa w adresie zgadzała się z nazwą w certyfikacie. Druga nazwa, `localhost`, służy do otwierania konsoli Neo4j w przeglądarce oraz do łączenia się narzędzi programistycznych z przekierowanym portem 7687.
- nginx: wyłącznie `localhost` – adres, pod którym przeglądarka otwiera aplikację kliencką.
- API: `app` – nazwa serwisu, pod którą nginx przekazuje żądania do API (`https://app:8000`), oraz `localhost`, używana przy bezpośrednim dostępie do API z hosta i przez serwer deweloperski Vite.
- PostgreSQL: `postgres` i `localhost`, analogicznie do Neo4j.

Nazwy plików `public.crt` i `private.key` są domyślnymi nazwami oczekiwanymi przez politykę SSL (ang. *Secure Sockets Layer*) Neo4j w katalogu wskazanym przez `base_directory` [CYTOWANIE: https://neo4j.com/docs/operations-manual/current/security/ssl-framework/]. Ponieważ polityki `bolt` i `https` wskazują ten sam katalog, oba połączenia Neo4j korzystają z tej samej pary kluczy.

Osobne pary kluczy wynikają z zasady najmniejszych uprawnień. Każdy kontener montuje wyłącznie katalog z własną parą oraz publiczny certyfikat `ca.pem`, więc przejęcie jednego z nich nie pozwala podszyć się pod żaden inny serwis. Ma to szczególne znaczenie dla nginx. Jest to jedyny serwis, z którym łączy się przeglądarka, a więc najbardziej narażony na wykorzystanie podatności serwera.

Skrypt nadaje kluczom prywatnym prawa `644`, czyli prawo odczytu dla wszystkich użytkowników. Jest to konieczne, ponieważ procesy w kontenerach działają z innym identyfikatorem użytkownika (UID, ang. *User Identifier*) niż właściciel plików na hoście (np. API działa jako użytkownik `api` o UID 10001, opisany w 5.1.5), a katalogi z certyfikatami są montowane w trybie tylko do odczytu.

We wdrożeniu produkcyjnym certyfikat serwera webowego zostałby zastąpiony certyfikatem publicznego CA (np. Let's Encrypt).


5.1.2 Docker Compose

Konfiguracja wszystkich serwisów znajduje się w pliku `docker-compose.yml` w repozytorium. Kolejne sekcje opisują decyzje dotyczące poszczególnych serwisów, z wyjątkiem serwisu `postgres`, opisanego w 6.3.

Docker Compose pozwala na jednoczesne uruchamianie wszystkich kontenerów i proste zarządzanie nimi. Dodatkowo, dzięki niemu można ładować zmienne środowiskowe do tych kontenerów. Są one pobierane z pliku `.env` na potrzeby prototypu. We wdrożeniu produkcyjnym zmienne te powinny pochodzić z dedykowanego magazynu sekretów, np. HashiCorp Vault.

5.1.3 Serwis neo4j

Ten kontener bazuje na obrazie `neo4j:2026.07.1-enterprise`. Jest on grafową bazą danych, potrzebną do przechowywania struktury uczelni i dostępów. Wymagana jest wersja obrazu 2025.06 lub nowsza, ponieważ dopiero od niej działa Cypher 25. By dodatkowo móc ustawić GRAPH TYPE, potrzebna była wersja 2026.02 lub nowsza, w tym konieczny był wybór wersji enterprise, ponieważ tylko tam działa ta funkcja.  [CYTOWANIE: https://neo4j.com/docs/cypher-manual/current/queries/select-version/] [CYTOWANIE: https://neo4j.com/docs/cypher-manual/current/schema/graph-types/set-graph-types/]. W związku z wersją enterprise, wymagane było ustawienie zmiennej `NEO4J_ACCEPT_LICENSE_AGREEMENT: "yes"`.

Instancja Neo4j wystawia wiele portów, ale z kontenera przekierowywane są jedynie 7473 i 7687. [CYTOWANIE: https://neo4j.com/docs/operations-manual/current/configuration/ports/] Port 7473 służy do połączenia z HTTPS API i konsolą Neo4j, dającą programiście możliwość wygodnego podglądu na węzły i krawędzie. Jest to narzędzie typowo programistyczne, zatem w produkcyjnym wdrożeniu należy je wyłączyć lub ograniczyć do sieci wewnętrznej.

W trakcie prac nad systemem wystawiany był port 7474 - HTTP. Wdrożono jednak certyfikaty i szyfrowanie TLS/SSL, co pozwoliło na korzystanie z konsoli HTTPS.

![[Pasted image 20261114171135.png]]
*Brak możliwości wejścia na konsolę HTTP*

![[Pasted image 20261114171233.png]]
*Zrzut ekranu z konsoli Neo4j wystawionej po HTTPS na porcie 7473*

Port TCP (ang. *Transmission Control Protocol*) 7687 to domyślny port połączenia Bolt. Jest on wykorzystywany przez Cypher Shell, pokazaną wyżej konsolę Neo4j oraz przez oficjalne sterowniki Neo4j. Z racji tego, że API będzie wykorzystywało sterownik Neo4j do komunikacji z bazą, port 7687 jest konieczny.

Żeby połączenie między bazą a API było odporne na podsłuch, wprowadzono szyfrowanie poprzez TLS/SSL. W związku z tym, że SSL jest włączony z Bolt, URI (ang. *Uniform Resource Identifier*) zmienia się z `bolt` na `bolt+s`.

Pozostałe porty domyślnie włączone na instancjach Neo4j, takie jak "Cluster routing connector" czy "Remote debugging" uznano za niepotrzebne. W związku z tym, że nie są one potrzebne, to nie powinny być wystawiane.

Konfiguracja bazowego obrazu Neo4j odbywa się poprzez ustawianie zmiennych środowiskowych. Poza wcześniej wymienioną zmienną potrzebną do akceptowania licencji enterprise, należało włączyć szyfrowanie (https i bolt+s), wyłączyć domyślnie włączone, niebezpieczne protokoły (http), przekazać katalog z zaufanymi certyfikatami, a także przekazać dane do inicjalizacji konta administratora, pobierane z `.env`.

Wolumeny zamontowane w ramach tego serwisu to `neo4j_data`, `import`, katalog `certificates/neo4j` oraz certyfikat `ca.pem`. Para kluczy Neo4j jest konieczna do wdrożenia szyfrowania SSL/TLS, a certyfikat CA wykorzystuje test stanu, opisany poniżej. Import zawiera dane, które będą importowane do bazy danych po jej uruchomieniu. `neo4j_data` służy do przechowywania danych w samej bazie już po inicjalizacji, w tym zmian wprowadzonych na żywej instancji pomiędzy uruchomieniami kontenera.

Ostatnim elementem konfiguracji kontenera jest test stanu (ang. *healthcheck*), od którego wyniku zależy uruchomienie pozostałych serwisów korzystających z bazy danych. Test jest wykonywany co 30 s, po upływie 60 s od startu kontenera, z limitem czasu 10 s na próbę. Jeśli pięć kolejnych prób zakończy się niepowodzeniem, serwis zostaje oznaczony jako niesprawny, a zależne od niego serwisy nie zostaną uruchomione.

5.1.4 Serwis init

Neo4j nie ma możliwości uruchomienia skryptu inicjalizacyjnego po uruchomieniu bazy danych. Do utworzenia schematu, importu danych i utworzenia konta API służy więc osobny serwis `init`.

Serwis korzysta z obrazu API (5.1.5), ponieważ zawiera on już sterownik Neo4j dla Pythona. Uruchamia się dopiero wtedy, gdy serwis `neo4j` osiągnie stan „zdrowy” (ang. *healthy*), sprawdzany opisanym wcześniej testem stanu.

Zmienne przekazane do kontenera to adres bazy danych (`bolt+s://neo4j:7687`), dane do logowania administratora bazy oraz nazwa i hasło konta z ograniczonymi uprawnieniami, którym API będzie łączyło się z bazą. Dane administratora są potrzebne do zdefiniowania schematu, w tym ograniczeń, oraz do zaimportowania danych z plików CSV (ang. *Comma-Separated Values*).

Montowane są katalog `queries` z instrukcjami Cypher, skrypt `init_db.py` oraz certyfikat `ca.pem`. Wszystkie są zamontowane w trybie `ro` (ang. *read only*), ponieważ serwis `init` nie ma powodu, by je modyfikować. Kontener ma ponadto nałożone te same ograniczenia co serwis `app` (`read_only`, `cap_drop: ALL`, `no-new-privileges`, 5.1.5).

Skrypt `init_db.py` wykonuje kolejno instrukcje z plików `schema.cypher`, `nodes.cypher`, `edges.cypher` i `security.cypher`:

```python
with driver.session(database="neo4j") as session:
    for query in statements("schema.cypher"):
        session.run(query).consume()

    with session.begin_transaction() as tx:
        for name in ("nodes.cypher", "edges.cypher"):
            for query in statements(name):
                tx.run(query).consume()
        tx.commit()

with driver.session(database="system") as session:
    for query in statements("security.cypher"):
        session.run(query, user=app_user, pw=app_password).consume()
```

*Wykonanie instrukcji inicjalizacyjnych (`init_db.py`)*

Funkcja `statements()` dzieli plik na instrukcje zakończone średnikiem. Zmiany schematu nie mogą znajdować się w jednej transakcji z zapisem danych, dlatego plik `schema.cypher` jest wykonywany osobno. Import węzłów i krawędzi odbywa się w jednej jawnej transakcji, więc dane zostają załadowane w całości albo wcale. Instrukcje administracyjne dotyczą bazy `system` i są wykonywane pojedynczo. Działanie skryptów ładujących dane opisano w 5.3.

Każdy błąd przerywa skrypt wyjątkiem, a kontener kończy działanie z kodem różnym od 0. Serwis `app` uruchamia się wyłącznie po pomyślnym zakończeniu serwisu `init` (`condition: service_completed_successfully`).

Sterownik weryfikuje certyfikat serwera na podstawie pliku wskazanego zmienną środowiskową `SSL_CERT_FILE`, czyli certyfikatu lokalnego CA (`ca.pem`) [CYTOWANIE: https://docs.python.org/3/library/ssl.html]. Schemat `bolt+s` sprawdza przy tym podpis certyfikatu i nazwę hosta. Neo4j udostępnia też schemat `bolt+ssc`, który mimo skrótu od *self-signed certificate* w nazwie w ogóle nie weryfikuje ani certyfikatu serwera, ani jego podpisu, ani nazwy hosta. Połączenie pozostaje szyfrowane, ale klient nie ma pewności, z kim się łączy. Atakujący w pozycji pośrednika, posługujący się dowolnym certyfikatem, mógłby podszyć się pod serwer bazy danych, a tym samym odczytać i modyfikować ruch, w tym przesyłane dane uwierzytelniające.

Instrukcje z pliku `security.cypher` tworzą użytkownika bazy danych z ograniczonymi uprawnieniami, wykorzystywanego przez API. Rola `app_rw` pozwala na odczyt i zapis danych w grafie `neo4j`, ale nie obejmuje zarządzania schematem ani użytkownikami. Neo4j przyznaje wyłącznie jawnie nadane uprawnienia, więc te operacje są niedostępne bez dodatkowej konfiguracji. Inaczej jest z uprawnieniem `LOAD`, pozwalającym m.in. na wczytywanie plików poleceniem `LOAD CSV`: każdy użytkownik posiada rolę `PUBLIC`, która domyślnie ma nadane `LOAD ON ALL DATA`. Dlatego zostało ono jawnie odebrane poleceniem `DENY`, które ma pierwszeństwo przed `GRANT`. Ograniczenie uprawnień zmniejsza skutki ewentualnego przejęcia lub błędnej konfiguracji warstwy API.

```cypher
CREATE OR REPLACE USER $user SET PASSWORD $pw CHANGE NOT REQUIRED;
CREATE ROLE app_rw IF NOT EXISTS;
GRANT ACCESS ON DATABASE neo4j TO app_rw;
GRANT MATCH {*} ON GRAPH neo4j TO app_rw;
GRANT WRITE ON GRAPH neo4j TO app_rw;

DENY LOAD ON ALL DATA TO app_rw;
GRANT ROLE app_rw TO $user;
```

*Utworzenie konta API o ograniczonych uprawnieniach (`security.cypher`)*

Nazwa i hasło konta są przekazywane jako parametry zapytania `$user` i `$pw`. Sterownik przesyła je do serwera oddzielnie od treści zapytania, więc nie są interpretowane jako kod i nie wymagają żadnego przetwarzania.

Pierwsza wersja serwisu `init` korzystała z narzędzia cypher-shell, dostępnego w obrazie Neo4j. Nazwa i hasło konta API były przekazywane opcją `--param`:

```bash
cypher-shell -d system -f /queries/security.cypher \
    --param "user => '$NEO4J_APP_USER'" \
    --param "pw => '$NEO4J_APP_PASSWORD'"
```

*Pierwotne wywołanie `security.cypher` za pomocą narzędzia `cypher-shell`*

Wartość opcji `--param` jest wyrażeniem Cypher. Zgodnie z dokumentacją, wartością parametru może być dowolne wyrażenie Cypher, obliczane jednorazowo po stronie serwera [CYTOWANIE: https://neo4j.com/docs/operations-manual/current/cypher-shell/]. Umożliwia to przekazywanie wartości dowolnego typu, np. dat, ale oznacza też, że wartość zmiennej środowiskowej, wstawiona przez powłokę bash do treści wyrażenia, staje się fragmentem kodu Cypher. Objęcie wartości apostrofami tworzy z niej literał tekstowy, jednak tylko dopóki sama wartość nie zawiera apostrofu. Inicjalizacja była więc podatna na wstrzyknięcie kodu Cypher (ang. *Cypher injection*), a wartości zawierające znaki o specjalnym znaczeniu, takie jak `'` czy `\`, powodowały błąd inicjalizacji lub ciche zapisanie innego hasła niż podane w `.env`.

*Wartość parametru `pw` w zależności od zawartości zmiennej `NEO4J_APP_PASSWORD`*

| Wartość w `.env`     | Apostrofy w poleceniu | Wyrażenie otrzymane przez cypher-shell | Wynik                                               |
| -------------------- | --------------------- | -------------------------------------- | --------------------------------------------------- |
| `hunter2`            | nie                   | `pw => hunter2`                        | błąd: niezdefiniowana zmienna `hunter2`             |
| `1+1`                | nie                   | `pw => 1+1`                            | `2` (INTEGER)                                       |
| `hunter2`            | tak                   | `pw => 'hunter2'`                      | `"hunter2"` (STRING), poprawnie                     |
| `it's`               | tak                   | `pw => 'it's'`                         | błąd: apostrof kończy literał                       |
| `' + datetime() + '` | tak                   | `pw => '' + datetime() + ''`           | `"2026-11-14T18:53:46.592Z"` (STRING), wykonany kod |

Z poziomu samego Cypher nie da się tego obejść, ponieważ problem występuje już na etapie parsowania wyrażenia, zanim jakakolwiek funkcja mogłaby przetworzyć wartość. Z tego powodu cypher-shell zastąpiono skryptem korzystającym ze sterownika. Zmiana uprościła również weryfikację certyfikatu.

Skrypt jest uruchamiany przy każdym starcie środowiska, a dane bazy, w tym użytkownicy, są zachowywane w wolumenie `neo4j_data`. Dlatego musi on działać poprawnie także wtedy, gdy użytkownik już istnieje, i jednocześnie uwzględniać ewentualną zmianę hasła w `.env`. Spełnia to polecenie `CREATE OR REPLACE USER`, które tworzy użytkownika od nowa z bieżącym hasłem – `CREATE USER … IF NOT EXISTS` pominąłby zmianę hasła, a `ALTER USER … SET PASSWORD` kończy się błędem, gdy hasło się nie zmieniło.

5.1.5 Serwis app
Odpowiada on za backend aplikacji, czyli API dające klientom wygodny dostęp do zawartości grafowej bazy danych.
Serwis `app` jest budowany z pliku `Dockerfile` w katalogu głównym repozytorium, bazującego na obrazie `python:3.14-slim`. Zależności z `requirements.txt` są instalowane przed skopiowaniem kodu aplikacji. Dzięki temu przy zmianie samego kodu Docker ponownie wykorzystuje warstwę z zainstalowanymi pakietami.

Obraz tworzy użytkownika systemowego `api` o UID 10001, bez katalogu domowego, i z jego uprawnieniami uruchamia aplikację. Przejęcie procesu aplikacji nie daje więc atakującemu uprawnień użytkownika `root`. Aplikację uruchamia serwer uvicorn na porcie 8000, pod adresem `0.0.0.0`, dzięki czemu jest ona osiągalna z innych kontenerów, np. z serwera nginx.

Opcje `--ssl-certfile` i `--ssl-keyfile` sprawiają, że uvicorn serwuje API wyłącznie po HTTPS. Certyfikat i klucz pochodzą z katalogu `certificates/app/` (5.1.1), montowanego w Docker Compose jako `/certs` w trybie tylko do odczytu.

Bez tego ruch między serwerem nginx a API odbywałby się zwykłym HTTP. Szyfrowanie TLS kończyłoby się na nginx, a token JWT, dane logowania i odpowiedzi API przechodziłyby przez sieć Dockera jawnym tekstem. Choć sieć ta jest izolowana od hosta, każdy kontener w niej podłączony mógłby taki ruch podsłuchać lub podszyć się pod API.

Aplikacja wystawiona na porcie 8000 jest również przekierowywana na port 8000 localhost, dzięki czemu API jest dostępne dla programisty pod adresem `https://localhost:8000/api`.

![[Pasted image 20261115020127.png]]

*API widoczne z przeglądarki*

W produkcyjnym wdrożeniu port 8000 w tym kontenerze nie powinien być wystawiony na hosta. Nie jest on potrzebny do działania systemu: z bazą danych połączenie jest wykonywane po `bolt+s://neo4j:7687`, a aplikacja kliencka widzi API poprzez serwer nginx w kontenerze `frontend`, pełniący rolę odwrotnego proxy (ang. *reverse proxy*). Przeglądarka komunikuje się wyłącznie z nginx po HTTPS, w ramach tego samego pochodzenia (ang. *origin*) co aplikacja kliencka, a nginx przekazuje żądania kierowane do ścieżek zaczynających się od `/api` pod adres `https://app:8000` w wewnętrznej sieci Dockera (5.1.6).

Zmienne środowiskowe przekazują aplikacji konfigurację w postaci adresu bazy danych (`NEO4J_URI`) i danych uwierzytelniających użytkownika systemowego stworzonego przez serwis `init` (`NEO4J_USER` i `NEO4J_PASSWORD`). Dodatkowo przekazywany jest `JWT_SECRET` potrzebny do podpisywania tokenów wydawanych przez API oraz `SSL_CERT_FILE`, czyli ścieżka do certyfikatu. Dzięki tej zmiennej certyfikat zostaje załadowany do zaufanych certyfikatów, co pozwala później z nich korzystać.

Zmienne `PG_CONNINFO` i `PG_PASSWORD` służą backendowi relacyjnemu (6.3).

Składnia `${ZMIENNA:?komunikat}` sprawia, że Docker Compose odmawia uruchomienia, jeśli zmienna nie jest ustawiona w `.env` [CYTOWANIE: https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/]. Zapobiega to sytuacjom, w których kontenery uruchamiają się z błędnymi zmiennymi.

Wolumeny montują certyfikat CA (`/ca.pem`) oraz certyfikat i klucz API (`/certs`), oba w trybie tylko do odczytu.

Pozostałe opcje ograniczają możliwości kontenera na wypadek przejęcia aplikacji:
- `read_only: true` – system plików kontenera jest tylko do odczytu, więc atakujący nie może podmienić kodu aplikacji ani zapisać własnych plików wykonywalnych.
- `tmpfs: /tmp` – jedyny zapisywalny katalog, przechowywany w pamięci RAM (ang. *Random Access Memory*) i znikający po zatrzymaniu kontenera. Jest potrzebny bibliotekom, które zapisują pliki tymczasowe.
- `cap_drop: ALL` – odbiera procesowi wszystkie uprawnienia jądra Linux (ang. *capabilities*), np. możliwość zmiany właściciela plików czy obsługi surowych gniazd sieciowych. Aplikacja nasłuchuje na porcie 8000, powyżej 1024, więc żadne z nich nie jest jej potrzebne.
- `no-new-privileges:true` – uniemożliwia procesowi uzyskanie nowych uprawnień, np. przez uruchomienie programu z bitem setuid. Uzupełnia to działanie jako nieuprzywilejowany użytkownik `api`.

`depends_on` z warunkiem `service_completed_successfully` sprawia, że API startuje dopiero po pomyślnym zakończeniu serwisu `init`, czyli gdy baza zawiera już schemat, dane i konto `app_rw`. Gdyby inicjalizacja się nie powiodła, API w ogóle nie zostanie uruchomione. Analogicznie API czeka na gotowość serwisu `postgres` (6.3).


5.1.6 Serwis frontend

Serwis `frontend` jest punktem wejścia do systemu dla użytkownika: serwer nginx serwuje aplikację kliencką Vue (5.6) i pełni rolę odwrotnego proxy dla API (2.3) pod jednym adresem (`https://localhost:5173`), dzięki czemu nie jest potrzebna konfiguracja CORS. Obraz powstaje w budowaniu wieloetapowym (ang. *multi-stage build*) z pliku `frontend/Dockerfile` – etap `build` z Node.js buduje aplikację, a do końcowego obrazu `nginx:1.27-alpine` trafiają wyłącznie pliki statyczne z katalogu `dist`, co ogranicza rozmiar kontenera i powierzchnię ataku.

Konfiguracja w pliku `frontend/nginx.conf` nasłuchuje wyłącznie na porcie 443 z TLS, przekierowanym na `127.0.0.1:5173` (powiązanie z adresem lokalnym zapobiega publikacji portu na wszystkich interfejsach z pominięciem zapory hosta [CYTOWANIE: https://docs.docker.com/engine/network/packet-filtering-firewalls/]). Brak bloku dla portu 80 sprawia, że nieszyfrowane żądania HTTP są odrzucane odpowiedzią `400 Bad Request`.

![[Pasted image 20261115022335.png]]

*Odpowiedź nginx na żądanie HTTP*

Serwer korzysta z własnej pary kluczy (`certificates/nginx/`, 5.1.1) dla nazwy `localhost`, podpisanej lokalnym CA z mkcert, więc przeglądarka otwiera aplikację bez ostrzeżeń.

![[Pasted image 20261115022652.png]]
*Aplikacja kliencka pod adresem https://localhost:5173 z informacją o poprawnym certyfikacie*

Żądania z prefiksem `/api/` trafiają przez `proxy_pass` do `https://app:8000` wraz z nagłówkami oryginalnego żądania (host, adres IP klienta, protokół). Ponieważ nginx domyślnie nie weryfikuje certyfikatu serwera docelowego [CYTOWANIE: https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_ssl_verify], włączono `proxy_ssl_verify` z zaufanym lokalnym CA, ograniczono połączenie do TLS 1.3 oraz wymuszono sprawdzenie nazwy `app` przekazywanej w SNI (ang. *Server Name Indication*). Pozostałe ścieżki obsługuje blok SPA: dyrektywa `try_files` zwraca `index.html` dla tras routera w przeglądarce, natomiast brakujące pliki w `/assets/` kończą się błędem 404 i są buforowane bezterminowo (`immutable`), przy wyłączonym buforowaniu `index.html` (`no-cache`).

Zgodnie z zasadą najmniejszych uprawnień (5.1.1) kontener montuje wyłącznie trzy potrzebne pliki (`ca.pem`, certyfikat i klucz nginx), bez dostępu do kluczy pozostałych serwisów. Na kontener nałożono te same ograniczenia co na serwis `app` (`read_only`, `no-new-privileges`, 5.1.5), z katalogami `tmpfs` dla `/var/cache/nginx` i `/var/run` (plik PID, ang. *Process Identifier*) oraz `cap_drop: ALL` z przywróceniem jedynie uprawnień wymaganych przez nginx (`NET_BIND_SERVICE`, `SETUID`, `SETGID` i `CHOWN`) [CYTOWANIE: https://man7.org/linux/man-pages/man7/capabilities.7.html]. We wdrożeniu produkcyjnym można użyć obrazu `nginxinc/nginx-unprivileged`, działającego bez uprawnień jądra.

5.2 Struktura repozytorium

```
.
├── app
├── certificates
│   ├── app
│   ├── neo4j
│   ├── nginx
│   └── postgres
├── endpoint_schema
├── frontend
│   ├── Dockerfile
│   ├── nginx.conf
│   └── src
├── import
│   ├── edges
│   └── nodes
├── queries
├── sql
├── bench
├── tests
├── .env.example
├── certs.sh
├── docker-compose.yml
├── Dockerfile
├── init_db.py
└── requirements.txt
```

*Struktura katalogów i głównych plików repozytorium*

Klient Vue jest w całości zawarty w katalogu `frontend/`, wraz z plikiem `Dockerfile` budującym jego obraz i konfiguracją serwera nginx (`nginx.conf`), który go serwuje.

W katalogu `app/` znajduje się backend, w tym warstwa API (szczegółową strukturę przedstawiono w 5.5.1). W podkatalogu `schemas/` zdefiniowano modele Pydantic, opisujące oczekiwany kształt żądań i odpowiedzi serwera, niezależne od bazy danych. W podkatalogu `graph_backend/` znajduje się backend grafowy, czyli cały kod zależny od Neo4j. Plik `database.py` tworzy w nim połączenie z bazą za pomocą sterownika, punkty końcowe znajdują się w `routers/`, pogrupowane według ról użytkowników, uwierzytelnianie i autoryzacja w `auth/`, wspólna obsługa błędów w `errors.py`, a zapytania do bazy danych w pozostałych modułach.

Podkatalog `relation_backend/` oraz katalogi `sql/`, `bench/` i `tests/` dotyczą porównania z modelem relacyjnym i testów (rozdziały 6 i 7).

Ponieważ eksploracja bazy danych jest szczególnym celem tej pracy, poświęcono jej dużą część repozytorium. Katalog `import/` zawiera dane początkowe, a katalog `queries/` – instrukcje w języku Cypher wykonywane przy inicjalizacji bazy danych przez skrypt `init_db.py` (5.1.4, 5.3). Katalog `endpoint_schema/` zawiera dokumentację punktów końcowych API (5.4).

Katalog `certificates/` jest tworzony przez skrypt `certs.sh` (5.1.1). Zawiera certyfikat lokalnego CA (`ca.pem`) oraz osobne podkatalogi z certyfikatem i kluczem każdego serwisu: `neo4j/`, `nginx/`, `app/` i `postgres/`.

Dane dostępowe (hasła do bazy danych i klucz podpisujący tokeny) przechowywane są w pliku `.env`. Wymagane zmienne opisano w pliku `.env.example`.

5.3 Inicjalizacja i schemat bazy danych

W katalogu `import/` znajdują się dane w formacie CSV, importowane przy inicjalizacji bazy danych – `nodes/` zawiera węzły, a `edges/` krawędzie. Na każdy typ węzła i na każdy typ krawędzi przypada osobny plik. Wyjątkiem jest etykieta `User` – dane logowania (adres e-mail i skrót hasła) są kolumnami w plikach studentów, prowadzących i administratorów, a etykieta nadawana jest przy imporcie tym osobom, które mają podany adres e-mail.

Skrypt `init_db.py` (5.1.4) wykonuje kolejno instrukcje z katalogu `queries/`: `schema.cypher` narzuca kształt węzłów i krawędzi oraz pozostałe ograniczenia, `nodes.cypher` i `edges.cypher` wczytują pliki CSV z węzłami i krawędziami, a `security.cypher` tworzy konto bazodanowe, którym łączy się API (4.4.3).

Definicja typu grafu w `schema.cypher` jest zapisana w wersji Cypher 25 (`CYPHER 25 ALTER CURRENT GRAPH TYPE SET ...`), ponieważ ta funkcja jest dostępna wyłącznie w tej wersji języka. Pozostałe zapytania, zarówno importujące, jak i wykonywane przez API, korzystają z domyślnej wersji języka skonfigurowanej w bazie.

5.3.1 Schemat bazy danych

Plik `schema.cypher` jest ładowany do bazy danych jako pierwszy, skryptem `init_db.py` opisanym w 5.1.4. Definiuje on typ grafu, czyli opis dopuszczalnego kształtu węzłów i krawędzi. Typ grafu pozwala określić typy danych właściwości, wymagać ich istnienia oraz narzucić inne ograniczenia, takie jak klucze i unikalność. Funkcja ta jest dostępna wyłącznie w wersji Enterprise Neo4j, co było jednym z powodów wyboru obrazu `neo4j:2026.07.1-enterprise` (5.1.3).

Dla każdego przewidzianego typu węzła powstało w tym pliku odpowiadające mu ograniczenie. Jako przykład posłuży definicja węzła grupy (`Group`):

```cypher
	(g:Group => {
		id :: STRING,
		weekday :: INTEGER NOT NULL,
		number :: INTEGER NOT NULL,
		pnp :: STRING NOT NULL,
		capacity :: INTEGER NOT NULL,
		start_time :: LOCAL TIME NOT NULL,
		end_time :: LOCAL TIME NOT NULL
	}) REQUIRE g.id IS KEY,
```

*Definicja węzła `Group` w typie grafu (`schema.cypher`)*

Zgodnie z projektem systemu węzeł grupy przechowuje identyfikator, dzień tygodnia, numer grupy, parzystość tygodni, w których odbywają się zajęcia, pojemność grupy oraz godziny rozpoczęcia i zakończenia zajęć. Godziny mają typ `LOCAL TIME`, czyli czas bez przesunięcia strefy czasowej (4.3.3).

Jako typ identyfikatora (`id`) przyjęto `STRING` zamiast `INTEGER`, ponieważ Neo4j nie obsługuje autoinkrementacji. Identyfikatory liczbowe wymagałyby osobnego, globalnego mechanizmu ich nadawania, z którego korzystałyby wszystkie zapytania tworzące nowe węzły. Alternatywą byłoby wyszukanie w grafie największego istniejącego identyfikatora i zwiększenie go o 1, lecz takie rozwiązanie jest podatne na wyścigi – dwie równoległe transakcje mogą odczytać tę samą wartość i nadać ten sam identyfikator. O wbudowaną autoinkrementację użytkownicy Neo4j proszą co najmniej od 2013 roku [CYTOWANIE: https://gist.github.com/tekiegirl/8012859]. Ten sposób wykorzystano jedynie w punkcie końcowym `GET /admin/people/next-idx`, który podpowiada administratorowi kolejny numer osoby (`idx`). Jest to wyłącznie podpowiedź: jeśli dwóch administratorów otrzyma ten sam numer, drugą próbę utworzenia osoby odrzuci ograniczenie `idx IS KEY`, a API zwróci kod 409.

Do tego celu nie nadaje się również wewnętrzny identyfikator elementu, zwracany przez funkcję `elementId()`. Dokumentacja Neo4j zastrzega, że poza pojedynczą transakcją nie ma żadnych gwarancji co do powiązania identyfikatorów z elementami, a identyfikatory usuniętych węzłów i krawędzi są ponownie wykorzystywane [CYTOWANIE: https://neo4j.com/docs/cypher-manual/current/functions/scalar/]. Dokumentacja wprost odradza więc opieranie aplikacji na wewnętrznych identyfikatorach i zaleca identyfikatory generowane przez aplikację.

Problemy te rozwiązuje zastąpienie identyfikatorów liczbowych identyfikatorami UUID (ang. *Universally Unique Identifier*). Wygenerowanie UUID nie wymaga przechowywania stanu ani znajomości identyfikatorów istniejących już w bazie. Cypher udostępnia do tego funkcję `randomUUID()`, która według dokumentacji zwraca „128-bitową wartość z silnymi gwarancjami unikalności” (ang. *a 128-bit value with strong guarantees of uniqueness*) [CYTOWANIE: https://neo4j.com/docs/cypher-manual/current/functions/scalar/]. W tym projekcie UUID jest identyfikatorem prawie wszystkich typów węzłów. Nowe identyfikatory generuje API funkcją `uuid4()` z biblioteki standardowej Pythona, a dane początkowe mają je zapisane w plikach CSV. Podobne stanowisko prezentują użytkownicy forum społeczności Neo4j, odradzając liczbową autoinkrementację, ponieważ silnik bazy danych powinien przedkładać wydajność i stabilność nad wygodę [CYTOWANIE: https://community.neo4j.com/t/how-to-auto-increment-to-get-unique-value-for-a-new-nodes-field/12815/7].

Właściwości `weekday`, `number` i `capacity` są liczbami całkowitymi. Dzień tygodnia naturalniej byłoby zapisać jako typ wyliczeniowy (ang. *enum*), dostępny w większości współczesnych języków programowania i w relacyjnych bazach danych, np. PostgreSQL. Neo4j nie obsługuje jednak typów wyliczeniowych i nie pozwala ograniczyć zbioru dopuszczalnych wartości właściwości, dlatego poprawność dnia tygodnia sprawdza warstwa aplikacji – model żądania `GroupCreateRequest` przyjmuje wyłącznie wartości od 1 do 7. Zastąpienie liczby siedmioma węzłami dni tygodnia wymagałoby dodatkowego przejścia po grafie przy każdym odczycie grupy, a baza i tak nie wymusiłaby istnienia krawędzi (4.3.7), dlatego z niego zrezygnowano. Przyjęto, że 1 oznacza poniedziałek, a 7 – niedzielę, zgodnie z normą ISO (ang. *International Organization for Standardization*) 8601 [CYTOWANIE: ISO 8601-1:2019] oraz z numeracją składowej `dayOfWeek` w typach czasowych Neo4j [CYTOWANIE: https://neo4j.com/docs/cypher-manual/current/values-and-types/temporal/].

Inaczej potraktowano sale, w których odbywają się zajęcia – są one osobnymi węzłami (`Room`), połączonymi z grupą krawędzią `IN_ROOM`:

```cypher
	(g)-[:IN_ROOM => {}]->(r),
```

*Definicja krawędzi `IN_ROOM` w typie grafu (`schema.cypher`)*

Sala, w przeciwieństwie do dnia tygodnia, jest samodzielnym bytem: ma własne właściwości (budynek i numer sali), w jednej sali odbywa się wiele grup, a zbiór sal zmienia się w czasie – powstają nowe budynki, a istniejące sale są wyłączane z użytku. Gdyby budynek i numer sali były właściwościami grupy, zmiana danych sali wymagałaby aktualizacji wszystkich odbywających się w niej grup, a literówka w nazwie budynku tworzyłaby w praktyce nową salę. Jako osobny węzeł sala jest zapisana w jednym miejscu, a ograniczenie unikalności pary budynek–numer sali (`REQUIRE (r.building, r.room_num) IS UNIQUE`) chroni przed duplikatami.

Właściwość `pnp`, określająca parzystość tygodni, w których odbywają się zajęcia, również skorzystałaby na typie wyliczeniowym. Przyjmuje ona jedną z trzech wartości tekstowych: `"P"` (tygodnie parzyste), `"NP"` (tygodnie nieparzyste) oraz `"ALL"` (co tydzień). Parzystość wyznaczana jest na podstawie numeru tygodnia według normy ISO 8601. Tę samą informację mogłyby przechowywać trzy liczby (`0`, `1`, `2`), jednak bez typu wyliczeniowego byłyby to liczby magiczne (ang. *magic numbers*) – programista rozwijający aplikację łatwo mógłby pomylić, czy 0 oznacza tygodnie parzyste, czy nieparzyste. Wartości tekstowe są czytelne same w sobie, a ich poprawność, podobnie jak w przypadku dnia tygodnia, sprawdza warstwa aplikacji – model `GroupCreateRequest` przyjmuje wyłącznie jedną z trzech wymienionych wartości. Ograniczeniem tego rozwiązania jest brak walidacji dozwolonych wartości po stronie samej bazy danych, co wynika z możliwości Neo4j.

Poza kształtem samego węzła `Group` typ grafu określa również, jakie krawędzie mogą łączyć grupę z innymi węzłami: `IN_ROOM` (grupa -> sala), `OF_TYPE` (grupa -> typ grupy), `ABOUT` (opinia -> grupa), `REGISTERED_IN` (student -> grupa), `OPENS` (rejestracja -> grupa) oraz `TEACHES` (prowadzący -> grupa). Krawędź `REGISTERED_IN` przechowuje dodatkowo dwie właściwości: `registered_at` typu `ZONED DATETIME` oraz `grade` typu `FLOAT`. W przypadku zapisu istotna jest zarówno data, jak i godzina, a strefa czasowa pozwala jednoznacznie określić ten moment. Ocena jest liczbą zmiennoprzecinkową, ponieważ w skali ocen występują wartości połówkowe (np. 3,5 i 4,5). Właściwość `grade` nie jest oznaczona jako `NOT NULL`, ponieważ student zostaje zapisany do grupy, zanim otrzyma ocenę – do tego czasu wartość pozostaje pusta.

```cypher
	(st)-[:REGISTERED_IN => {
		registered_at :: ZONED DATETIME NOT NULL,
		grade :: FLOAT
	}]->(g),
	(o)-[:ABOUT => {}]->(g),
	(g)-[:OF_TYPE => {}]->(gt),
	(reg)-[:OPENS => {}]->(g),
	(g)-[:IN_ROOM => {}]->(r),
	(t)-[:TEACHES => {}]->(g)
```

*Definicje krawędzi powiązanych z węzłem `Group` (`schema.cypher`)*

Graph type, poza typem danych, określa również, które właściwości są wymagane. Sama deklaracja `nazwa :: TYP` jedynie wymusza typ, jeśli właściwość występuje. Jej istnienie wymusza dopiero modyfikator `NOT NULL`. Wpis `REQUIRE g.id IS KEY` sprawia, że identyfikator grupy musi istnieć i dodatkowo musi być unikatowy.

Ograniczenie typu `KEY` jest równoważne połączeniu ograniczenia unikalności (`IS UNIQUE`) z ograniczeniem istnienia (`IS NOT NULL`) na tym samym zbiorze właściwości [CYTOWANIE: https://neo4j.com/docs/cypher-manual/current/schema/constraints/]:

```cypher
CREATE CONSTRAINT group_id_exists FOR (g:Group) REQUIRE g.id IS NOT NULL;
CREATE CONSTRAINT group_id_unique FOR (g:Group) REQUIRE g.id IS UNIQUE;
```

*Ograniczenia `IS NOT NULL` i `IS UNIQUE` równoważne ograniczeniu `IS KEY`*

`Group` jest węzłem przechowującym najwięcej informacji. Pozostałe węzły służące do definiowania domeny uczelnianej są skonstruowane w bardzo podobny sposób – typy danych określone w projekcie systemu są tłumaczone na typy danych dostępne w silniku Neo4j, a dodatkowe ograniczenia są nakładane analogicznie. Następnie, jeśli między węzłami mają istnieć krawędzie, są one również definiowane.

Wszystko przebiegłoby zgodnie z założeniami projektowymi, gdyby nie pewne ograniczenie mechanizmu graph type. Według dokumentacji (oraz błędu wielokrotnie napotkanego przez autora) nie jest możliwe zdefiniowanie typu węzła, który nie posiada żadnych właściwości ani nie implikuje żadnej etykiety [CYTOWANIE: https://neo4j.com/docs/cypher-manual/25/schema/graph-types/set-graph-types/]. Węzeł `SubjectInstance`, który zgodnie z projektem nie potrzebuje absolutnie żadnej właściwości, nie może więc otrzymać własnego typu węzła. Próba takiej definicji kończy się błędem 22NC2 – „data exception – node element type has no effect” [CYTOWANIE: https://neo4j.com/docs/status-codes/current/errors/gql-errors/22NC2/].

Surowy komunikat błędu zwracany przez Neo4j (wersja 2026.07.1 Enterprise) przy próbie zdefiniowania węzła bez właściwości:

```cypher
CYPHER 25 ALTER CURRENT GRAPH TYPE SET { (si:SubjectInstance => {}) }
```

*Próba zdefiniowania węzła `SubjectInstance` bez właściwości*

```shell
22NC2: data exception - node element type has no effect. The node element type `SubjectInstance` must contain one or more implied labels, or at least one property type.
  42001: syntax error or access rule violation - invalid syntax
```

*Komunikat błędu `22NC2` zwracany przez Neo4j*

Pierwszym obejściem, jakie się nasuwa, jest nadanie węzłowi sztucznego identyfikatora, np. `id :: STRING` z ograniczeniem `IS KEY`. Taka właściwość nie byłaby jednak do niczego wykorzystywana – węzeł i tak jest zawsze odnajdywany poprzez krawędzie łączące go z przedmiotem i cyklem akademickim – a wprowadzałaby do modelu informację, której projekt nie przewiduje. Węzeł, którego jedyną rolą jest łączenie innych węzłów krawędziami, jest w pełni poprawnym elementem modelu grafowego, a wymuszenie istnienia w nim właściwości lub implikowanej etykiety nie wnosi do schematu żadnej informacji.

Z tego powodu etykieta `SubjectInstance` została pominięta w definicjach węzłów i występuje w typie grafu jedynie jako początek wychodzących z niej krawędzi:

```cypher
	(:SubjectInstance)-[:INSTANCE_OF => {}]->(su),
	(:SubjectInstance)-[:OFFERED_IN => {}]->(ac),
	(:SubjectInstance)-[:HAS_TYPE => {}]->(gt),
```

*Definicje krawędzi wychodzących z węzła `SubjectInstance` (`schema.cypher`)*

Pozostałe węzły i krawędzie opisujące model uczelni nie napotkały podobnego problemu, ponieważ każdy z nich miał uzasadnione właściwości. Jeszcze inny problem pojawił się jednak w modelowaniu ludzi korzystających z platformy.

Jak wspomniano wcześniej, wykorzystano etykiety implikowane i wieloetykietowość, żeby każda osoba pracująca na uczelni oraz student musieli być człowiekiem.

```cypher
	(t:Teacher => :Person {
		degree :: STRING NOT NULL,
		working_since :: DATE NOT NULL
	}),

	(st:Student => :Person {
		joined :: ZONED DATETIME NOT NULL
	}),

	(u:User => :Person {
		email :: STRING,
		passwd_hash :: STRING NOT NULL
	}) REQUIRE u.email IS KEY,

	(a:Admin => :Person),

	(i:Inactive => :Person {
		deactivated_at :: ZONED DATETIME NOT NULL
	}),
```

*Definicje etykiet ról i konta implikujących etykietę `Person` (`schema.cypher`)*

Jak widać, w etykietach `Teacher`, `Student`, `User` i `Inactive` są przechowywane jedynie właściwości ekskluzywne dla tej roli. `Admin` nie niesie ze sobą żadnych dodatkowych informacji, zatem jedynie implikuje `Person`. Jest to dozwolony zabieg.

Problem pojawia się dopiero w samej definicji etykiety `Person`. Wygodne i oczywiste byłoby zdefiniowanie jej jako na przykład:

```cypher
 (p:Person => {
	 idx :: STRING,
	 name :: STRING NOT NULL,
	 surname :: STRING NOT NULL,
	 phone :: STRING NOT NULL,
	 photo :: STRING
 }) REQUIRE p.idx IS KEY,
```

*Próba zdefiniowania etykiety `Person` bezpośrednio w typie grafu*

Okazuje się, że próba zdefiniowania etykiet w ten sposób powoduje błąd 22NC4 [CYTOWANIE: https://neo4j.com/docs/status-codes/current/errors/gql-errors/22NC4/], dokładnie: 

```shell
  22NC4: data exception - a label cannot be both identifying and implied. The label(s) `Person` are defined as both identifying and implied. (line 
  2, column 20 (offset: 60))                                                       "    (t:Teacher => :Person {"                                                                                                                
                      ^                                                              42001: syntax error or access rule violation - invalid syntax
```

*Komunikat błędu `22NC4` zwracany przez Neo4j*

Jeśli w poleceniu graph type etykieta jest w ogóle zdefiniowana, to staje się ona identyfikująca. Jeśli jest ona identyfikująca, to jednocześnie nie może być implikowana, co zupełnie psuje mechanizm zaplanowany wcześniej.

Sposobem na ominięcie tego mechanizmu proponowanym przez Neo4j w opisie tego błędu jest zastąpienie definicji z graph type zwykłymi instrukcjami CONSTRAINT. Ponieważ wspólna etykieta, pełniąca rolę klasy bazowej, była potrzebna, etykieta `Person` jest zdefiniowana w postaci listy ograniczeń.

```cypher
	CONSTRAINT person_idx FOR (pe:Person) REQUIRE pe.idx IS KEY,
	CONSTRAINT person_identity FOR (pe:Person) REQUIRE (pe.name, pe.surname, pe.phone) IS UNIQUE,
	CONSTRAINT person_idx_type FOR (pe:Person) REQUIRE pe.idx IS :: STRING,
	CONSTRAINT person_name FOR (pe:Person) REQUIRE pe.name IS NOT NULL,
	CONSTRAINT person_name_type FOR (pe:Person) REQUIRE pe.name IS :: STRING,
	CONSTRAINT person_surname FOR (pe:Person) REQUIRE pe.surname IS NOT NULL,
	CONSTRAINT person_surname_type FOR (pe:Person) REQUIRE pe.surname IS :: STRING,
	CONSTRAINT person_phone FOR (pe:Person) REQUIRE pe.phone IS NOT NULL,
	CONSTRAINT person_phone_type FOR (pe:Person) REQUIRE pe.phone IS :: STRING,
	CONSTRAINT person_photo FOR (pe:Person) REQUIRE pe.photo IS :: STRING,

```

*Ograniczenia właściwości etykiety `Person` (`schema.cypher`)*

To samo ograniczenie uniemożliwia wyrażenie zależności etykiety `Inactive` od `User`. Dezaktywować można wyłącznie konto, więc `Inactive` powinna implikować `User`. Etykieta `User` ma jednak własną definicję w typie grafu, a więc jest identyfikująca. Definicja `(i:Inactive => :User {...})` kończy się tym samym błędem: „The label(s) `User` are defined as both identifying and implied”. Odrzucane jest również niezależne ograniczenie wymagające od węzła `Inactive` właściwości konta, ponieważ etykieta `Inactive` jest zdefiniowana w typie grafu („Independent constraints cannot be defined on label `Inactive`”).

Sprawdzono także obejście analogiczne do etykiety `Person`: zdefiniowanie `User` wyłącznie instrukcjami CONSTRAINT i zapis `(i:Inactive => :Person&User {...})`. Taki typ grafu odrzuca węzeł `Inactive` bez etykiety `User`. Etykieta `User` traci jednak implikację `Person`, więc baza przyjmuje węzeł `User` bez danych osoby. Implikacje nie są przechodnie. Każda etykieta pośrednia w hierarchii wymaga wypisania wszystkich etykiet nadrzędnych oraz rezygnacji z jej własnej definicji w typie grafu, przez co obejście usuwa jedną lukę kosztem drugiej. Pozostawiono więc definicję `Inactive => Person`, a regułę, że dezaktywować można tylko konto, egzekwuje API (4.3.1).

5.3.2 Import węzłów

Po zdefiniowaniu akceptowanych typów danych można zaimportować same dane. Plik `nodes.cypher` zawiera instrukcje Cypher pozwalające odczytać pliki .csv i na ich podstawie utworzyć węzły.

Import węzłów opisujących uczelnię jest bardzo prosty i zostanie omówiony na przykładzie grupy zajęciowej:

```cypher
LOAD CSV WITH HEADERS FROM "file:///nodes/groups.csv" AS row
MERGE (g:Group {id: row.id})
SET g.weekday = toInteger(row.weekday),
    g.number = toInteger(row.number),
    g.pnp = row.pnp,
    g.capacity = toInteger(row.capacity),
    g.start_time = localtime(row.start_time),
    g.end_time = localtime(row.end_time);
```

*Import węzłów `Group` z pliku CSV (`nodes.cypher`)*

Zaczyna się od instrukcji `LOAD CSV WITH HEADERS FROM "file:///nodes/groups.csv" AS row`. Odczytuje ona plik wiersz po wierszu, a każdy wiersz udostępnia jako zmienną `row`. Zmienna ta jest mapą, w której kluczami są nazwy kolumn z nagłówka, a wartościami – zawartość odpowiadających im komórek w postaci tekstu. Pozostała część zapytania wykonywana jest osobno dla każdego wiersza.

Zawartość `groups.csv` zaczyna się od:

```csv
id,weekday,number,pnp,capacity,start_time,end_time
131f00c2-a504-550e-8117-167bd6218535,3,1,NP,120,13:15:00,15:00:00
74e99473-12fb-5919-9992-db58d514944b,3,1,P,120,13:15:00,15:00:00
f1421862-5912-57ee-a1d6-cb357169c3fc,1,1,ALL,120,15:15:00,16:55:00
3e1d2221-1124-533d-8e5b-cd97e997453d,4,1,ALL,16,17:05:00,19:40:00
```

*Fragment pliku wejściowego `import/nodes/groups.csv`*

Plik zawiera więc wszystkie nazwane kolumny konieczne do utworzenia grupy zajęciowej.

Instrukcja `MERGE (g:Group {id: row.id})` szuka węzła z etykietą `Group`, którego właściwość `id` jest równa wartości kolumny `id` w bieżącym wierszu. Jeśli taki węzeł już istnieje, zostaje przypisany do zmiennej `g`, a jeśli nie, instrukcja go tworzy i dopiero wtedy przypisuje.

Następnie blok instrukcji `SET` ustawia pozostałe właściwości węzła na wartości z pliku. Dzięki temu, jeśli dane w plikach .csv ulegną zmianie, węzły zostaną zaktualizowane przy ponownej inicjalizacji. Zawartość pliku jest odczytywana jako tekst, zatem zapisanie wartości jako czasu lub liczby całkowitej wymaga wywołania wbudowanych funkcji, takich jak `localtime()` bądź `toInteger()`.

Na koniec instrukcja zamyka się średnikiem, który oddziela ją od kolejnej instrukcji w pliku. Skrypt `init_db.py` wykonuje wszystkie instrukcje z plików `nodes.cypher` i `edges.cypher` w jednej jawnej transakcji (5.1.4). Błąd w dowolnej z nich wycofuje również zmiany wprowadzone przez instrukcje wcześniejsze, więc import wykonuje się w całości albo wcale. Użycie `MERGE` zamiast `CREATE` pozwala z kolei powtarzać import przy każdym uruchomieniu środowiska bez tworzenia duplikatów; sprawdzenie istnienia węzła korzysta z indeksu klucza, a krawędzi – z listy krawędzi znalezionego już węzła, więc nie wydłuża istotnie importu (7.8.3).

Pojedyncze zapytanie można by uzyskać również przez usunięcie średników. Nie jest to jednak sposób dobry. Wszystkie polecenia stałyby się wtedy jednym zapytaniem, w którym kolejne `LOAD CSV` wykonuje się osobno dla każdego wiersza poprzedniego pliku – dla 3 kierunków i 11 planów studiów zapytanie przetwarza 33 wiersze zamiast 14. Ponowne użycie nazwy `row` nie powoduje przy tym jawnego błędu, ale tworzy zachowanie nieoczekiwane. Zmienna nadal wskazuje na wiersz pierwszego pliku. W efekcie poniższe zapytanie próbuje utworzyć plan studiów z identyfikatorem kierunku i bez roku naboru:

```cypher
LOAD CSV WITH HEADERS FROM "file:///nodes/programmes.csv" AS row
MERGE (p:Programme {id: row.id})
SET p.name = row.name

LOAD CSV WITH HEADERS FROM "file:///nodes/curriculums.csv" AS row
MERGE (c:Curriculum {id: row.id})
SET c.intake_year = row.intake_year;
```

*Błędne połączenie dwóch instrukcji `LOAD CSV` ze wspólną zmienną `row`*

Zatrzymuje je dopiero ograniczenie typu grafu, wymagające istnienia właściwości `intake_year`:

```
22N77: data exception - property presence verification failed. NODE (563) with label 'Curriculum' must have the following properties: `intake_year`.
```

*Komunikat błędu `22N77` wywołany brakiem właściwości `intake_year`*

Bez zdefiniowanego typu grafu zapytanie zakończyłoby się powodzeniem i zapisało w bazie błędne węzły. Rozwiązaniem mogłoby być nazywanie każdej zmiennej odpowiadającej plikowi .csv w inny sposób, czyli jeden `row` importujący grupę nazywałby się `g_row`, dla cyklu akademickiego `ac_row` i tak dalej, zachowując unikatowość dla każdego pliku. Chociaż to działa, to jest bardzo niewygodne i nieeleganckie. 

W podobny sposób przebiega import większości pozostałych węzłów. Wyjątek stanowią węzły dotyczące nauczycieli i studentów. Wynika to z tego, że każda z tych osób na pewno jest osobą (`Person`), ale jednocześnie może być użytkownikiem (`User`). W plikach .csv przechowywane są wszystkie informacje na temat ludzi, wraz z tymi opcjonalnymi. 

```cypher
LOAD CSV WITH HEADERS FROM "file:///nodes/students.csv" AS row
MERGE (st:Student:Person {idx: row.idx})
SET st.name = row.name, st.surname = row.surname,
    st.phone = row.phone, st.photo = nullif(row.photo, ""),
    st.joined = datetime(row.joined)
CALL (row, st) {
    WHEN row.email <> "" THEN {
        SET st:User, st.email = row.email, st.passwd_hash = row.passwd_hash
    }
};
```

*Import węzłów `Student` z warunkowym nadawaniem etykiety `User` (`nodes.cypher`)*

Początek instrukcji jest podobny, jak wcześniej - do zmiennej `row` są po kolei ładowane wszystkie wiersze z nagłówkami określającymi klucze w mapie. 

```csv
idx,name,surname,phone,photo,joined,email,passwd_hash
285903,Maja,Król,607216739,,2025-10-01T00:00:00+02:00,285903@student.pwr.edu.pl,$2bHIDDEN
285904,Filip,Wieczorek,610000007,285904.jpg,2025-10-01T00:00:00+02:00,,
283501,Aleksandra,Jabłońska,605126225,,2024-10-01T00:00:00+02:00,283501@student.pwr.edu.pl,$2HIDDEN
```

*Fragment pliku wejściowego `import/nodes/students.csv`*

W przykładowym fragmencie pliku widać, że nie każdy student ma zdjęcie, a przede wszystkim nie każdy student ma adres e-mail i skrót hasła. Bez danych do logowania nie da się utworzyć etykiety `User`. 

Podobnie jak wcześniej, instrukcja `MERGE` szuka węzła `Student`, jednocześnie `Person`, o wartości `idx` równej tej z `row`.  Jeśli taki istnieje, to przypisuje go do `st`. Jeśli nie, to go tworzy z tymi dwoma etykietami i wtedy przypisuje. Wymagane właściwości, a także opcjonalna właściwość `photo`, są ustawiane w instrukcji `SET`.

Na uwagę zasługuje podzapytanie `CALL (row, st) { ... }`, któremu przekazywane są zmienne `row` i `st`. Wewnątrz niego znajduje się zapytanie warunkowe `WHEN ... THEN`, dostępne w wersji Cypher 25 [CYTOWANIE: https://neo4j.com/docs/cypher-manual/current/queries/composed-queries/conditional-queries/]. Sprawdza ono, czy e-mail jest ustawiony, a jeśli jest, to przypisuje studentowi etykietę `User`, wraz z którą obowiązkowo ustawia właściwości `email` i `passwd_hash`. Gdy warunek nie jest spełniony, to nie dzieje się nic - węzeł pozostaje jedynie studentem, bez etykiety `User`.

Bardzo podobny wzorzec jest wykorzystywany w imporcie nauczycieli (`Teacher`). Podzapytanie do ustawiania etykiety `User` wygląda tak samo, różni się jedynie nazwą przekazywanej zmiennej – zamiast `CALL (row, st)` widnieje `CALL (row, t)`, odpowiednio dla węzła prowadzącego.

5.3.3 Import krawędzi
Mając węzły należy je ze sobą połączyć. Służą ku temu krawędzie, również przechowywane w plikach .csv. Prawie każdy z nich przechowuje jedynie identyfikatory odpowiednich węzłów, które mają być ze sobą połączone. Przykładem jest `curriculum_terms.csv`, który odpowiada za krawędź `HAS_TERM`

```csv
curriculum_id,term_id
69fa951f-504c-5034-ad7c-e301998a6017,f66570ad-4751-5f8e-9f5a-231975f69cd7
69fa951f-504c-5034-ad7c-e301998a6017,f6af6573-d17f-57c7-a4f2-68e6e089b100
69fa951f-504c-5034-ad7c-e301998a6017,11bf9d83-0f5a-56b2-b99b-3f706379192e
```

*Fragment pliku wejściowego `import/edges/curriculum_terms.csv`*

Krawędź jest tworzona poprzez instrukcję Cypher, w której szukane są węzły odpowiedniego typu o danym id, a następnie jest tworzona wybrana krawędź między nimi, po kolei dla każdego wiersza pliku .csv:

```cypher
LOAD CSV WITH HEADERS FROM "file:///edges/curriculum_terms.csv" AS row
MATCH (c:Curriculum {id: row.curriculum_id})
MATCH (ct:CurriculumTerm {id: row.term_id})
MERGE (c)-[:HAS_TERM]->(ct);
```

*Import krawędzi `HAS_TERM` (`edges.cypher`)*

Jedną z krawędzi, które wymagały dodatkowej obsługi, jest `REGISTERED_IN`, która dodatkowo przechowuje właściwość `registered_at`, odczytywaną z dokumentu. Drugą taką specjalną zależnością okazało się połączenie przedmiotu, instancji przedmiotu i cyklu akademickiego. Ponieważ `SubjectInstance` nie ma trwałego identyfikatora, jest importowane jako "krok" pomiędzy przedmiotem a cyklem akademickim. 

```cypher
LOAD CSV WITH HEADERS FROM "file:///edges/instance_group_types.csv" AS row
MATCH (:Subject {code: row.subject_code})<-[:INSTANCE_OF]-(si:SubjectInstance)-[:OFFERED_IN]->(:AcademicCycle {id: row.cycle_id})
MATCH (gt:GroupType {id: row.group_type_id})
MERGE (si)-[:HAS_TYPE]->(gt);
```

*Import krawędzi `HAS_TYPE` z wyszukaniem węzła `SubjectInstance` (`edges.cypher`)*

Osobnego traktowania wymagało też wyszukiwanie studentów i prowadzących. Klucz `idx` jest zdefiniowany dla etykiety `Person` (5.3.1), a nie dla `Student` czy `Teacher`. W zapytaniach API planista korzysta z indeksu `Person(idx)` także przy dopasowaniu `(:Student {idx: ...})`, jednak w instrukcjach importu, które tworzą krawędzie (`MERGE`), wybierał przegląd wszystkich węzłów etykiety. Koszt utworzenia każdej krawędzi rósł więc z liczbą studentów, a czas importu kwadratowo z rozmiarem danych (7.8.3). Rozwiązaniem jest jawne wskazanie indeksu:

```cypher
LOAD CSV WITH HEADERS FROM "file:///edges/student_registered.csv" AS row
MATCH (st:Person:Student {idx: row.student_idx}) USING INDEX st:Person(idx)
MATCH (g:Group {id: row.group_id})
MERGE (st)-[r:REGISTERED_IN]->(g)
...
```

*Wyszukanie studenta z jawnym użyciem indeksu `Person(idx)` (`edges.cypher`)*

5.3.4 Udany import
Po zakończeniu działania serwisu `init`, bazę danych można obejrzeć chociażby poprzez konsolę Neo4j wystawioną po HTTPS. Z poziomu konta administracyjnego `neo4j` wygląda to następująco:

![[Pasted image 20261116175212.png]]

*Konsola Neo4j z zaimportowanymi elementami*

Możliwe jest również zalogowanie się na konto użytkowe `app` z ograniczonymi uprawnieniami. Jak widać, nie jest możliwe z tego konta między innymi stworzenie węzła o etykiecie, która nie została zdefiniowana w schemacie lub nie ma jej jeszcze w bazie danych. Dla porównania, z konta `neo4j` jest to jak najbardziej możliwe. Broni to przed przyszłymi sytuacjami, w których literówka w kwerendzie po stronie aplikacji może spowodować zapis danych w złym miejscu, który się wykona bez ostrzeżenia.

![[Pasted image 20261116175608.png]]

*Udane stworzenie węzła z etykietą `Professor` jako użytkownik neo4j*

![[Pasted image 20261116175715.png]]

*Nieudana próba stworzenia węzła z etykietą `Janitor` jako użytkownik app*

Wszystkie zaimportowane węzły i krawędzie są widoczne po użyciu funkcji `db.schema.visualization()`. Niestety, przez wieloetykietowość ten wykres jest mało czytelny.

![[visualisation(1)-cropped.svg]]

*Wynik funkcji `CALL db.schema.visualization()`*

5.4 Dokumentacja

Katalog `endpoint_schema/` zawiera dokumentację punktów końcowych API: dozwolone role, kształt żądań i odpowiedzi oraz wykonywane zapytania bazodanowe. Każdy plik odpowiada roli, która może wykonywać dane zapytanie.

Ponadto API generuje interaktywną dokumentację w standardzie OpenAPI [CYTOWANIE: https://fastapi.tiangolo.com/reference/openapi/docs/], na podstawie tych samych modeli, które służą do walidacji. Jest ona dostępna pod adresem `/api/docs`.

5.4.1 Konwencje

Każdy punkt końcowy jest opisany według tego samego schematu: kto może go wywołać (**Allowed**), kształt żądania (**Request**), kształt odpowiedzi (**Response**) oraz zapytania Cypher, które wykonuje (**Query**). `X?` oznacza pole opcjonalne lub mogące przyjąć wartość `null`, a `List[X]` tablicę JSON. Każdy punkt końcowy poza `POST /login` wymaga nagłówka `Authorization: Bearer <token>`. Ścieżki podawane są względem prefiksu `/api`, np. `GET /subjects` jest dostępny pod adresem `/api/subjects`.

Poniżej opisano wybrane punkty końcowe wraz z zapytaniami Cypher, które wykonują. Przykładowe żądania i odpowiedzi zawierają pliki w katalogu `endpoint_schema/`. Zapis do grupy i wystawianie oceny omówiono w podrozdziale 5.5, razem z ich implementacją.

5.4.2 Logowanie - POST /login

Jedyny punkt końcowy dostępny bez tokenu. Przyjmuje adres e-mail i hasło, a w odpowiedzi zwraca token oraz listę ról użytkownika.

```cypher
MATCH (u:User {email: $email})
RETURN
  u.passwd_hash AS passwd_hash,
  u.email AS email,
  u.idx AS idx,
  u:Inactive AS inactive,
  u:Admin AS admin,
  u:Teacher AS teacher,
  u:Student AS student
```

*Zapytanie Cypher dla punktu końcowego `POST /login`*

Na tym zapytaniu dobrze widać zaletę wieloetykietowości. Role są po prostu etykietami tego samego węzła. Wyrażenia `u:Admin`, `u:Teacher` itd. zwracają wartość logiczną, więc jednym odczytem węzła uzyskiwany jest komplet informacji o uprawnieniach. Podobnie działa blokada konta - dezaktywowany użytkownik dostaje etykietę `Inactive`.

5.4.3 Katalog przedmiotów - GET /subjects

Zwraca listę przedmiotów w postaci siatki: wiersze to przedmioty, a kolumny to cykle akademickie. Każda komórka mówi, czy przedmiot jest w danym cyklu prowadzony, ile ma grup i czy trwają na niego zapisy. Opcjonalne parametry `name` i `code` zawężają wyniki do przedmiotów, których nazwa lub kod zawiera podany tekst.

Serwer wykonuje dwa zapytania. Pierwsze pobiera wszystkie cykle akademickie, które po posortowaniu chronologicznym stają się kolumnami siatki. Ich identyfikatory trafiają do drugiego zapytania jako lista `$cycle_ids`, a ono zwraca gotowe wiersze:

```cypher
// 1. Kolumny: wszystkie cykle akademickie (sortowane przez serwer)
MATCH (ac:AcademicCycle)
RETURN ac.id AS id, ac.year AS year, ac.season AS season

// 2. Wiersze: przedmioty z wydziałami i komórką dla każdego cyklu
MATCH (su:Subject)
WHERE ($name IS NULL OR toLower(su.name) CONTAINS toLower($name))
  AND ($code IS NULL OR toLower(su.code) CONTAINS toLower($code))
RETURN
  su.code AS code,
  su.name AS name,
  su.ects AS ects,
  COLLECT {
    MATCH (su)<-[:INCLUDES]-(:CurriculumTerm)<-[:HAS_TERM]-(:Curriculum)<-[:HAS_CURRICULUM]-(:Programme)-[:OFFERED_BY]->(fa:Faculty)
    RETURN DISTINCT fa.name
  } AS faculties,
  [cycle_id IN $cycle_ids | {
    offered: EXISTS {
      (su)<-[:INCLUDES]-(:CurriculumTerm)-[:TAUGHT_IN]->(:AcademicCycle {id: cycle_id})
    },
    group_count: COUNT {
      (su)<-[:INSTANCE_OF]-(si:SubjectInstance)-[:OFFERED_IN]->(:AcademicCycle {id: cycle_id}),
      (si)-[:HAS_TYPE]->(:GroupType)<-[:OF_TYPE]-(:Group)
    },
    registration_open: EXISTS {
      MATCH (su)<-[:INSTANCE_OF]-(si:SubjectInstance)-[:OFFERED_IN]->(:AcademicCycle {id: cycle_id}),
            (si)-[:HAS_TYPE]->(:GroupType)<-[:OF_TYPE]-(:Group)<-[:OPENS]-(reg:Registration)-[:HAS_TURN]->(rt:RegistrationTurn)
      WITH reg,
           min(datetime({date: rt.date, time: rt.start_time, timezone: 'Europe/Warsaw'})) AS opens,
           max(datetime({date: rt.date, time: rt.end_time, timezone: 'Europe/Warsaw'})) AS closes
      WHERE opens <= datetime() < closes
    }
  }] AS cycles
ORDER BY su.name
```

*Zapytania Cypher dla punktu końcowego `GET /subjects`*

Warunek `$name IS NULL OR ...` sprawia, że to samo zapytanie obsługuje zarówno wyszukiwanie z filtrem, jak i bez niego. Podzapytanie `COLLECT` przechodzi ścieżką od przedmiotu, przez semestr programu i program studiów, aż do wydziału.

Komórki siatki powstają w wyrażeniu listowym `[cycle_id IN $cycle_ids | { ... }]`, w kolejności zgodnej z kolumnami. Każde pole komórki to osobne pytanie o istnienie ścieżki w grafie: `EXISTS { ... }` sprawdza, czy taka ścieżka istnieje, a `COUNT { ... }` liczy jej wystąpienia. Przedmiot jest oferowany w cyklu, jeśli należy do semestru programu studiów realizowanego w tym cyklu. Zapisy są otwarte, jeśli bieżący moment mieści się w okresie zapisów (`Registration`) obejmujących którąkolwiek grupę przedmiotu z tego cyklu. Zapisy nie mają własnych dat, więc ich okres trwa od początku pierwszej do końca ostatniej tury. Godziny tur są czasem lokalnym, dlatego do porównania z bieżącym momentem łączy się je z datą tury w strefie czasowej uczelni (`Europe/Warsaw`). Wzorzec zawierający przecinek opisuje dwie ścieżki, które muszą być spełnione jednocześnie i mają wspólny węzeł `si`.

5.4.4 Lista grup w zapisach - GET /me/registrations/{registration_id}/groups
Punkt końcowy studenta, wywoływany po wybraniu przedmiotu w trakcie zapisów. Zwraca wszystkie grupy tego przedmiotu otwarte przez dane zapisy, wraz z liczbą zajętych miejsc i informacją, czy student już jest w danej grupie zapisany. Zapisy są wskazywane w ścieżce, a przedmiot w parametrze zapytania, ponieważ jedynie zawęża listę grup otwartych przez zapisy.

Najpierw sprawdzane jest, czy student ma przydzieloną turę w tych zapisach (5.5.7) – w przeciwnym razie API zwraca kod 403. Następnie pobierane są same grupy:

```cypher
MATCH (st:Student {idx: $student_idx})
MATCH (reg:Registration {id: $registration_id})-[:OPENS]->(g:Group)
MATCH (g)-[:OF_TYPE]->(gt:GroupType)<-[:HAS_TYPE]-(:SubjectInstance)-[:INSTANCE_OF]->(:Subject {code: $subject_code})
OPTIONAL MATCH (g)-[:IN_ROOM]->(r:Room)
OPTIONAL MATCH (t:Teacher)-[:TEACHES]->(g)
OPTIONAL MATCH (st)-[mine:REGISTERED_IN]->(g)
RETURN
  g.id AS id,
  gt.g_type AS g_type,
  g.number AS number,
  g.weekday AS weekday,
  g.start_time AS start,
  g.end_time AS end,
  g.capacity AS capacity,
  size([(g)<-[:REGISTERED_IN]-() | 1]) AS filled,
  r.building + " " + r.room_num AS room,
  t.name + " " + t.surname AS teacher,
  mine IS NOT NULL AS registered
ORDER BY gt.g_type, g.number
```

*Zapytanie Cypher dla punktu końcowego `GET /me/registrations/{registration_id}/groups`*

Sala i prowadzący są dołączane przez `OPTIONAL MATCH`, ponieważ nowo utworzona grupa może ich jeszcze nie mieć - wtedy odpowiednie pola mają wartość `null`, a grupa nadal jest zwracana. Liczbę zajętych miejsc wyznacza się dynamicznie jako liczbę krawędzi `REGISTERED_IN` wchodzących do grupy, co eliminuje ryzyko utraty spójności między oddzielnym licznikiem a faktycznym stanem zapisów.

5.4.5 Dodanie studenta - POST /admin/students
Punkt końcowy administratora, tworzący nowego studenta i od razu przypisujący go do semestru programu studiów.

Pole `term_id` jest opcjonalne. Bez niego student trafia na pierwszy semestr najnowszego programu (`Curriculum`) danego kierunku. Podanie go pozwala zapisać studenta na dowolny semestr, co przydaje się przy przeniesieniach z innej uczelni. Najpierw zapytanie wyznacza semestry kierunku pasujące do żądania. API wybiera pierwszy z nich albo odrzuca żądanie: z kodem 404, gdy kierunek nie istnieje, z kodem 409, gdy kierunek nie ma jeszcze programu lub pierwszego semestru, oraz z kodem 422, gdy podany semestr nie należy do kierunku. Dopiero potem tworzony jest węzeł studenta wraz z krawędzią `ENROLLED` do wybranego semestru.

Udane utworzenie zwraca kod 201 z nagłówkiem `Location: /api/students/{idx}`, czyli adresem, pod którym można od razu odczytać nowego studenta. Zajęty numer indeksu zostaje wykryty przez ograniczenie `idx IS KEY` w bazie i zwrócony jako 409.

Student jest tworzony bez etykiety `User`, czyli bez możliwości logowania - konto nadaje się osobnym punktem końcowym `POST /admin/users`.

5.5 API

API odbiera żądanie na wybranym punkcie końcowym, weryfikuje token i uprawnienia użytkownika, otwiera sesję bazy danych, wykonuje zapytanie w języku Cypher, a jego wynik przekształca do oczekiwanego kształtu i zwraca klientowi. Poprawność danych wejściowych i format odpowiedzi wyznaczają modele Pydantic. Zapytania są wykonywane bezpośrednio przez oficjalny, asynchroniczny sterownik Neo4j dla języka Python [CYTOWANIE: https://neo4j.com/docs/api/python-driver/current/].

5.5.1 Struktura aplikacji

Podział katalogu `app/` na modele (`schemas/`), backend grafowy (`graph_backend/`) i backend relacyjny (`relation_backend/`) opisano w 5.2. Backend grafowy dzieli się dalej na routery pogrupowane według ról (`routers/`), uwierzytelnianie i autoryzację (`auth/`) oraz moduły pomocnicze.

W pliku `app/__init__.py` jest tworzony obiekt `app`, instancja klasy `FastAPI`. To do niego podłączane są wszystkie elementy backendu: punkty końcowe, obsługa błędów i obsługa cyklu życia aplikacji. Ten sam obiekt wykorzystuje polecenie `uvicorn app:app` z 5.1.5.

5.5.2 Inicjalizacja i błędy

Do konstruktora `FastAPI` w pliku `app/__init__.py` przekazywane są tytuł, funkcja `lifespan` oraz ścieżki do automatycznie generowanej dokumentacji.

Funkcja `lifespan` obejmuje cały czas działania aplikacji [CYTOWANIE: https://fastapi.tiangolo.com/advanced/events/#lifespan]. FastAPI wymaga, by była ona asynchronicznym menedżerem kontekstu, a staje się nim poprzez dekorator `@asynccontextmanager`. Kod przed `yield` wykonuje się raz, przy uruchomieniu, a kod po `yield` też raz, przy zamknięciu. Pomiędzy nimi funkcja jest wstrzymana na słowie `yield`, aplikacja przez ten czas obsługuje żądania. Obie wywoływane funkcje są asynchroniczne, dlatego poprzedza je `await`. Wywołanie funkcji asynchronicznej zwraca jedynie obiekt korutyny (ang. *coroutine*), jej kod wykonuje się dopiero po użyciu `await`.

![[Pasted image 20261117184011.png]]

*Dokumentacja metody `verify_connectivity` [CYTOWANIE: https://neo4j.com/docs/api/python-driver/current/async_api.html#neo4j.AsyncDriver.verify_connectivity]*

Przy starcie `verify_connectivity()` sprawdza, czy sterownik może połączyć się z bazą i zalogować. Jeśli baza jest niedostępna, aplikacja nie uruchamia się wcale. Przy zamknięciu `close_driver()` zamyka sterownik wraz z jego pulą połączeń. Analogiczne funkcje `open_pool()` i `close_pool()` obsługują pulę połączeń backendu relacyjnego (6.4).

Na poziomie całej aplikacji są rejestrowane procedury obsługi wyjątków (ang. *exception handlers*). Określają one, jaki kod statusu i jaki komunikat w formacie JSON zwrócić, gdy podczas obsługi żądania zostanie zgłoszony wyjątek danego typu [CYTOWANIE: https://fastapi.tiangolo.com/tutorial/handling-errors/#install-custom-exception-handlers]. Zdefiniowano je w funkcji `register_exception_handlers()` w pliku `errors.py`.

Dzięki temu punkty końcowe nie muszą same przechwytywać błędów bazy danych. Naruszenie ograniczenia ze schematu (5.3.1), np. duplikat klucza, kończy się kodem 409, a odrzucenie zapytania przez bazę, np. z powodu niepoprawnej daty, kodem 400. `ConstraintError` dziedziczy po `ClientError`, a ten po `Neo4jError`. Pozostałe błędy – inne błędy bazy, niezgodność odpowiedzi z modelem Pydantic i nieobsłużone wyjątki – kończą się kodem 500. Ich szczegóły trafiają do logów serwera, a klient otrzymuje ogólny komunikat.

W tym samym pliku zdefiniowano funkcje pomocnicze tworzące `HTTPException` dla najczęstszych kodów: `unauthorized` (401), `forbidden` (403), `not_found` (404), `conflict` (409) i `invalid` (422). Punkty końcowe zgłaszają błędy wyłącznie przez nie, co pozwala ustandaryzować odpowiedzi.

Na końcu `app/__init__.py` podłączane są routery z katalogu `routers/` (5.5.1), pogrupowane według ról użytkowników. Każdy jest dołączany z argumentem `prefix=API_PREFIX`, więc wszystkie punkty końcowe zaczynają się od `/api`. Routery backendu relacyjnego otrzymują prefiks `/api/rel` (4.2).

5.5.3 Połączenie z bazą danych

Baza danych Neo4j wykorzystywana przez aplikację komunikuje się z aplikacją przez asynchroniczny sterownik zdefiniowany w `graph_backend/database.py`. Pojedyncza instancja `AsyncGraphDatabase.driver` jest współdzielona w całej aplikacji. Zgodnie z testami wykonanymi na potrzeby biblioteki neomodel, asynchroniczny sterownik jest szybszy od zrównoleglonego i o wiele szybszy od szeregowego.  [CYTOWANIE: https://github.com/mariusconjeaud/neomodel-locust]

Konstruktor sterownika przyjmuje URI bazy danych oraz login i hasło użytkownika aplikacji. Wszystkie trzy wartości są odczytywane ze zmiennych środowiskowych ustawianych przez Docker Compose (5.1.5). URI ma schemat `bolt+s`, więc cały ruch między API a bazą jest szyfrowany TLS.

Moduł udostępnia też funkcje `verify_connectivity()` i `close_driver()`, wywoływane w `lifespan` (5.5.2), oraz zależność `get_session()`, przez którą punkty końcowe otrzymują sesję bazy danych.

Funkcja `get_session()` otwiera sesję w bloku `async with`, czyli przez asynchroniczny menedżer kontekstu (ang. *context manager*). Przy wejściu do bloku wywoływana jest metoda `__aenter__()`, która otwiera sesję, a przy wyjściu – `__aexit__()`, która ją zamyka, również wtedy, gdy w bloku wystąpi wyjątek. Wewnątrz bloku funkcja zatrzymuje się na `yield` i przekazuje sesję. Resztą zarządza FastAPI: wstrzykuje sesję do punktu końcowego jako zależność, a po jego zakończeniu wznawia funkcję, która wychodzi z bloku `async with` i zamyka sesję [CYTOWANIE: https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/].

Sesja jest tworzona raz na żądanie. Zgodnie z dokumentacją sterownika, tworzenie sesji jest lekką operacją, ale sesje nie są bezpieczne przy współbieżnym użyciu [CYTOWANIE: https://neo4j.com/docs/api/python-driver/current/async_api.html#asyncsessions-asynctransactions]. Każde żądanie otrzymuje zatem własną sesję, natomiast współdzielona pozostaje pojedyncza instancja sterownika. To on utrzymuje pulę połączeń, z której sesje pobierają połączenie przy pierwszym zapytaniu i do której je oddają przy zamknięciu.

Transakcje są wykorzystywane na dwa sposoby. Pojedyncze wywołanie `session.run()` jest wykonywane jako transakcja automatyczna (ang. *auto-commit*): zapytanie wykonuje się w całości albo wcale. Większość punktów końcowych wykonuje jedno zapytanie, więc to wystarcza. Gdy kilka zapytań musi się udać razem, otwierana jest jawna transakcja i zatwierdzana przez `commit()`. Tak działa m.in. usuwanie roli użytkownika oraz otwarcie zapisów, w którym utworzenie rejestracji, jej tur i powiązań z grupami jest jedną operacją.

Zapytania w transakcji są wykonywane tą samą funkcją `one()` co w sesji (5.5.5), ponieważ sesja i transakcja udostępniają metodę `run()` o tej samej sygnaturze. Jeśli przed `commit()` zostanie zgłoszony wyjątek, `close()` w bloku `finally` wycofuje transakcję i żadna ze zmian nie trafia do bazy. Neo4j zawsze działa na poziomie izolacji *read committed* (ang.), którego nie da się podnieść, dlatego spójność przy współbieżnych żądaniach zapewniają jawne blokady zapisu, opisane w 5.5.10 [CYTOWANIE: https://neo4j.com/docs/operations-manual/current/database-internals/concurrent-data-access/].

5.5.4 Modele danych (schema)

Kształt żądań i odpowiedzi zdefiniowano w katalogu `schemas/` w postaci modeli Pydantic. Pydantic działa w obie strony: dane JSON z żądania zamienia na zwalidowany obiekt Pythona, a wynik zapytania – na odpowiedź JSON. Pliki są podzielone według dziedziny (przedmioty, grupy, opinie itd.), a nazwy modeli stosują konwencję `…Request` dla treści żądania i `…Response` dla odpowiedzi. Kształt odpowiedzi określono dla każdego punktu końcowego zwracającego dane, a kształt żądania – dla każdego, który przyjmuje treść.

Walidacja działa po obu stronach punktu końcowego. Żądanie niezgodne z modelem jest odrzucane z kodem 422, zanim funkcja punktu końcowego zostanie wywołana, więc błędne dane nie docierają do bazy danych. Odpowiedź niezgodna z modelem podanym w `response_model` kończy się kodem 500 (5.5.2), ponieważ sygnalizuje błąd po stronie serwera.

Definiowanie modelu Pydantic polega na stworzeniu klasy dziedziczącej po `BaseModel` i określeniu, jakie pola i jakiego typu ma zawierać. Typ `Optional[X]`, równoważny `X | None`, oznacza, że pole może przyjąć wartość `null`.

Od Pydantic v2 `Optional` nie oznacza jednak, że pole można pominąć. O tym decyduje wyłącznie wartość domyślna: pole `Optional` bez niej jest wymagane, a żądanie, które go nie zawiera, zostaje odrzucone z kodem 422 [CYTOWANIE: https://docs.pydantic.dev/latest/migration/#required-optional-and-nullable-fields]. Dlatego wszystkie pola opcjonalne w projekcie mają jawnie ustawione `= None`, np. `ects: Optional[int] = None` w modelu `SubjectUpsertRequest`.

Ograniczenia wartości pola można określić funkcją `Field()`, działającą podobnie do funkcji `field()` dla klas danych (ang. *dataclasses*). Mimo zapisu po prawej stronie znaku `=`, wartość domyślną określa się w niej dopiero za pomocą argumentów `default` lub `default_factory`.

W modelu `GroupCreateRequest` pole `weekday: int = Field(ge=1, le=7)` dopuszcza jako dzień tygodnia wyłącznie liczby całkowite od 1 do 7, a typ `Literal["P", "NP", "ALL"]` ogranicza pole `pnp` do trzech wartości.

Bardziej złożoną walidację zapewniają własne walidatory. Metoda oznaczona dekoratorami `@field_validator()` i `@classmethod` jest wywoływana dla pól podanych w argumentach dekoratora. Domyślnie metoda uruchamia się po standardowej walidacji typu, więc otrzymuje wartość już przekonwertowaną na typ danych języka Python. 

W projekcie własny walidator sprawdza, czy liczba jest oceną ze skali 2.0, 2.5, …, 5.0. Nie można było użyć `Literal[2.0, 2.5, …]`, ponieważ `Literal` z założenia nie przyjmuje liczb zmiennoprzecinkowych [CYTOWANIE: https://peps.python.org/pep-0586/#illegal-parameters-for-literal-at-type-check-time]. Sama funkcja `check_grade()` znajduje się w osobnym pliku `grades.py`, ponieważ korzystają z niej dwa modele: `OpinionCreateRequest` (ocena prowadzącego w opinii) i `SetGroupGradeRequest` (ocena wystawiana studentowi).

Wystawienie oceny spoza skali, np. 4.2, kończy się odpowiedzią 422. Jej pole `loc` wskazuje pole `grade` w treści żądania, a `msg` zawiera komunikat zgłoszony przez `check_grade()`. Żądanie zostaje odrzucone przed sprawdzeniem, czy grupa i student w ogóle istnieją.

5.5.5 Funkcje współdzielone

Zapytania do bazy danych są wykonywane przez dwie funkcje z pliku `query.py`: `run()` i `one()`. Są to cienkie nakładki (ang. *wrappers*) na metodę `run()` sesji i transakcji sterownika, które poza wykonaniem zapytania zamieniają jego wynik na listę słowników z typami Pythona. Funkcja `one()` korzysta z `run()`, ale zwraca jedynie pierwszy wiersz albo `None`, gdy wynik jest pusty. Jest przeznaczona dla zapytań, które z założenia zwracają najwyżej jeden wiersz. Takich jest w projekcie dużo – w szczególności zapytania kontroli dostępu. Wynik `None` oznacza, że szukany element nie istnieje, co punkty końcowe zamieniają na odpowiedź 404.

Za zamianę typów odpowiada funkcja `native()`. Sterownik zwraca daty i godziny jako własne typy (`neo4j.time.Date`, `neo4j.time.DateTime` itd.), które nie dziedziczą po typach z modułu `datetime`, więc modele Pydantic by ich nie przyjęły, a odpowiedź kończyłaby się błędem 500 (5.5.2). Funkcja przechodzi rekurencyjnie przez listy i słowniki i każdą wartość mającą metodę `to_native()` zamienia na odpowiadający jej typ Pythona.

Metoda `run()` sterownika przyjmuje tekst zapytania oraz jego parametry, przekazywane osobno – jako słownik lub jako argumenty nazwane. Przykładowo zapytanie tworzące wydział, wykonane bezpośrednio przez sterownik, wyglądałoby tak:

```python
result = await session.run(
    """
    CREATE (fa:Faculty {id: $id, name: $name, full_name: $full_name})
    RETURN fa.id AS id, fa.name AS name, fa.full_name AS full_name
    """,
    id=new_id(),
    name=body.name,
    full_name=body.full_name,
)
```

*Zapytanie z `POST /admin/faculties` wykonane bezpośrednio metodą `run()` sterownika*

Zapisy `$id`, `$name` i `$full_name` to parametry zapytania [CYTOWANIE: https://neo4j.com/docs/cypher-manual/current/syntax/parameters/]. Sterownik wysyła do bazy treść zapytania i parametry osobno, a ich podstawienie odbywa się dopiero po stronie bazy, bez wstawiania wartości w tekst kwerendy. Dzięki temu dane od użytkownika nigdy nie stają się częścią kodu zapytania, co chroni przed wstrzykiwaniem kodu Cypher. Tekst zapytania pozostaje przy tym stały, więc baza może ponownie wykorzystać raz przygotowany plan jego wykonania. Dane od użytkownika trafiają do zapytań w projekcie wyłącznie w ten sposób.

Python 3.14 wprowadził szablony tekstowe (ang. *template strings*, t-stringi), które pozwalają zapisać zapytanie podobnie do f-stringa, a mimo to przekazać wartości osobno. Biblioteka psycopg, służąca do łączenia z bazą PostgreSQL, już je obsługuje [CYTOWANIE: https://www.psycopg.org/psycopg3/docs/basic/tstrings.html], natomiast sterownik Neo4j w wykorzystanej wersji 6.2.0 jeszcze tej składni nie wspiera. W obu przypadkach mechanizm separacji parametrów zapewnia taki sam poziom bezpieczeństwa, a różnica dotyczy jedynie zwięzłości zapisu.

Ostatnią funkcją z `query.py` jest `new_id()`, która generuje losowy identyfikator funkcją `uuid4()` i od razu zamienia go na napis. Neo4j nie ma typu UUID, dlatego identyfikatory są w schemacie zadeklarowane jako `STRING`. Powody wyboru UUID zamiast identyfikatorów liczbowych omówiono w 5.3.1.

Pozostałe funkcje współdzielone wynikają z logiki dziedziny:
- `teacher_groups()` (`teaching.py`) – zapytanie zwracające grupy prowadzącego, wykorzystywane przez trzy punkty końcowe: `/me/groups`, `/teachers/{idx}` oraz `/teachers/{idx}/groups`. Dzięki temu lista grup prowadzącego ma wszędzie ten sam kształt i kolejność.
- `cycle_sort_key()` (`cycles.py`) – klucz sortowania cykli akademickich: najpierw rok, a w jego obrębie semestr zimowy przed letnim. Zwykłe sortowanie alfabetyczne dałoby odwrotną kolejność, ponieważ „L” poprzedza „Z”.
- `average_grade()` (`grades.py`) – średnia ocen studenta ważona punktami ECTS, liczona z ostatniego w pełni ocenionego podejścia do każdego przedmiotu. Do wyboru ostatniego podejścia wykorzystuje `cycle_sort_key()`. Ocena z przedmiotu w danym podejściu jest średnią ważoną ocen z form zajęć, chyba że którakolwiek z nich jest niższa niż 3.0. Wtedy ocena z przedmiotu wynosi 2.0 (3.2), ponieważ średnia ważona pozwalałaby zaliczyć przedmiot mimo oceny negatywnej, np. 5.0 z wykładu o wadze 0,7 i 2.0 z laboratorium dawałyby 4.1. Średnia jest liczona w Pythonie, ponieważ wybór podejścia i uśrednianie ocen z kilku grup tego samego typu byłyby w Cypher znacznie mniej czytelne.

5.5.6 Uwierzytelnianie

Uwierzytelnianie zrealizowano w pliku `graph_backend/auth/deps.py`. Zawiera on funkcje obsługi haseł i tokenów, z których korzystają punkt końcowy `POST /login` (5.4.2) oraz tworzenie kont w module administratora, a także zależność `get_caller()`, przez którą wszystkie pozostałe punkty końcowe ustalają, kto wysłał żądanie. Założenia tego mechanizmu, w tym powody wyboru tokenów JWT, opisano w 4.4.1.

Hasła są obsługiwane przez bibliotekę bcrypt w wersji 5.0.0.

Funkcja `hash_password()` wywołuje `bcrypt.hashpw()`, która przyjmuje jako argumenty surowe hasło i sól, a `verify_password()` sprawdza hasło funkcją `bcrypt.checkpw()`. Funkcja `gensalt()` przy każdym wywołaniu losuje nową sól i ustala współczynnik kosztu (ang. *salt rounds*), domyślnie 12, co oznacza 2^12 rund rozwinięcia klucza. Wynikiem `hashpw()` jest napis w postaci:

```
$2b$12$.lG2u6PuGdo7F5TdxxeEDuTQiGb/6nF5zkc04Qq9sf0SfD0egQsmq
```

*Skrót hasła konta administratora z danych początkowych*

Kolejne fragmenty oddzielone znakiem `$` to wariant algorytmu (`2b`), koszt (`12`), a następnie 22 znaki soli i 31 znaków właściwego skrótu [CYTOWANIE: https://www.usenix.org/legacy/events/usenix99/provos/provos.pdf]. Skrót zawiera więc wszystko, co jest potrzebne do jego weryfikacji poprzez odtworzenie.

Koszt obliczeniowy jest wyraźnie odczuwalny: na maszynie testowej (7.1) żądanie `POST /login` z istniejącym adresem trwa ok. 184 ms (7.2.2), z czego niemal cały czas zajmuje bcrypt. Dla pojedynczego logowania jest to niezauważalne, ale atakującemu, który zdobyłby skróty z bazy, ogranicza liczbę sprawdzanych haseł do kilku na sekundę na jeden rdzeń procesora.

Algorytm bcrypt uwzględnia wyłącznie pierwsze 72 bajty hasła. Wcześniejsze wersje biblioteki obcinały dłuższe hasła bez ostrzeżenia, zgodnie z oryginalną implementacją zaproponowaną przez OpenBSD. Od wersji 5.0.0 zgłaszany jest wyjątek `ValueError` [CYTOWANIE: https://github.com/pyca/bcrypt/blob/main/CHANGELOG.rst].

Przy zakładaniu konta wyjątek ten kończył się początkowo błędem 500, ponieważ `hash_password()` go nie przechwytywał. Dlatego model `AssignUserRequest` ma walidator, który odrzuca hasła dłuższe niż 72 bajty z kodem 422, zanim punkt końcowy zostanie wywołany (5.5.4).

```python
MAX_PASSWORD_BYTES = 72

class AssignUserRequest(BaseModel):
    email: str
    passwd: str
    idx: str

    @field_validator("passwd")
    @classmethod
    def passwd_fits_bcrypt(cls, value: str) -> str:
        if len(value.encode()) > MAX_PASSWORD_BYTES:
            raise ValueError(f"password cannot be longer than {MAX_PASSWORD_BYTES} bytes")
        return value
```

*Walidacja długości hasła przy zakładaniu konta (`schemas/auth.py`)*

Punkt końcowy `POST /login` pobiera węzeł użytkownika zapytaniem z 5.4.2, a następnie sprawdza kolejne warunki z 4.4.1.

```python
@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)) -> LoginResponse:
    row = await one(session, _LOGIN, email=body.email)
    password_hash = row["passwd_hash"] if row is not None else DUMMY_PASSWORD_HASH
    password_ok = verify_password(body.password, password_hash)
    if row is None or not password_ok:
        raise unauthorized("Invalid email or password")
    if row["inactive"]:
        raise forbidden("Account inactive")
    roles = roles_from_flags(row["admin"], row["teacher"], row["student"])
    if not roles:
        raise forbidden("Account has no role")
    caller = Caller(email=row["email"], idx=row["idx"], roles=roles)
    return LoginResponse(
        email=caller.email,
        idx=caller.idx,
        roles=list(caller.roles),
        token=create_token(caller),
    )
```

*Punkt końcowy logowania (`routers/public.py`)*

Brak użytkownika i błędne hasło obsługuje ten sam warunek, z tym samym komunikatem. Sama treść odpowiedzi nie wystarcza jednak, żeby ukryć istnienie konta. W jednej z pierwszych implementacji, gdy użytkownik nie istniał, warunek kończył się przed wywołaniem `verify_password()`, więc bcrypt się nie wykonywał.

Odpowiedź dla nieistniejącego konta przychodziła przez to wyraźnie szybciej niż dla istniejącego konta z błędnym hasłem, co umożliwiało atak czasowy (2.2) i sprawdzanie istnienia kont [CYTOWANIE: OWASP Authentication Cheat Sheet, https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html#authentication-responses]. Pomiary przed poprawką i po niej przedstawiono w 7.2.2.

Obecnie, gdy użytkownik nie istnieje, hasło jest sprawdzane względem `DUMMY_PASSWORD_HASH`, czyli skrótu losowego hasła, wyliczanego raz przy starcie aplikacji z tym samym kosztem co prawdziwe skróty. bcrypt wykonuje się zawsze, a wynik i tak jest odrzucany warunkiem `row is None`.

```python
DUMMY_PASSWORD_HASH = hash_password(os.urandom(16).hex())
```

*Skrót zastępczy (`auth/deps.py`)*

Stan konta i role są sprawdzane dopiero po poprawnej weryfikacji hasła, więc odpowiedź 403 („konto nieaktywne” albo „brak roli”) otrzymuje tylko ktoś, kto zna hasło. Funkcja `roles_from_flags()` zamienia trzy wartości logiczne z zapytania na krotkę nazw ról: `Admin`, `Teacher`, `Student`.

```python
def create_token(caller: Caller) -> str:
    payload = {
        "sub": caller.email,
        "idx": caller.idx,
        "roles": list(caller.roles),
        "iat": time.time(),
        "exp": datetime.now(timezone.utc) + timedelta(hours=12),
    }
    return jwt.encode(payload, _secret, algorithm=_algorithm)
```

*Tworzenie tokenu*

Token JWT (2.2) jest tworzony biblioteką PyJWT i zawiera pięć roszczeń: standardowe `sub` (adres e-mail), `iat` (moment wydania z dokładnością do ułamka sekundy, wykorzystywany przy unieważnianiu tokenów) i `exp` (ważność 12 godzin) [CYTOWANIE: RFC 7519, sekcja 4.1] oraz dwa roszczenia prywatne specyficzne dla platformy: `idx` i `roles`.

Podpis jest wyznaczany symetrycznym algorytmem HS256 (HMAC-SHA256) [CYTOWANIE: RFC 7518, sekcja 3.2] z użyciem klucza ze zmiennej środowiskowej `JWT_SECRET` (5.1.5) – wystarczy klucz symetryczny, ponieważ token wydaje i weryfikuje wyłącznie to samo API. Zgodnie z budową JWT (2.2) nagłówek i treść są jawne po zdekodowaniu z `base64url`, a podpis chroni wyłącznie ich integralność (np. przed dopisaniem roli `Admin`).

![[Pasted image 20261118175909.png]]

*Token JWT zdekodowany przy pomocy https://www.jwt.io/*

Każdy punkt końcowy poza `POST /login` wymaga tokenu. Jest on sprawdzany przez zależność `get_caller()`.

```python
_bearer = HTTPBearer()


async def get_caller(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
) -> Caller:
    try:
        payload = jwt.decode(
            creds.credentials, _secret, algorithms=[_algorithm], options={"require": ["sub", "iat", "exp"]}
        )
        if _revoked(payload.get("idx"), float(payload["iat"])):
            raise unauthorized("Token revoked")
        raw = payload.get("roles")
        if not isinstance(raw, list) or any(role not in ("Student", "Teacher", "Admin") for role in raw):
            raise unauthorized("Invalid token")
        roles = tuple(role for role in ("Admin", "Teacher", "Student") if role in raw)
        if not roles:
            raise unauthorized("Invalid token")
        return Caller(email=payload["sub"], idx=payload.get("idx"), roles=roles)
    except jwt.PyJWTError:
        raise unauthorized("Invalid token")
```

*Zależność weryfikująca token*

`HTTPBearer` to klasa FastAPI, która odczytuje nagłówek `Authorization` i oddziela schemat `Bearer` od samego tokenu. Jeśli nagłówka brakuje lub ma on inny schemat niż `Bearer`, `HTTPBearer` sam przerywa obsługę żądania i zwraca błąd 401 `Not authenticated`, a `get_caller()` ani funkcja punktu końcowego nie zostają wywołane. Dodatkowo `HTTPBearer` rejestruje schemat zabezpieczeń w dokumentacji OpenAPI, dzięki czemu w `/api/docs` pojawia się przycisk *Authorize*, którym można wkleić token i wywoływać chronione punkty końcowe bezpośrednio z przeglądarki.

`jwt.decode()` sprawdza podpis tokenu i jego datę ważności. Wygaśnięty lub zmodyfikowany token zwróci błąd. Domyślnie PyJWT sprawdza datę ważności tylko wtedy, gdy pole `exp` znajduje się w tokenie – token bez niego byłby ważny bezterminowo. Dlatego opcja `require` wymusza obecność pól `sub`, `iat` i `exp`, a token bez któregoś z nich jest odrzucany wyjątkiem `MissingRequiredClaimError` [CYTOWANIE: https://pyjwt.readthedocs.io/en/stable/api.html#jwt.decode]. Argument `algorithms=[_algorithm]` wymusza po stronie serwera jeden dozwolony algorytm weryfikacji podpisu, co chroni przed atakami podmiany algorytmu w nagłówku tokenu (2.2) [CYTOWANIE: RFC 8725, sekcja 2.1].

Poprawnie podpisany token jest dodatkowo sprawdzany: `roles` musi być niepustą listą znanych ról. Każdy z tych przypadków kończy się tą samą odpowiedzią 401 `Invalid token`, więc klient nie dowiaduje się, dlaczego token został odrzucony. Osobną odpowiedź, 401 `Token revoked`, otrzymuje token unieważniony. Klient wie wtedy, że wystarczy ponowne zalogowanie.

Token zawiera role z chwili logowania i bez dodatkowego mechanizmu pozostawałby ważny do wygaśnięcia również po zmianie uprawnień osoby (4.4.1). API przechowuje więc w pamięci moment ostatniego unieważnienia tokenów każdej osoby:

```python
_STARTED = time.time()
_revoked_before: dict[str, float] = {}


def revoke_tokens(idx: str) -> None:
    _revoked_before[idx] = time.time()


def _revoked(idx: str | None, issued: float) -> bool:
    return issued < _STARTED or (idx is not None and issued < _revoked_before.get(idx, 0.0))
```

*Unieważnianie tokenów (`auth/deps.py`)*

Funkcję `revoke_tokens()` wywołują punkty końcowe administratora odbierające rolę, dezaktywujące konto i usuwające konto (5.5.9). Token wydany przed zapisanym momentem jest odrzucany, a osoba po ponownym zalogowaniu otrzymuje token z aktualnymi rolami. Ułamkowa część `iat` zapewnia, że token wydany przy logowaniu tuż po unieważnieniu ma późniejszy moment wydania.

Słownik `_revoked_before` znika przy ponownym uruchomieniu API. Bez dodatkowego warunku restart przywracałby więc ważność unieważnionym tokenom. Dlatego odrzucane są wszystkie tokeny wydane przed startem procesu (`_STARTED`), a restart API wylogowuje wszystkich użytkowników. Rozwiązanie zakłada działanie jednego procesu API, ponieważ kilka procesów miałoby osobne słowniki. W prototypie warunek ten jest spełniony: serwer uvicorn uruchamia jeden proces (5.1.5). Przy kilku instancjach listę unieważnień należałoby przenieść do współdzielonego magazynu, np. Redis.

| Sytuacja                                                    | Kod | Treść odpowiedzi                          |
| ----------------------------------------------------------- | :-: | ----------------------------------------- |
| brak nagłówka `Authorization` lub schemat inny niż `Bearer` | 401 | `{"detail": "Not authenticated"}`         |
| zmieniony, wygasły lub uszkodzony token                     | 401 | `{"detail": "Invalid token"}`             |
| token unieważniony lub wydany przed uruchomieniem API       | 401 | `{"detail": "Token revoked"}`             |
| błędny e-mail lub hasło przy logowaniu                      | 401 | `{"detail": "Invalid email or password"}` |
| konto z etykietą `Inactive`                                   | 403 | `{"detail": "Account inactive"}`          |
| konto bez żadnej roli                                       | 403 | `{"detail": "Account has no role"}`       |

*Odpowiedzi przy nieudanym uwierzytelnieniu*

Wynikiem `get_caller()` jest obiekt klasy danych `Caller` z adresem e-mail, identyfikatorem osoby i krotką ról. Weryfikacja odbywa się bez odpytywania bazy danych, na podstawie zawartości tokenu oraz listy unieważnień w pamięci API. Na tym obiekcie opiera się autoryzacja opisana w 5.5.7.

5.5.7 Autoryzacja
Autoryzacja przypisuje funkcje aplikacji do ról, które może otrzymać użytkownik. Opiera się na pokazanym wcześniej mechanizmie `Depends()`, dzięki któremu FastAPI wywołuje funkcję sprawdzającą uprawnienia, zanim uruchomi funkcję punktu końcowego.

Do RBAC wykorzystywana jest fabryka zależności `require(*roles)`, której wynik przekazuje się do `Depends()` w argumentach funkcji punktu końcowego.

```python
def require(*roles: Role):
    async def checker(caller: Caller = Depends(get_caller)) -> Caller:
        if not any(role in caller.roles for role in roles):
            raise forbidden()
        return caller
    return checker
```

*Fabryka zależności sprawdzającej role (`auth/deps.py`)*

Poprzez `Depends(get_caller)` z tokenu uwierzytelniającego użytkownika wyciągane są role (5.5.6), które następnie są porównywane z krotką ról, dla których przewidziano dostęp do danego punktu końcowego. Jeśli w tokenie jest przynajmniej jedna z nich, dostęp jest przyznawany, a `checker` zwraca obiekt `Caller`, z którego funkcja punktu końcowego może dalej korzystać. W przeciwnym razie zgłaszany jest błąd 403, zanim funkcja punktu końcowego zostanie wywołana.

Kod `require` działa w dwóch różnych momentach. Sama funkcja `require` jest wywoływana raz, przy imporcie modułu routera; jej zadaniem jest utworzenie i zwrócenie funkcji `checker`, która zapamiętuje przekazaną krotkę ról jako domknięcie (ang. *closure*). Dopiero `checker` jest wywoływana przez FastAPI przy każdym żądaniu, po rozwiązaniu jej własnej zależności `get_caller`. Dlatego `require` jest zwykłą funkcją, a `checker` – asynchroniczną: gdyby `require` była zadeklarowana jako `async def`, jej wywołanie zwróciłoby obiekt korutyny (5.5.2) zamiast funkcji, której oczekuje `Depends()`.

Zależności dla poszczególnych zestawów ról są tworzone raz, na początku modułów routerów, i współdzielone przez ich punkty końcowe.

| Zmienna | Role | Moduł | Liczba punktów końcowych |
| --- | --- | --- | ---: |
| `_logged_in` | `Student`, `Teacher`, `Admin` | `catalogue.py` | 10 |
| `_student` | `Student` | `student.py` | 10 |
| `_teacher` | `Teacher` | `teacher.py` | 1 |
| `_staff` | `Teacher`, `Admin` | `teacher.py` | 3 |
| `_admin` | `Admin` | `admin.py` | 34 |

*Zależności sprawdzające role*

O ile RBAC jest realizowany w zależnościach FastAPI, o tyle szczegółową kontrolę dostępu ReBAC (2.2, 4.4.2) egzekwują funkcje punktów końcowych. W praktyce polega to na wykonaniu dodatkowej kwerendy sprawdzającej istnienie wymaganej ścieżki w grafie przed wykonaniem kwerendy docelowej i zwróceniu kodu 403 przy braku dopasowania.

```python
_CAN_USE_REGISTRATION = """
MATCH (st:Student {idx: $student_idx})-[:ASSIGNED]->(:RegistrationTurn)<-[:HAS_TURN]-(reg:Registration {id: $registration_id})
RETURN reg.id AS id
"""


async def _require_registration(session: AsyncSession, student_idx: str, registration_id: str) -> None:
    row = await one(
        session,
        _CAN_USE_REGISTRATION,
        student_idx=student_idx,
        registration_id=registration_id,
    )
    if row is None:
        raise forbidden()
```

*Sprawdzenie dostępu studenta do rejestracji (`routers/student.py`)*

Funkcja `_require_registration()` jest najprostszą postacią ReBAC. Sprawdza, czy w grafie istnieje ścieżka od studenta, przez przypisaną mu turę (`ASSIGNED`), do rejestracji, do której ta tura należy (`HAS_TURN`). Wzorzec w `MATCH` jest jednocześnie regułą dostępu: student ma dostęp do rejestracji wtedy i tylko wtedy, gdy przypisano go do którejś z jej tur. W przypadku braku dopasowania funkcja zgłasza wyjątek z kodem 403, a przy spełnieniu warunku kończy działanie bez zwracania wartości. Ponieważ przyjmuje oba identyfikatory jako argumenty, jest niezależna od kontekstu żądania i obsługuje wspólnie punkty końcowe `GET /me/registrations/{registration_id}/subjects` oraz `GET /me/registrations/{registration_id}/groups`.

Kolejnym elementem granularnej kontroli dostępu jest ustalenie, czyich danych dotyczy żądanie. Identyfikator osoby trafia do obiektu `Caller` z roszczenia `idx` tokenu (5.5.6), a do tokenu – z właściwości `idx` węzła użytkownika, odczytanej przy logowaniu (5.4.2). Jest to ten sam identyfikator, którym osoba jest oznaczona w grafie, np. numer indeksu `279413` dla studenta albo `T001` dla prowadzącego. Ponieważ token jest podpisany, klient nie może go zmienić bez unieważnienia podpisu, więc `caller.idx` jest wiarygodny w takim samym stopniu jak role.

Zgodnie z 4.4.2 punkty końcowe operujące na danych zalogowanego użytkownika (z prefiksem `/me/`, jest ich dziesięć) biorą identyfikator osoby wyłącznie z tokenu.

```python
@router.get("/me/enrolments", response_model=MyEnrolmentsResponse)
async def my_enrolments(
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_student),
) -> MyEnrolmentsResponse:
    rows = await run(
        session,
        """
        MATCH (st:Student {idx: $student_idx})-[:ENROLLED]->(ct:CurriculumTerm)<-[:HAS_TERM]-(c:Curriculum)<-[:HAS_CURRICULUM]-(p:Programme)
        OPTIONAL MATCH (ct)-[:TAUGHT_IN]->(ac:AcademicCycle)
        RETURN
          p.id AS programme_id,
          p.name AS programme,
          // ...
        """,
        student_idx=caller.idx,
    )
    return MyEnrolmentsResponse(enrolments=[Enrolment(**row) for row in rows])
```

*Punkt końcowy zwracający kierunki i semestry studenta (`routers/student.py`)*

Zapytanie zaczyna się od węzła studenta wskazanego przez `caller.idx` i przechodzi wyłącznie po jego krawędziach, więc z założenia może zwrócić dane tylko tego użytkownika. Jeśli student nie jest zapisany na żaden kierunek, otrzymuje po prostu pustą listę, bez konieczności osobnego sprawdzenia ReBAC.

Nie zawsze da się uniknąć identyfikatora w żądaniu. Prowadzący, wystawiając ocenę, musi wskazać grupę i studenta, więc ich identyfikatory przychodzą od klienta i trzeba sprawdzić, czy wolno mu z nich skorzystać. Wtedy oba mechanizmy łączą się: jeden koniec ścieżki sprawdzanej przez ReBAC wyznacza `caller.idx` z tokenu, a drugi – identyfikator z żądania.

```python
_staff = require("Teacher", "Admin")

# ...
@router.put("/groups/{group_id}/students/{student_idx}/grade", response_model=SetGroupGradeResponse)
async def set_group_grade(
    group_id: str,
    student_idx: str,
    body: SetGroupGradeRequest,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_staff),
) -> SetGroupGradeResponse:
    if "Teacher" in caller.roles and "Admin" not in caller.roles:
        allowed = await one(
            session,
            """
            MATCH (t:Teacher {idx: $teacher_idx})-[:TEACHES]->(g:Group {id: $group_id})
            RETURN g.id AS id
            """,
            teacher_idx=caller.idx,
            group_id=group_id,
        )
        if allowed is None:
            raise forbidden()
# ...
```

*Fragment funkcji `set_group_grade()` odpowiedzialny za ReBAC*

W tej funkcji kwerenda sprawdza, czy nauczycielowi wolno wystawić ocenę. Z zależności wyciągana jest informacja o sesji i osobie wołającej ten punkt końcowy. Z ciała zapytania wyciągane są informacje o ocenie, a ze ścieżki zasobu – identyfikatory grupy i studenta. Do sprawdzenia uprawnień wystarczą dwa z nich: `caller.idx` z tokenu i `group_id` ze ścieżki. Kwerenda sprawdza, czy prowadzący o tym identyfikatorze uczy (`TEACHES`) grupę o podanym UUID. Jeśli tak, to zostanie zwrócona grupa. Jeśli nie, to zostanie zwrócone `None`, co skutkuje przedwczesnym zatrzymaniem wykonania funkcji przez błąd 403 Forbidden. Sama ocena jest następnie zapisywana we właściwości `grade` krawędzi `REGISTERED_IN` (4.3.3); jeśli student nie jest zapisany do grupy, wzorzec nie zostanie dopasowany, a API odpowiada kodem 404.

Reguła ReBAC sprawia, że podmiana `group_id` na cudzą grupę nic nie daje, ponieważ nie będzie oczekiwanej ścieżki od nauczyciela zaszytego w tokenie do cudzej grupy. 

Jednocześnie administracja omija tę zasadę poprzez instrukcję warunkową na początku funkcji. Warunek sprawdza obie role, ponieważ osoba może mieć jednocześnie rolę prowadzącego i administratora – wtedy obowiązują uprawnienia szersze.

W ten sam sposób łączy oba mechanizmy pokazana wcześniej funkcja `_require_registration()`: punkty końcowe `/me/registrations/{registration_id}/...` wywołują ją z `caller.idx` jako identyfikatorem studenta i `registration_id` ze ścieżki.

5.5.8 Budowa punktu końcowego

Punkty końcowe, zdefiniowane w katalogu `routers/`, są wszystkie zbudowane w bardzo podobny sposób:
1. Dekorator - metoda HTTP, ścieżka względna, `response_model`, kod statusu (jeśli inny niż 200)
2. Argumenty - parametry ścieżki i zapytania, model treści żądania, zależności (sesja, `Caller`)
3. *(FastAPI)* Rozwiązanie zależności - uwierzytelnienie (401) i RBAC (403)
4. *(FastAPI)* Walidacja parametrów i treści żądania (422)
5. *(opcjonalnie)* ReBAC - osobna kwerenda lub warunek w kwerendzie docelowej (403)
6. Kwerenda docelowa - z parametrami ze ścieżki, zapytania, treści żądania lub `caller.idx`
7. Obsługa wyniku - brak wyniku (404), konflikt (409)
8. *(opcjonalnie)* Przetworzenie wyniku w Pythonie i nagłówki odpowiedzi (`Location`)
9. *(FastAPI)* Serializacja przez `response_model` (500 przy niezgodności) i zamknięcie sesji

> Kroki oznaczone *(FastAPI)* nie wymagają kodu w treści funkcji – wynikają z deklaracji w dekoratorze i argumentach.

Dzięki kolejności kroków 3 i 4 walidacja treści żądania nie zdradza nic użytkownikowi bez uprawnień (7.2.1).

Wszystkie kroki przechodzi punkt końcowy `GET /students/{student_idx}`, zwracający prowadzącemu lub administratorowi szczegóły studenta wraz ze średnią ocen:

```python
@router.get("/students/{student_idx}", response_model=StudentDetailResponse)  # [1]
async def student_detail(
    student_idx: str,                                   # [2], [4]
    session: AsyncSession = Depends(get_session),       # [2]
    caller: Caller = Depends(_staff),                   # [2], [3]
) -> StudentDetailResponse:
    if "Teacher" in caller.roles and "Admin" not in caller.roles:   # [5]
        allowed = await one(
            session,
            """
            MATCH (t:Teacher {idx: $teacher_idx})-[:TEACHES]->(:Group)<-[:REGISTERED_IN]-(st:Student {idx: $student_idx})
            RETURN st.idx AS idx
            """,
            teacher_idx=caller.idx,
            student_idx=student_idx,
        )
        if allowed is None:
            raise forbidden()
    row = await one(session, _STUDENT, student_idx=student_idx)     # [6]
    if row is None:                                                 # [7]
        raise not_found("Student")
    grade_rows = await run(session, _STUDENT_GRADES, student_idx=student_idx)  # [6]
    return StudentDetailResponse(**row, avg_grade=average_grade(grade_rows))  # [8], [9]
```

*Punkt końcowy `GET /students/{student_idx}` z oznaczonymi krokami (`routers/teacher.py`)*

1. Metoda `GET`, ścieżka z parametrem `student_idx`, model odpowiedzi; kod statusu domyślny (200).
2. `student_idx` pochodzi ze ścieżki (ta sama nazwa), zależności dostarczają sesję (5.5.3) i `Caller`.
3. `_staff = require("Teacher", "Admin")` - weryfikacja tokenu (5.5.6) i roli (5.5.7).
4. Tylko typ `str` parametru - brak treści żądania.
5. Prowadzący widzi tylko studentów, których uczy lub uczył (ścieżka przez dowolną grupę), a administrator pomija sprawdzenie.
6. `_STUDENT` - dane studenta, `_STUDENT_GRADES` - oceny z wagami typów zajęć i punktami ECTS.
7. Potencjalny brak studenta - 404.
8. Średnia liczona w Pythonie przez `average_grade()` (5.5.5), zaokrąglona do 3 miejsc po przecinku.
9. Walidacja modelem `StudentDetailResponse`, serializacja do JSON, zamknięcie sesji.

W przypadku zapisu do grupy sprawdzenie ReBAC, limitu miejsc i zasady jednej grupy danego typu zostało połączone z utworzeniem krawędzi `REGISTERED_IN` w jednej kwerendzie. Kwerenda zwraca wynik sprawdzenia, a funkcja punktu końcowego zamienia go na kod odpowiedzi.

Jeśli grupa nie należy do żadnej rejestracji z turą studenta albo tura nie trwa, kwerenda nie zwraca wiersza (403). W przeciwnym razie zwraca `status`: `"conflict"` lub `"full"` (409) albo `"ok"`, gdy krawędź została utworzona lub już istniała. Wypis z grupy to analogiczne żądanie `DELETE` pod tym samym adresem – poza turą studenta kończy się kodem 403, a jeśli student nie jest zapisany do grupy, kodem 404. Kod 204 oznacza sukces bez treści odpowiedzi – funkcja niczego nie zwraca. Kwerendę `_REGISTER` i powody, dla których sprawdzenie i zapis muszą być jednym zapytaniem, opisano w 5.5.10.

Punkty końcowe tworzące zasoby zwracają kod 201. Standard HTTP zaleca, by odpowiedź 201 wskazywała utworzony zasób nagłówkiem `Location` [CYTOWANIE: RFC 9110, sekcje 15.3.2 i 10.2.2]. Ustawia go funkcja pomocnicza `_location()`, korzystająca z metody `url_path_for()`.

`url_path_for()` buduje adres z nazwy funkcji punktu końcowego i jej parametrów. Nagłówek ustawiają tylko punkty końcowe, których zasób ma własny `GET` (prowadzący, student, grupa, przedmiot) – pozostałe, np. wydziały, są dostępne wyłącznie jako listy.

Przedmiot jest identyfikowany kodem nadawanym przez uczelnię, więc kod jest w ścieżce, a tworzenie i aktualizacja to jedno żądanie `PUT`. Kod statusu zależy wtedy od wyniku kwerendy i jest ustawiany w treści funkcji. Pierwsze żądanie tworzy przedmiot i zwraca kod 201 z nagłówkiem `Location`. To samo żądanie powtórzone zwraca 200, ponieważ przedmiot już istnieje i zostaje jedynie zaktualizowany. Żądanie `PUT` jest więc idempotentne.

5.5.9 Wybrane punkty końcowe

Poniżej opisano po jednym punkcie końcowym z każdego modułu z 4.5.1. Moduł `public` zawiera wyłącznie logowanie, opisane w 5.5.6. Wybrano przede wszystkim te funkcje, które zapowiedziano w analizie wymagań (3.2, 3.5), a które nie pojawiły się jeszcze w poprzednich podrozdziałach.

W module studenta wystawienie opinii (`POST /opinions`) jest trzecim z procesów opisanych w 3.5. Opinię może wystawić student zapisany do grupy, o prowadzącym tej grupy, i tylko raz dla danej pary grupa–prowadzący (4.3.5).

```python
@router.post("/opinions", response_model=OpinionCreateResponse, status_code=201)
async def create_opinion(
    body: OpinionCreateRequest,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_student),
) -> OpinionCreateResponse:
    student_idx = caller.idx
    check = await one(
        session,
        """
        MATCH (st:Student {idx: $student_idx})
        OPTIONAL MATCH (st)-[:REGISTERED_IN]->(g:Group {id: $group_id})
        OPTIONAL MATCH (t:Teacher {idx: $teacher_idx})-[:TEACHES]->(g)
        OPTIONAL MATCH (st)-[:WRITES]->(dup:Opinion)-[:ABOUT]->(g), (dup)-[:ABOUT_TEACHER]->(t)
        RETURN g IS NOT NULL AS registered, t IS NOT NULL AS teaches, dup IS NOT NULL AS duplicate
        """,
        student_idx=student_idx,
        group_id=body.group_id,
        teacher_idx=body.teacher_idx,
    )
    if check is None or not check["registered"]:
        raise forbidden()
    if not check["teaches"]:
        raise forbidden("Teacher does not teach this group")
    if check["duplicate"]:
        raise conflict("Opinion already exists")
    # ... utworzenie opinii
```

*Sprawdzenie uprawnień przy wystawianiu opinii (`routers/student.py`)*

Identyfikator autora opinii pobierany jest wyłącznie z tokenu wywołującego (5.5.7), bez możliwości wskazania go w treści żądania.

Kwerenda sprawdzająca odpowiada na trzy pytania naraz. Każdy kolejny wzorzec jest w `OPTIONAL MATCH`, więc wiersz jest zwracany nawet wtedy, gdy ścieżka nie istnieje, a brakujący węzeł ma wartość `null`. Dzięki temu jedno zapytanie mówi, czy student jest zapisany do grupy, czy prowadzący ją prowadzi i czy opinia już istnieje, a API może zwrócić dokładny komunikat. Sama opinia jest tworzona drugą kwerendą, jako węzeł z trzema krawędziami: `WRITES`, `ABOUT` i `ABOUT_TEACHER`. Kwerenda ta jeszcze raz sprawdza duplikat, ponieważ między obiema kwerendami ta sama opinia mogła zostać utworzona przez inne żądanie (5.5.10).

| Żądanie | Odpowiedź |
| --- | --- |
| opinia o prowadzącym, który nie prowadzi grupy | 403 `Teacher does not teach this group` |
| poprawna opinia | 201, utworzona opinia |
| ta sama grupa i prowadzący drugi raz | 409 `Opinion already exists` |

*Odpowiedzi `POST /opinions` dla studenta 279413 i wykładu z Biometrii*

W module katalogu odczyt opinii realizuje punkt końcowy `GET /opinions`. Opinie są widoczne przy grupie i przy prowadzącym, bez informacji o autorze (3.4). Punkt końcowy przyjmuje dwa opcjonalne parametry zapytania, `teacher_idx` i `group_id`, z których przynajmniej jeden musi być podany – inaczej zwraca 422.

Zapytanie zaczyna się od węzła wskazanego w żądaniu. Jeśli podano prowadzącego, pierwsza klauzula ma postać:

```cypher
MATCH (t:Teacher {idx: $teacher_idx})<-[:ABOUT_TEACHER]-(o:Opinion)-[:ABOUT]->(g:Group)
WHERE $group_id IS NULL OR g.id = $group_id
```

*Klauzula początkowa kwerendy opinii dla zapytania po prowadzącym (`routers/catalogue.py`)*

a jeśli tylko grupę:

```cypher
MATCH (g:Group {id: $group_id})<-[:ABOUT]-(o:Opinion)-[:ABOUT_TEACHER]->(t:Teacher)
```

*Klauzula początkowa kwerendy opinii dla zapytania po grupie (`routers/catalogue.py`)*

Funkcja punktu końcowego wybiera jedną z nich i dołącza do niej wspólną dalszą część:

```cypher
MATCH (g)-[:OF_TYPE]->(gt:GroupType)<-[:HAS_TYPE]-(si:SubjectInstance)-[:INSTANCE_OF]->(su:Subject)
MATCH (si)-[:OFFERED_IN]->(ac:AcademicCycle)
RETURN
  o.id AS id, o.grade AS grade, o.content AS content, date(o.submit) AS submit,
  g.id AS group_id, su.code AS course_code, su.name AS course_name,
  gt.g_type AS g_type, ac.year + " " + ac.season AS cycle,
  t.idx AS teacher_idx, t.name + " " + t.surname AS teacher
ORDER BY o.submit DESC
```

*Wspólna część kwerendy zwracającej opinie (`routers/catalogue.py`)*

Pierwsza wersja obsługiwała oba parametry jednym warunkiem `WHERE ($teacher_idx IS NULL OR t.idx = $teacher_idx) AND ($group_id IS NULL OR g.id = $group_id)`. Neo4j przechowuje jeden plan dla danej treści zapytania, więc plan musiał działać także przy pustym parametrze i nie mógł zacząć się od wyszukania prowadzącego w indeksie. Zapytanie przeglądało więc wszystkie opinie w bazie i dopiero potem je filtrowało, co ujawniła analiza planu zapytania (`PROFILE`). Rozdzielenie zapytania sprawia, że zaczyna się ono od wyszukania jednego węzła w indeksie klucza (`NodeUniqueIndexSeek`), a jego koszt zależy tylko od liczby opinii o danym prowadzącym lub grupie. Z tego samego powodu rozdzielono odpowiednik zapytania w backendzie relacyjnym: po przejściu na polecenie przygotowane z planem ogólnym PostgreSQL również przeglądał całą tabelę opinii.

Zapytanie pomija krawędź `WRITES`, dzięki czemu dane autora nie są odczytywane z bazy i nie trafiają do odpowiedzi. Sama krawędź pozostaje jednak w grafie, aby wykrywać powtórzone opinie, dlatego opinie są pseudonimowe (4.3.5). Z tego samego względu kwerenda zwraca wyłącznie datę wystawienia opinii. W małej grupie dokładny czas wystawienia pozwalałby prowadzącemu typować autora na podstawie listy zapisanych studentów. Średnia ocen z opinii (`avg_grade`) jest liczona w Pythonie.

W module prowadzącego lista studentów w grupie (`GET /groups/{group_id}/students`) stanowi drugi krok procesu wystawiania oceny (3.5): prowadzący widzi studentów zapisanych do grupy razem z ich dotychczasowymi ocenami. Sprawdzenie uprawnień jest identyczne jak przy wystawianiu oceny (5.5.7) – prowadzący musi prowadzić grupę, administrator pomija sprawdzenie. Ocena jest odczytywana z krawędzi `REGISTERED_IN`, na której jest przechowywana (4.3.3):

```cypher
MATCH (g:Group {id: $group_id})
MATCH (st:Student)-[r:REGISTERED_IN]->(g)
RETURN
  st.idx AS idx, st.name AS name, st.surname AS surname,
  st.phone AS phone, st.photo AS photo, st.joined AS joined,
  r.grade AS grade
ORDER BY st.surname, st.name
```

*Kwerenda zwracająca studentów grupy (`routers/teacher.py`)*

Studenci bez oceny mają w polu `grade` wartość `null`, zgodnie z tym, że właściwość ta nie jest wymagana w schemacie (5.3.1).

W module administratora dezaktywację i usunięcie konta realizują punkty końcowe `PATCH` i `DELETE /admin/users/{idx}`. Zgodnie z wymaganiami (3.1, 3.2) odebranie dostępu nie może usuwać danych osoby. Dezaktywacja (`PATCH` z treścią `{"active": false}`) dodaje etykietę `Inactive` z momentem dezaktywacji, a ponowna aktywacja ją usuwa:

```cypher
// dezaktywacja
MATCH (u:User {idx: $idx})
SET u:Inactive, u.deactivated_at = datetime({timezone: 'Europe/Warsaw'})
RETURN u.idx AS idx

// aktywacja
MATCH (u:User {idx: $idx})
REMOVE u:Inactive, u.deactivated_at
RETURN u.idx AS idx
```

*Zapytania dezaktywacji i aktywacji konta (`routers/admin.py`)*

Usunięcie konta (`DELETE`) zdejmuje z węzła etykiety `User` i `Inactive` oraz dane logowania. Węzeł `Person` z rolami i wszystkimi krawędziami – zapisami, ocenami, opiniami – zostaje w grafie:

```cypher
MATCH (u:User {idx: $idx})
REMOVE u:User:Inactive, u.email, u.passwd_hash, u.deactivated_at
RETURN u.idx AS idx
```

*Zapytanie usunięcia konta z zachowaniem węzła `Person` (`routers/admin.py`)*

Przed wykonaniem tej kwerendy funkcja sprawdza, czy administrator nie usuwa własnego konta, i w takim przypadku zwraca 409. Zapobiega to sytuacji, w której jedyny administrator przypadkowo odcina sobie dostęp do systemu.

Po dezaktywacji i po usunięciu konta API unieważnia tokeny tej osoby (5.5.6). Etykieta `Inactive` jest sprawdzana tylko przy logowaniu, więc bez tego wcześniej wydany token działałby do wygaśnięcia.

Działanie obu operacji, w tym unieważniania tokenów, sprawdzono testem opisanym w 7.2.3.

5.5.10 Współbieżność

Zgodnie z wymaganiami (3.3, 4.3.4) jednoczesne żądania wielu użytkowników nie mogą doprowadzić do niespójnych danych, w szczególności do przepełnienia grupy w trakcie zapisów. Ponieważ Neo4j działa na poziomie izolacji *read committed* (2.1, 5.5.3), typowy wyścig *check-then-act* przebiega następująco: dwie transakcje równocześnie liczą zapisanych studentów, obie widzą 2 z 3 miejsc i obie tworzą krawędź, przez co w grupie znajdują się 4 osoby.

W projekcie zastosowano dwa mechanizmy:
1. Sprawdzenie warunków i zapis wykonuje jedna kwerenda, a więc jedna transakcja.
2. Przed sprawdzeniem warunków kwerenda zakłada blokadę zapisu (ang. *write lock*) na węzłach, których warunki dotyczą.

Neo4j zakłada blokadę zapisu na węźle przy pierwszej modyfikacji i trzyma ją do końca transakcji, a inne transakcje próbujące zmodyfikować ten sam węzeł czekają [CYTOWANIE: https://neo4j.com/docs/operations-manual/current/database-internals/locks-deadlocks/]. Cypher nie ma osobnej instrukcji blokującej węzeł, dlatego blokadę wymusza się zapisem, który niczego nie zmienia, np. `SET g.capacity = g.capacity` [CYTOWANIE: https://neo4j.com/docs/operations-manual/current/database-internals/concurrent-data-access/].

```cypher
MATCH (st:Student {idx: $student_idx})-[:ASSIGNED]->(rt:RegistrationTurn)<-[:HAS_TURN]-(:Registration)-[:OPENS]->(g:Group {id: $group_id})
// Only during the student's turn. Turn times are wall-clock (LOCAL TIME) in the university's zone,
// so the offset is resolved for the turn's date, including summer time.
WHERE datetime({date: rt.date, time: rt.start_time, timezone: 'Europe/Warsaw'}) <= datetime()
  AND datetime() < datetime({date: rt.date, time: rt.end_time, timezone: 'Europe/Warsaw'})
MATCH (g)-[:OF_TYPE]->(gt:GroupType)
WITH DISTINCT st, g, gt
SET st.idx = st.idx
SET g.capacity = g.capacity
WITH st, g,
  EXISTS { (st)-[:REGISTERED_IN]->(g) } AS already,
  EXISTS {
    MATCH (st)-[:REGISTERED_IN]->(other:Group)-[:OF_TYPE]->(gt)
    WHERE other <> g
  } AS conflict,
  COUNT { (g)<-[:REGISTERED_IN]-(:Student) } >= g.capacity AS full
WITH st, g, CASE
  WHEN already THEN "ok"
  WHEN conflict THEN "conflict"
  WHEN full THEN "full"
  ELSE "ok"
END AS status
FOREACH (_ IN CASE WHEN status = "ok" THEN [1] ELSE [] END |
  MERGE (st)-[r:REGISTERED_IN]->(g)
    ON CREATE SET r.registered_at = datetime({timezone: 'Europe/Warsaw'})
)
RETURN status
```

*Kwerenda `_REGISTER` (`routers/student.py`)*

Pierwszy `MATCH` jest jednocześnie sprawdzeniem ReBAC: jeśli student nie ma trwającej tury w rejestracji otwierającej grupę, kwerenda nie zwraca wiersza (403, 5.5.8).

Godziny tury są czasem lokalnym (4.3.4). Przed porównaniem z bieżącym momentem łączy się je z datą tury w strefie `Europe/Warsaw`, więc przesunięcie strefy jest wyznaczane dla konkretnej daty, z uwzględnieniem czasu letniego. Następnie zakładane są dwie blokady:
- `SET st.idx = st.idx` – na studencie: jego jednoczesne żądania zapisu do różnych grup czekają na siebie, więc warunek „jedna grupa danego typu” widzi zapis zatwierdzony chwilę wcześniej,
- `SET g.capacity = g.capacity` – na grupie: jednoczesne zapisy do niej wykonują się po kolei, więc liczba zajętych miejsc jest zawsze aktualna.

Dopiero po założeniu blokad kwerenda oblicza warunki. Przy *read committed* transakcja, która czekała na blokadę, widzi już krawędzie zatwierdzone przez poprzednią. Blokady są zakładane zawsze w tej samej kolejności – najpierw student, potem grupa – dzięki czemu dwie transakcje nie mogą czekać na siebie nawzajem (ang. *deadlock*).

Warunkowy zapis realizuje `FOREACH` po liście jednoelementowej albo pustej – jest to standardowy sposób na wykonanie zapisu tylko przy spełnionym warunku w Cypher bez podzapytań. `MERGE` zamiast `CREATE` sprawia, że ponowny zapis do tej samej grupy niczego nie zmienia, zgodnie z idempotentnością metody `PUT` (4.5.2).

Działanie blokad sprawdzono testem współbieżności opisanym w 7.3. Wykazał on również, że ta sama kwerenda bez dwóch linii `SET` dopuszcza przepełnienie grupy.

Ten sam wzorzec zastosowano przy zapisie dziekańskim (`POST /admin/groups/students`), który pomija sprawdzenie tury, a parametrem `ignore_capacity` pozwala pominąć również limit miejsc (3.2). W odróżnieniu od zapisu studenta, ponowny zapis do tej samej grupy zwraca tu 409, ponieważ jest to metoda `POST`.

Każda osoba musi mieć przynajmniej jedną rolę, więc odebranie ostatniej roli kończy się kodem 409. Bez blokady dwa jednoczesne żądania odebrania dwóch różnych ról osobie, która ma ich dokładnie dwie, mogłyby oba przejść sprawdzenie i zostawić osobę bez roli. Dlatego usunięcie roli wykonuje się w jawnej transakcji (5.5.3), w której najpierw blokowany jest węzeł osoby:

```python
_LOCK_PERSON = "MATCH (p:Person {idx: $idx}) SET p.idx = p.idx RETURN p.idx AS idx"
```

*Zapytanie zakładające blokadę zapisu na węźle `Person` (`routers/admin.py`)*

Kwerenda usuwająca rolę ponownie sprawdza liczbę ról już po założeniu blokady. Do ich odczytu wykorzystano funkcję `labels(p)`, ponieważ predykat etykiety (np. `p:Admin`) po oczekiwaniu na blokadę może jeszcze zwracać etykietę usuniętą chwilę wcześniej przez równoległą transakcję. Działanie blokady potwierdził test współbieżności (7.3, scenariusz D).

Po odebraniu roli API unieważnia tokeny osoby (5.5.6), ponieważ wcześniej wydany token nadal zawiera odebraną rolę. Skutek braku unieważnienia zależał od roli. Kwerendy studenta i prowadzącego zaczynają się od węzła z etykietą roli, np. `(t:Teacher {idx: $teacher_idx})-[:TEACHES]->`, więc po odebraniu etykiety nie dopasowywały niczego i żądanie kończyło się kodem 403. Punkty końcowe administratora sprawdzają natomiast tylko rolę zapisaną w tokenie. Bez unieważniania osoba pozbawiona roli administratora mogłaby więc nadal korzystać z jego punktów końcowych, aż do wygaśnięcia tokenu (7.2.3).

Blokadę zapisu stosuje się również przy wystawianiu opinii (blokada studenta przed ponownym sprawdzeniem duplikatu, 5.5.9), tworzeniu typu grupy (blokada przedmiotu, by instancja przedmiotu i typ grupy nie powstały dwukrotnie) oraz przypisywaniu studentów do tur (blokada rejestracji, by student nie trafił do dwóch tur tej samej rejestracji).

5.6 Klient

Aplikacja kliencka jest aplikacją jednostronicową (4.1) napisaną we frameworku Vue 3, z routerem Vue Router i magazynem stanu Pinia. Całą komunikację z bazą danych realizuje przez API (5.5), ograniczając swoją rolę do prezentacji danych i zbierania parametrów żądań.

Komunikację z API obsługuje jeden moduł `api/client.js`. Funkcja `apiRequest()` dokleja do ścieżki prefiks `/api`, dołącza nagłówek `Authorization` z tokenem i zamienia odpowiedź na obiekt JavaScript. Odpowiedzi z kodem błędu zamienia na wyjątek z komunikatem z pola `detail`, a błędy walidacji (422) – na listę par „pole: komunikat”, które widoki wyświetlają użytkownikowi. Pozostałe funkcje modułu odpowiadają pojedynczym punktom końcowym i są pogrupowane tak jak moduły API (4.5.1), np. `student.register(groupId)` wysyła `PUT /me/registered-groups/{group_id}`.

Formularze administratora odpowiadają kształtom żądań API. Wszędzie tam, gdzie żądanie wymaga identyfikatora istniejącego elementu, np. wydziału przy tworzeniu kierunku czy cyklu przy tworzeniu semestru planu, formularz udostępnia listę wyboru z czytelnymi nazwami. Listy są wypełniane przy otwarciu widoku równoległymi zapytaniami do punktów końcowych administratora zwracających listy elementów, a jako wartość pola trafia do żądania identyfikator. Spełnia to wymaganie z 3.2 – administrator nie musi znać identyfikatorów. Przy tworzeniu osoby formularz podpowiada kolejny numer `idx` (5.3.1).

Po zalogowaniu token, adres e-mail, identyfikator osoby i lista ról z odpowiedzi `POST /login` (5.4.2) są zapisywane w magazynie stanu i w `sessionStorage`, dzięki czemu przetrwają odświeżenie strony, ale nie zamknięcie karty. Na podstawie ról magazyn wyznacza widoczne zakładki:

```javascript
visibleTabs(state) {
  const tabs = []
  if (state.token) tabs.push({ name: 'catalogue', label: 'Catalogue', path: '/catalogue' })
  if (state.roles.includes('Student'))
    tabs.push({ name: 'student', label: 'Student', path: '/student' })
  if (state.roles.includes('Teacher') || state.roles.includes('Admin'))
    tabs.push({ name: 'teacher', label: 'Teacher', path: '/teacher' })
  if (state.roles.includes('Admin'))
    tabs.push({ name: 'admin', label: 'Admin', path: '/admin' })
  return tabs
},
```
*Wyznaczanie zakładek na podstawie ról (`stores/auth.js`)*

Zakładki odpowiadają modułom API i mają te same wymagania co do ról, w tym dostęp administratora do zakładki prowadzącego. Osoba z kilkoma rolami widzi kilka zakładek.

Ukrycie zakładki nie blokuje jednak wpisania adresu widoku ręcznie, dlatego trasy routera mają w metadanych wymagane role, sprawdzane przed każdą zmianą widoku:

```javascript
router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.public) {
    if (auth.isLoggedIn && to.name === 'login') return auth.defaultRoute
    return true
  }
  if (!auth.isLoggedIn) return { name: 'login', query: { redirect: to.fullPath } }
  const roles = to.matched.flatMap((r) => r.meta.roles || [])
  if (roles.length) {
    const ok = roles.some((role) => /* ... */ auth.roles.includes(role))
    if (!ok) return auth.defaultRoute
  }
  return true
})
```
*Strażnik nawigacji (`router/index.js`)*

Strażnik nawigacji realizuje trzy przekierowania. Niezalogowany użytkownik trafia na stronę logowania, a adres, na który próbował wejść, jest zapamiętywany w parametrze `redirect`. Zalogowany użytkownik nie może wrócić na stronę logowania. Wejście do widoku niedozwolonego dla ról użytkownika przenosi go na jego widok domyślny – studenta na plan zajęć studenta, prowadzącego na plan zajęć prowadzącego, a pozostałych na pierwszą dostępną zakładkę. Czwarte przekierowanie wykonuje moduł `api/client.js`: odpowiedź 401 na żądanie z tokenem oznacza, że token wygasł, więc klient usuwa go i przenosi użytkownika na stronę logowania.

Wszystkie te mechanizmy służą wygodzie użytkownika oraz potwierdzeniu, że wszystkie potrzebne punkty końcowe działają poprawnie.
