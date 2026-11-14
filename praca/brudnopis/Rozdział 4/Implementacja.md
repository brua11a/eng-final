5.1 Technologie i środowisko
Środowisko jest stworzone z kontenerów Dockerowych. Częśc z nich to gotowy obraz, część wymagała własnego Dockerfile. Całość jest zorchiestrowana poprzez Docker Compose. 

W celu zabezpieczenia ruchu pomiędzy kontenerami, wprowadzono szyfrowanie zgodnie z dokumentacją: https://neo4j.com/docs/operations-manual/current/security/ssl-framework/. Dotyczy ona konsoli Neo4j i połączenia Bolt wystawianego przez bazę. Z racji tego, że projekt nie zakłada produkcyjnego wdrożenia, nie wdrożono pełnoprawnego CA.

5.1.2 Certyfikaty

Szyfrowanie TLS w projekcie obejmuje trzy połączenia: protokół Bolt bazy Neo4j (port 7687), konsolę Neo4j wystawioną po HTTPS (port 7473) oraz serwer nginx serwujący klienta webowego (port 443 w kontenerze, 5173 na hoście). Wszystkie korzystają z jednego certyfikatu, podpisanego lokalnym urzędem certyfikacji.

Do wygenerowania certyfikatów wykorzystano narzędzie mkcert [CYTOWANIE: https://github.com/FiloSottile/mkcert]. Tworzy ono na maszynie developera lokalny urząd certyfikacji (CA), a polecenie `mkcert -install` dodaje jego certyfikat główny do systemowego magazynu zaufanych certyfikatów oraz do magazynów przeglądarek. Certyfikaty podpisane przez to CA są przez nie akceptowane bez ostrzeżeń, w przeciwieństwie do certyfikatów self-signed, które każda przeglądarka oznacza jako niezaufane. Jednocześnie, w odróżnieniu od certyfikatów self-signed, możliwa jest pełna weryfikacja certyfikatu po stronie klientów, łącznie ze sprawdzeniem nazwy hosta.

Certyfikaty generowane są skryptem `certs.sh`, który należy uruchomić przed pierwszym `docker compose up`:

```bash
#!/usr/bin/bash

set -euo pipefail

cd "$(dirname "$0")"

mkdir -p certificates
cp "$(mkcert -CAROOT)/rootCA.pem" certificates/ca.pem
mkcert -cert-file certificates/public.crt -key-file certificates/private.key neo4j localhost
chmod 644 certificates/private.key
```

Polecenie `cd "$(dirname "$0")"` przenosi skrypt do katalogu, w którym się znajduje, dzięki czemu certyfikaty trafiają do katalogu projektu niezależnie od tego, skąd skrypt został wywołany.

`mkcert -CAROOT` zwraca ścieżkę katalogu lokalnego CA. Do projektu kopiowany jest wyłącznie publiczny certyfikat główny `rootCA.pem`, zapisywany jako `ca.pem`. Klucz prywatny CA (`rootCA-key.pem`) nie opuszcza tego katalogu, więc nie trafia do żadnego kontenera. Plik `ca.pem` służy klientom do weryfikacji certyfikatu serwera.

Następnie generowana jest para: certyfikat `public.crt` i klucz prywatny `private.key`. Certyfikat zawiera w polu Subject Alternative Name dwie nazwy hosta:
- `neo4j` – nazwa serwisu w Docker Compose, pod którą kontenery `init` i `app` łączą się z bazą (`bolt+s://neo4j:7687`). Docker udostępnia w sieci projektu wewnętrzny serwer DNS, który rozwiązuje nazwy serwisów na adresy IP kontenerów [CYTOWANIE: https://docs.docker.com/compose/how-tos/networking/]. Schemat `bolt+s` wymaga, by nazwa w adresie zgadzała się z nazwą w certyfikacie.
- `localhost` – nazwa używana przy dostępie z maszyny hosta: przez przeglądarkę do klienta webowego i konsoli Neo4j oraz przez narzędzia developerskie łączące się z przekierowanym portem 7687.

Nazwy plików `public.crt` i `private.key` są domyślnymi nazwami oczekiwanymi przez politykę SSL Neo4j w katalogu wskazanym przez `base_directory` [CYTOWANIE: https://neo4j.com/docs/operations-manual/current/security/ssl-framework/]. Ponieważ polityki `bolt` i `https` wskazują ten sam katalog `/certificates`, oba połączenia korzystają z tej samej pary kluczy.

We wdrożeniu produkcyjnym certyfikat serwera webowego zostałby zastąpiony certyfikatem publicznego CA (np. Let's Encrypt).


5.1.2 Docker Compose

```yml
services:
  neo4j:
    image: neo4j:2026.07.1-enterprise
    ports:
      - "127.0.0.1:7473:7473"
      - "127.0.0.1:7687:7687"
    environment:
      NEO4J_ACCEPT_LICENSE_AGREEMENT: "yes"
      NEO4J_server_http_enabled: "false"
      NEO4J_server_https_enabled: "true"
      NEO4J_server_bolt_tls__level: REQUIRED
      NEO4J_dbms_ssl_policy_bolt_enabled: "true"
      NEO4J_dbms_ssl_policy_bolt_base__directory: /certificates
      NEO4J_dbms_ssl_policy_https_enabled: "true"
      NEO4J_dbms_ssl_policy_https_base__directory: /certificates
      NEO4J_AUTH: ${NEO4J_USER}/${NEO4J_PASSWORD:?set NEO4J_PASSWORD in .env}
    volumes:
      - neo4j_data:/data
      - ./import:/import:ro
      - ./certificates:/certificates:ro
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- --ca-certificate=/certificates/ca.pem https://localhost:7473 || exit 1"]
      interval: 30s
      timeout: 10s
      start_period: 60s
      retries: 5

  init:
    image: neo4j:2026.07.1-enterprise
    depends_on:
      neo4j:
        condition: service_healthy
    environment:
      NEO4J_ADDRESS: bolt+s://neo4j:7687
      NEO4J_USERNAME: ${NEO4J_USER}
      NEO4J_PASSWORD: ${NEO4J_PASSWORD:?set NEO4J_PASSWORD in .env}
      NEO4J_APP_USER: ${NEO4J_APP_USER}
      NEO4J_APP_PASSWORD: ${NEO4J_APP_PASSWORD:?set NEO4J_APP_PASSWORD in .env}
    volumes:
      - ./queries:/queries:ro
      - ./init.sh:/init.sh:ro
      - ./certificates/ca.pem:/ca.pem:ro
    entrypoint: ["bash", "/init.sh"]

  app:
    build: .
    ports:
      - "127.0.0.1:8000:8000"
    environment:
      NEO4J_URI: bolt+s://neo4j:7687
      NEO4J_USER: ${NEO4J_APP_USER}
      NEO4J_PASSWORD: ${NEO4J_APP_PASSWORD:?set NEO4J_APP_PASSWORD in .env}
      JWT_SECRET: ${JWT_SECRET:?set JWT_SECRET in .env}
      SSL_CERT_FILE: /ca.pem
    volumes:
      - ./certificates/ca.pem:/ca.pem:ro
    read_only: true
    tmpfs:
      - /tmp
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    depends_on:
      init:
        condition: service_completed_successfully

  frontend:
    build:
      context: ./frontend
      args:
        NPM_REGISTRY: ${NPM_REGISTRY:-https://registry.npmjs.org/}
    ports:
      - "5173:443"
    volumes:
      - ./certificates:/certificates:ro
    depends_on:
      - app

volumes:
  neo4j_data:

```

Docker Compose pozwala na jednoczesne uruchamianie wszystkich kontenerów i prostą orchiestrację. Dodatkowo, dzięki niemu można ładować zmienne środowiskowe do tych kontenerów. Są one wyciągane z pliku `.env` na potrzeby prototypu. W produkcyjnym wdrożeniu te zmienne powinny pochodzić z np. secrets valut.

5.1.3 Serwis neo4j

Ten kontener bazuje na obrazie `neo4j:2026.07.1-enterprise`. Jest on grafową bazą danych, potrzebną do przechowywania struktury uczelni i dostępów. Wymagana jest wersja obrazu 2025.06 lub nowsza, oraz koniecznie wersja enterprise, ponieważ jedynie tutaj działa Cypher 25. By dodatkowo móc ustawić GRAPH TYPE, potrzebna była wersja 2026.02 lub nowsza, w tym konieczny był wybór wersji enterprise, ponieważ tylko tam działa ta funkcja.  [CYTOWANIE: https://neo4j.com/docs/cypher-manual/current/queries/select-version/] [CYTOWANIE: https://neo4j.com/docs/cypher-manual/current/schema/graph-types/set-graph-types/]. W związku z wersją enterprise, wymagane było ustawienie zmiennej `NEO4J_ACCEPT_LICENSE_AGREEMENT: "yes"`.

Instancja Neo4j wystawia wiele portów, ale z kontenera przekierowywane są jedynie 7473 i 7687. [CYTOWANIE: https://neo4j.com/docs/operations-manual/current/configuration/ports/] Port 7473 służy do połączenia z HTTPS API i konsolą Neo4j, dającą developerowi możliwość wygodnego podglądu na węzły i krawędzie. Jest to narzędzie typowo developerskie, zatem w produkcyjnym wdrożeniu należy je wyłączyć lub ograniczyć do sieci wewnętrznej.

W trakcie developmentu wystawiany był port 7474 - HTTP. Wdrożono jednak certyfikaty i szyforwanie TLS/SSL, co pozwoliło na korzystanie z konsoli HTTPS.

![[Pasted image 20261114171135.png]]
*Brak możliwości wejścia na konsolę HTTP*

![[Pasted image 20261114171233.png]]
*Zrzut ekranu z konsoli Neo4j wystawionej po HTTPS na porcie 7473*

Port TCP 7687 to domyślny port połączenia Bolt. Jest on wykorzystywany przez Cypher Shell, pokazaną wyżej konsolę Neo4j oraz przez oficjalne drivery Neo4j. Z racji tego, że API będzie wykorzystywało driver Neo4j do komunikacji z bazą, port 7687 jest konieczny.

Żeby połączenie między bazą a API było odporne na podsłuch, wprowadzono szyfrowanie poprzez TLS/SSL. W związku z tym, że SSL jest włączony z Bolt, URI zmienia się z `bolt` na `bolt+s`. Gdyby certyfikat był self-signed, to zamiast tego URI zaczynałoby się od `bolt+ssc`. Ta opcja włącza szyfrowanie bez dodatkowego sprawdzania certyfikatu, co jest akceptowalne na potrzeby lokalnego developmentu. Przeglądarka ostrzegałaby przed wejściem na stronę zabezpieczoną self-signed certyfikatem.

Postanowiono jednak użyć mkcert (https://github.com/FiloSottile/mkcert), co daje wygodę self-signed certyfikatów z "poprawnością" pełnoprawnych certyfikatów. We wdrożeniu produkcyjnym, te certyfikaty zostałyby zastąpione certyfiaktami od publicznie znanego CA

Pozostałe porty domyślnie włączone na instancjach Neo4j, takie jak "Cluster routing connector" czy "Remote debugging" uznano za niepotrzebne. W związku z tym, że nie są one potrzebne, to nie powinny być wystawiane.

Konfiguracja bazowego obrazu Neo4j odbywa się poprzez ustawianie zmiennych środowiskowych. Poza wcześniej wymienioną zmienną potrzebną do akceptowania licencji enterprise, należało włączyć szyfrowanie (https i bolt+s), wyłączyć domyślnie włączone, niebezpieczne protokoły (https), przekazać katalog z zaufanymi certyfikatami, a także przekazać dane do inicjalizacji konta administratora, wyciągane z `.env`.

Wolumeny zamontowane w ramach tego serwisu to `neo4j_data`, `import` i `certificates`. Certyfikaty są konieczne do wdrożenia szyfrowania SSL/TLS. Import zawiera dane, które będą importowane do bazy danych po tym, jak ta wstanie. neo4j_data służy do przechowywania danych w samej bazie już po inicjalizacji, w tym zmian wprowadzonych na żywej instancji pomiędzy uruchomieniami kontenera.

Ostatnim elementem kontenera będzie healthcheck, który będzie warunkiem uruchomienia innych serwisów polegających na bazie danych. Obywa się on po minucie co 30s z timeoutem 10s w pięciu próbach. Po pięciu próbach compose wyrzuci error.

5.1.4 Serwis init

Neo4j nie ma możliwości uruchomienia skryptu inicjalizacyjnego po uruchomieniu bazy danych. Zdecydowano zatem, że do importu danych i innych niezbędnych operacji będzie służył osobny serwis nazwany `init`. 

Polega on na tym samym obrazie, co serwis neo4j. Zdecydowano się na takie rozwiązanie, ponieważ do inicjalizacji jest potrzebne narzędzie cypher-shell, które już jest w tym obrazie. Oznacza to też mniej pobierania, bo bazowy obraz neo4j i tak na pewno już jest.

Serwis init polega na serwisie neo4j, czyli uruchomi się dopiero, gdy tamten będzie w stanie "zdrowym" (ang. *healthy*). Zdrowie serwisu jest sprawdzane healthcheck opisanym wcześniej.

Zmienne przekazane do kontenera to adres bazy danych (port 7687 po `bolt+s` dla adresu kontenera `neo4j`) oraz dane do logowania administratora i użytkownika. Dane administratora są potrzebne do inicjalizacji schemy, w tym ograniczeń, a także zapełnienia bazy danymi przygotowanymi w plikach .csv. Login i hasło użytkownika są potrzebne do stworzenia konta z ograniczonymi uprawnieniami, którym baza danych będzie się komunikowała z API. To konto będzie miało możliwość zapisu i odczytu, ale nie będzie w stanie modyfikować schemy i uprawnień.

Wolumeny montowane w ramach tego kontenera to `queries`, `init.sh` i `certificates`. Wszystkie są ustawione na tryb `ro` - read only, ponieważ nie istnieje powód, dla którego `init` powinien kiedykolwiek modyfikować te pliki.

Po uruchomieniu tego kontenera, wykonywany jest zamontowany wcześniej `init.sh`.

```bash
#!/usr/bin/bash

set -euo pipefail

rm -f /tmp/truststore.p12
keytool -importcert -noprompt -alias ca -file /ca.pem \
    -keystore /tmp/truststore.p12 -storepass changeit
export JAVA_OPTS="-Djavax.net.ssl.trustStore=/tmp/truststore.p12 -Djavax.net.ssl.trustStorePassword=changeit"

cypher-shell -d neo4j -f /queries/schema.cypher
cypher-shell -d neo4j -f /queries/nodes.cypher
cypher-shell -d neo4j -f /queries/edges.cypher

cypher-shell -d system -f /queries/security.cypher \
    --param "user => '$NEO4J_APP_USER'" \
    --param "pw => '${NEO4J_APP_PASSWORD//\'/\\\'}'"

```

Linijka `set -euo pipefail` sprawia, że skrypt kończy działanie z błędem, gdy dowolne polecenie zwróci status różny od 0 (`-e`), gdy użyta zostanie niezdefiniowana zmienna (`-u`) lub gdy błąd wystąpi w dowolnym poleceniu potoku (`-o pipefail`) [CYTOWANIE: https://www.man7.org/linux/man-pages/man1/set.1p.html]. 

Narzędzie cypher-shell jest aplikacją napisaną w Javie, a JVM nie korzysta z systemowego magazynu certyfikatów, tylko z własnego (`cacerts`), zawierającego wyłącznie publiczne urzędy certyfikacji. Certyfikat Neo4j jest podpisany lokalnym CA wygenerowanym przez mkcert, więc bez dodatkowej konfiguracji połączenie `bolt+s` kończy się błędem `PKIX path building failed`. cypher-shell nie udostępnia opcji wskazania pliku CA, dlatego za pomocą `keytool` tworzony jest magazyn zaufanych certyfikatów (ang. *truststore*) w formacie PKCS#12, do którego importowany jest certyfikat `ca.pem`. Następnie przez zmienną `JAVA_OPTS`, przekazywaną przez skrypt uruchomieniowy cypher-shell do JVM, ustawiane są właściwości `javax.net.ssl.trustStore` i `javax.net.ssl.trustStorePassword` [CYTOWANIE: Oracle JSSE Reference Guide].

Problem nie wystąpiłby w przypadku certyfikatu wystawionego przez publiczny urząd certyfikacji, ponieważ jego certyfikat główny znajduje się już w domyślnym magazynie `cacerts`. Zniknąłby również po zamianie schematu `bolt+s` na `bolt+ssc`. Takie rozwiązanie wprowadza jednak nowy problem: `bolt+ssc`, mimo skrótu od *self-signed certificate* w nazwie, w ogóle nie weryfikuje ani certyfikatu serwera, ani jego podpisu, ani nazwy hosta. Połączenie pozostaje szyfrowane, ale klient nie ma pewności, z kim się łączy. Atakujący w pozycji pośrednika (ang. *Man-in-the-Middle*), posługujący się dowolnym certyfikatem, mógłby podszyć się pod serwer bazy danych, a tym samym odczytać i modyfikować ruch, w tym przesyłane dane uwierzytelniające.

Ostatnim elementem inicjalizacji są cztery polecenia `cypher-shell`. 



5.2 Struktura repozytorium

```
.
├── app
│   ├── graph_backend
│   │   ├── auth
│   │   └── routers
│   └── schemas
├── endpoint_schema
├── frontend
│   └── src
│       ├── api
│       ├── components
│       │   └── catalogue
│       ├── composables
│       ├── layouts
│       ├── router
│       ├── stores
│       ├── styles
│       ├── utils
│       └── views
│           ├── admin
│           ├── catalogue
│           ├── shared
│           ├── student
│           └── teacher
├── import
│   ├── edges
│   └── nodes
├── queries
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.api
├── init.sh
├── requirements.txt
└── .env.example
```

Klient Vue jest w całości zawarty w katalogu `frontend/`.

W katalogu `app/` znajduje się backend, w tym warstwa API. W podkatalogu `schemas/` zdefiniowano modele Pydantic, opisujące oczekiwany kształt żądań i odpowiedzi serwera, a w podkatalogu `graph_backend/` – backend grafowy.

*todo* W tym samym katalogu, w podkatalogu `relation_backend/`, znajdzie się implementacja relacyjna podobnego systemu. Będzie ona działać w ten sam sposób – poprzez sterownik bazy danych zamiast mapowania obiektowo-relacyjnego. Oba backendy będą korzystać z tych samych modeli Pydantic.

Ponieważ eksploracja bazy danych jest szczególnym celem tej pracy, poświęcono jej dużą część repozytorium. Katalog `import/` zawiera dane początkowe, a katalog `queries/` – instrukcje w języku Cypher wykonywane przy inicjalizacji bazy danych przez skrypt `init.sh` (5.3). Katalog `endpoint_schema/` zawiera dokumentację punktów końcowych API (5.4).

Dane dostępowe (hasła do bazy danych i klucz podpisujący tokeny) przechowywane są w pliku `.env`, który nie trafia do repozytorium. Wymagane zmienne opisano w pliku `.env.example`.

5.3 Inicjalizacja i schemat bazy danych

W katalogu `import/` znajdują się dane w formacie CSV (ang. *Comma-Separated Values*), importowane przy inicjalizacji bazy danych – `nodes/` zawiera węzły, a `edges/` krawędzie. Na każdy typ węzła i na każdy typ krawędzi przypada osobny plik. Wyjątkiem jest etykieta User – dane logowania (adres e-mail i skrót hasła) są kolumnami w plikach studentów, prowadzących i administratorów, a etykieta nadawana jest przy imporcie tym osobom, które mają podany adres e-mail.

Skrypt `init.sh` wykonuje kolejno instrukcje z katalogu `queries/`: `schema.cypher` narzuca kształt węzłów i krawędzi oraz pozostałe ograniczenia, `nodes.cypher` i `edges.cypher` wczytują pliki CSV z węzłami i krawędziami, a `security.cypher` tworzy konto bazodanowe, którym łączy się API (4.4.3).

Definicja typu grafu w `schema.cypher` jest zapisana w wersji Cypher 25 (`CYPHER 25 ALTER CURRENT GRAPH TYPE SET ...`), ponieważ ta funkcja jest dostępna wyłącznie w tej wersji języka. Pozostałe zapytania, zarówno importujące, jak i wykonywane przez API, korzystają z domyślnej wersji języka skonfigurowanej w bazie.

5.4 Dokumentacja

Katalog `endpoint_schema/` zawiera dokumentację punktów końcowych API: dozwolone role, kształt żądań i odpowiedzi oraz wykonywane zapytania. Ponadto API generuje interaktywną dokumentację w standardzie OpenAPI [CYTOWANIE: https://fastapi.tiangolo.com/reference/openapi/docs/], na podstawie tych samych modeli, które służą do walidacji.

5.5 API

Na podstawie modeli Pydantic API sprawdza poprawność danych wejściowych i formatuje dane wyjściowe. Obsługa żądania przebiega następująco: API odbiera żądanie na wybranym punkcie końcowym, weryfikuje token i uprawnienia użytkownika, otwiera sesję bazy danych, a następnie – jeśli wykorzystywany jest backend grafowy – wykonuje zapytanie w języku Cypher, przekształca jego wynik do oczekiwanego kształtu i zwraca go klientowi. Zapytania wykonywane są bezpośrednio przez oficjalny, asynchroniczny sterownik Neo4j dla języka Python [CYTOWANIE: https://neo4j.com/docs/api/python-driver/current/].

5.6 Klient