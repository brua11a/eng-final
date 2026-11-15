5.1 Technologie i środowisko
Środowisko jest stworzone z kontenerów Dockerowych. Częśc z nich to gotowy obraz, część wymagała własnego Dockerfile. Całość jest zorchiestrowana poprzez Docker Compose. 

W celu zabezpieczenia ruchu pomiędzy kontenerami, wprowadzono szyfrowanie zgodnie z dokumentacją: https://neo4j.com/docs/operations-manual/current/security/ssl-framework/. Dotyczy ona konsoli Neo4j i połączenia Bolt wystawianego przez bazę. Szyfrowane są również połączenia przeglądarki z serwerem nginx oraz serwera nginx z API. Z racji tego, że projekt nie zakłada produkcyjnego wdrożenia, nie wdrożono pełnoprawnego CA.

5.1.1 Certyfikaty

Szyfrowanie TLS w projekcie obejmuje cztery połączenia: protokół Bolt bazy Neo4j (port 7687), konsolę Neo4j wystawioną po HTTPS (port 7473), serwer nginx serwujący klienta webowego (port 443 w kontenerze, 5173 na hoście) oraz API, do którego nginx przekazuje żądania (port 8000). Wykorzystywane są dwa certyfikaty, oba podpisane tym samym lokalnym urzędem certyfikacji: jeden współdzielony przez Neo4j i nginx, drugi przeznaczony wyłącznie dla API.

Do wygenerowania certyfikatów wykorzystano narzędzie mkcert [CYTOWANIE: https://github.com/FiloSottile/mkcert]. Tworzy ono na maszynie developera lokalny urząd certyfikacji (CA), a polecenie `mkcert -install` dodaje jego certyfikat główny do systemowego magazynu zaufanych certyfikatów oraz do magazynów przeglądarek. Certyfikaty podpisane przez to CA są przez przeglądarkę akceptowane bez ostrzeżeń, w przeciwieństwie do certyfikatów self-signed, które każda przeglądarka oznacza jako niezaufane. Jednocześnie, w odróżnieniu od certyfikatów self-signed, możliwa jest pełna weryfikacja certyfikatu po stronie klientów, łącznie ze sprawdzeniem nazwy hosta.

Certyfikaty generowane są skryptem `certs.sh`, który należy uruchomić przed pierwszym `docker compose up`:

```bash
#!/usr/bin/bash

set -euo pipefail

cd "$(dirname "$0")"

mkdir -p certificates
cp "$(mkcert -CAROOT)/rootCA.pem" certificates/ca.pem
mkcert -cert-file certificates/public.crt -key-file certificates/private.key neo4j localhost
chmod 644 certificates/private.key

mkdir -p certificates/app
mkcert -cert-file certificates/app/public.crt -key-file certificates/app/private.key app localhost
chmod 644 certificates/app/private.key
```

Polecenie `cd "$(dirname "$0")"` przenosi skrypt do katalogu, w którym się znajduje, dzięki czemu certyfikaty trafiają do katalogu projektu niezależnie od tego, skąd skrypt został wywołany.

`mkcert -CAROOT` zwraca ścieżkę katalogu lokalnego CA. Do projektu kopiowany jest wyłącznie publiczny certyfikat główny `rootCA.pem`, zapisywany jako `ca.pem`. Klucz prywatny CA (`rootCA-key.pem`) nie opuszcza tego katalogu, więc nie trafia do żadnego kontenera. Plik `ca.pem` służy klientom do weryfikacji certyfikatu serwera.

Następnie generowana jest para: certyfikat `public.crt` i klucz prywatny `private.key`. Certyfikat zawiera w polu Subject Alternative Name dwie nazwy hosta:
- `neo4j` – nazwa serwisu w Docker Compose, pod którą kontenery `init` i `app` łączą się z bazą (`bolt+s://neo4j:7687`). Docker udostępnia w sieci projektu wewnętrzny serwer DNS, który rozwiązuje nazwy serwisów na adresy IP kontenerów [CYTOWANIE: https://docs.docker.com/compose/how-tos/networking/]. Schemat `bolt+s` wymaga, by nazwa w adresie zgadzała się z nazwą w certyfikacie.
- `localhost` – nazwa używana przy dostępie z maszyny hosta: przez przeglądarkę do klienta webowego i konsoli Neo4j oraz przez narzędzia developerskie łączące się z przekierowanym portem 7687.

Nazwy plików `public.crt` i `private.key` są domyślnymi nazwami oczekiwanymi przez politykę SSL Neo4j w katalogu wskazanym przez `base_directory` [CYTOWANIE: https://neo4j.com/docs/operations-manual/current/security/ssl-framework/]. Ponieważ polityki `bolt` i `https` wskazują ten sam katalog `/certificates`, oba połączenia korzystają z tej samej pary kluczy.

Druga para, zapisywana w katalogu `certificates/app/`, należy do API. Jej certyfikat zawiera nazwy:
- `app` – nazwa serwisu w Docker Compose, pod którą nginx przekazuje żądania do API (`https://app:8000`),
- `localhost` – nazwa używana przez developera przy bezpośrednim dostępie do API z hosta oraz przez serwer deweloperski Vite.

Osobny certyfikat dla API wynika z zasady najmniejszych uprawnień: kontener `app` otrzymuje wyłącznie własny klucz prywatny i nie ma dostępu do klucza Neo4j. Przejęcie kontenera API nie pozwala więc podszyć się pod bazę danych i odwrotnie.

Polecenia `chmod 644` nadają kluczom prywatnym prawo odczytu dla wszystkich użytkowników. Jest to konieczne, ponieważ procesy w kontenerach działają z innym UID niż właściciel plików na hoście (np. API działa jako użytkownik `api` o UID 10001, opisany w 5.1.5), a katalogi z certyfikatami są montowane w trybie tylko do odczytu.

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
      - ./certificates/app:/certs:ro
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
      - "127.0.0.1:5173:443"
    volumes:
      - ./certificates/public.crt:/certificates/public.crt:ro
      - ./certificates/private.key:/certificates/private.key:ro
      - ./certificates/ca.pem:/certificates/ca.pem:ro
    read_only: true
    tmpfs:
      - /var/cache/nginx
      - /var/run
      - /tmp
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
      - CHOWN
      - SETUID
      - SETGID
    security_opt:
      - no-new-privileges:true
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
    --param "pw => '$NEO4J_APP_PASSWORD'"

```

Linijka `set -euo pipefail` sprawia, że skrypt kończy działanie z błędem, gdy dowolne polecenie zwróci status różny od 0 (`-e`), gdy użyta zostanie niezdefiniowana zmienna (`-u`) lub gdy błąd wystąpi w dowolnym poleceniu potoku (`-o pipefail`) [CYTOWANIE: https://www.man7.org/linux/man-pages/man1/set.1p.html]. 

Narzędzie cypher-shell jest aplikacją napisaną w Javie, a JVM nie korzysta z systemowego magazynu certyfikatów, tylko z własnego (`cacerts`), zawierającego wyłącznie publiczne urzędy certyfikacji. Certyfikat Neo4j jest podpisany lokalnym CA wygenerowanym przez mkcert, więc bez dodatkowej konfiguracji połączenie `bolt+s` kończy się błędem `PKIX path building failed`. cypher-shell nie udostępnia opcji wskazania pliku CA, dlatego za pomocą `keytool` tworzony jest magazyn zaufanych certyfikatów (ang. *truststore*) w formacie PKCS#12, do którego importowany jest certyfikat `ca.pem`. Następnie przez zmienną `JAVA_OPTS`, przekazywaną przez skrypt uruchomieniowy cypher-shell do JVM, ustawiane są właściwości `javax.net.ssl.trustStore` i `javax.net.ssl.trustStorePassword` [CYTOWANIE: Oracle JSSE Reference Guide].

Problem nie wystąpiłby w przypadku certyfikatu wystawionego przez publiczny urząd certyfikacji, ponieważ jego certyfikat główny znajduje się już w domyślnym magazynie `cacerts`. Zniknąłby również po zamianie schematu `bolt+s` na `bolt+ssc`. Takie rozwiązanie wprowadza jednak nowy problem: `bolt+ssc`, mimo skrótu od *self-signed certificate* w nazwie, w ogóle nie weryfikuje ani certyfikatu serwera, ani jego podpisu, ani nazwy hosta. Połączenie pozostaje szyfrowane, ale klient nie ma pewności, z kim się łączy. Atakujący w pozycji pośrednika (ang. *Man-in-the-Middle*), posługujący się dowolnym certyfikatem, mógłby podszyć się pod serwer bazy danych, a tym samym odczytać i modyfikować ruch, w tym przesyłane dane uwierzytelniające.

Ostatnim etapem inicjalizacji są cztery wywołania `cypher-shell`: trzy pierwsze ładują dane, a ostatnie konfiguruje dostęp do bazy. Wykonywane skrypty znajdują się w zamontowanym katalogu `queries`. `cypher-shell` odczytuje automatycznie adres, nazwę użytkownika i hasło ze zmiennych środowiskowych `NEO4J_ADDRESS`, `NEO4J_USERNAME` i `NEO4J_PASSWORD` [CYTOWANIE: https://neo4j.com/docs/operations-manual/current/cypher-shell/].

Działanie skryptów ładujących dane zostało opisane w rozdziale 5.3.

Ostatnie polecenie tworzy użytkownika bazy danych z ograniczonymi uprawnieniami, wykorzystywanego przez API. Rola `app_rw` pozwala na odczyt i zapis danych w grafie `neo4j`, ale nie obejmuje zarządzania schematem ani użytkownikami. Neo4j przyznaje wyłącznie jawnie nadane uprawnienia, więc te operacje są niedostępne bez dodatkowej konfiguracji. Inaczej jest z uprawnieniem `LOAD`, pozwalającym m.in. na wczytywanie plików poleceniem `LOAD CSV`: każdy użytkownik posiada rolę `PUBLIC`, która domyślnie ma nadane `LOAD ON ALL DATA`. Dlatego zostało ono jawnie odebrane poleceniem `DENY`, które ma pierwszeństwo przed `GRANT`. Ograniczenie uprawnień zmniejsza skutki ewentualnego przejęcia lub błędnej konfiguracji warstwy API.

```cypher
CREATE OR REPLACE USER $user SET PASSWORD $pw CHANGE NOT REQUIRED;
CREATE ROLE app_rw IF NOT EXISTS;
GRANT ACCESS ON DATABASE neo4j TO app_rw;
GRANT MATCH {*} ON GRAPH neo4j TO app_rw;
GRANT WRITE ON GRAPH neo4j TO app_rw;

DENY LOAD ON ALL DATA TO app_rw;
GRANT ROLE app_rw TO $user;
```

Wracając do samego polecenia `cypher-shell`, nazwa i hasło użytkownika są przekazywane jako parametry `$user` i `$pw` flagą `--param`, z wartościami pobieranymi ze zmiennych środowiskowych. Wartość flagi `--param` nie jest jednak zwykłym tekstem, lecz wyrażeniem Cypher. Zgodnie z dokumentacją, wartością parametru może być dowolne wyrażenie Cypher, obliczane jednorazowo po stronie serwera [CYTOWANIE: https://neo4j.com/docs/operations-manual/current/cypher-shell/]. Umożliwia to przekazywanie wartości dowolnego typu, np. dat, ale oznacza też, że wartość zmiennej środowiskowej, wstawiona przez powłokę bash do treści wyrażenia, staje się fragmentem kodu Cypher. Dlatego wartości zmiennych zostały objęte apostrofami, tworząc literał tekstowy Cypher.

Przekazywanie parametrów jako wyrażeń Cypher sprawia, że inicjalizacja jest podatna na wstrzyknięcie kodu Cypher (ang. *Cypher injection*), a wartości zawierające znaki o specjalnym znaczeniu, takie jak `'` czy `\`, powodują błąd inicjalizacji lub ciche zapisanie innego hasła niż podane w `.env`.

*Wartość parametru `pw` w zależności od zawartości zmiennej `NEO4J_APP_PASSWORD`*

| Wartość w `.env`     | Apostrofy w `init.sh` | Wyrażenie otrzymane przez cypher-shell | Wynik                                               |
| -------------------- | --------------------- | -------------------------------------- | --------------------------------------------------- |
| `hunter2`            | nie                   | `pw => hunter2`                        | błąd: niezdefiniowana zmienna `hunter2`             |
| `s3cr3t-pass`        | nie                   | `pw => s3cr3t-pass`                    | błąd: niezdefiniowana zmienna `s3cr3t`              |
| `12345`              | nie                   | `pw => 12345`                          | `12345` (INTEGER)                                   |
| `1+1`                | nie                   | `pw => 1+1`                            | `2` (INTEGER)                                       |
| `hunter2`            | tak                   | `pw => 'hunter2'`                      | `"hunter2"` (STRING), poprawnie                     |
| `it's`               | tak                   | `pw => 'it's'`                         | błąd: apostrof kończy literał                       |
| `ends\`              | tak                   | `pw => 'ends\'`                        | błąd: niezamknięty literał                          |
| `a\nb`               | tak                   | `pw => 'a\nb'`                         | `"a⏎b"` (STRING), znak nowej linii zamiast `\n`     |
| `' + datetime() + '` | tak                   | `pw => '' + datetime() + ''`           | `"2026-11-14T18:53:46.592Z"` (STRING), wykonany kod |

Z poziomu samego Cypher nie da się tego obejść, ponieważ problem występuje już na etapie parsowania wyrażenia, zanim jakakolwiek funkcja mogłaby przetworzyć wartość. Przyjęto więc założenie, że nazwa użytkownika i hasło nie zawierają znaków `'` ani `\`. Pełnym rozwiązaniem byłby dodatkowy skrypt, który odczytuje zmienne środowiskowe i wykonuje polecenia z `security.cypher` przy pomocy drivera Neo4j, przekazując nazwę użytkownika i hasło jako parametry zapytania. Parametry przesyłane przez driver nie są interpretowane jako kod, więc nie wymagają żadnego przetwarzania.

Skrypt jest uruchamiany przy każdym starcie środowiska, a dane bazy, w tym użytkownicy, są zachowywane w wolumenie `neo4j_data`. Dlatego musi on działać poprawnie także wtedy, gdy użytkownik już istnieje, i jednocześnie uwzględniać ewentualną zmianę hasła w `.env`. Rozważono trzy warianty:

- `CREATE USER … IF NOT EXISTS` – przy istniejącym użytkowniku polecenie jest pomijane, więc nowe hasło z `.env` nie zostałoby zastosowane.
- `ALTER USER … SET PASSWORD` – Neo4j odrzuca ustawienie hasła identycznego z dotychczasowym (błąd `22N89: new password cannot be the same as the old password`), więc każde ponowne uruchomienie bez zmiany hasła kończyłoby się błędem.
- `CREATE OR REPLACE USER` – użytkownik jest usuwany i tworzony od nowa z hasłem z `.env`.

Wybrano trzeci wariant, żeby móc zmienić hasło użytkownika bez przebudowy wszystkich elementów compose'a.

5.1.5 Serwis app
Odpowiada on za backend aplikacji, czyli API dające klientom wygodny dostęp do zawartości grafowej bazy danych.

Serwis `app` jest budowany z `Dockerfile` bazującym na obrazie `python:3.14-slim`.

```dockerfile
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN useradd --system --no-create-home --uid 10001 api
USER api

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", \
     "--ssl-certfile", "/certs/public.crt", "--ssl-keyfile", "/certs/private.key"]
```

Zmienne środowiskowe wyłączają buforowanie, by stdout i stderr pisały od razu, oraz zapisywanie plików `.pyc` z kodem bajtowym, które w kontenerze tylko do odczytu i tak nie byłoby możliwe [CYTOWANIE: https://docs.python.org/3/using/cmdline.html#environment-variables].

Instrukcja `WORKDIR` ustawia katalog roboczy `/app`, dzięki czemu kolejne instrukcje, a także uruchomiona aplikacja, działają w katalogu `/app` w środku kontenera. Dzięki temu aplikacja jest w swoim własnym katalogu, oddzielona od plików systemowych obrazu, a `uvicorn` może odnaleźć w nim pakiet `app` [CYTOWANIE: https://docs.docker.com/reference/dockerfile/].

Poprzez `COPY` jest kopiowana lista wymaganych bibliotek Pythonowych do kontenera, konkretnie do `/app/requirements.txt`. Następnie poprzez instrukcję `RUN` są one pobierane i instalowane.

Gdy wymagane pakiety są już zainstalowane, do `/app/app` jest kopiowany lokalny katalog z zawartością aplikacji, też nazwany `app`. Znajduje się tam kod potrzebny do uruchomienia backendu. Kopiowanie kodu dopiero po instalacji zależności sprawia, że przy zmianie samego kodu Docker ponownie wykorzystuje warstwę z zainstalowanymi pakietami, zamiast instalować je od nowa.

Instrukcje `RUN useradd --system --no-create-home --uid 10001 api` i `USER api` tworzą nowego użytkownika systemowego bez własnego katalogu domowego o UID 10001, a następnie przełączają się na niego, więc to z jego uprawnieniami działa aplikacja. Dzięki temu, gdyby komuś udało się przejąć proces aplikacji, wykonywałby polecenia z poziomu użytkownika `api`, a nie `root`.

Ostatnia instrukcja, `CMD`, uruchamia aplikację zamieszczoną w `/app/app` na porcie 8000 w kontenerze. Adres `0.0.0.0` sprawia, że jest ona osiągalna z innych kontenerów, np. z serwera nginx. Aplikacja działa, dopóki kontener nie zostanie zatrzymany.

Flagi `--ssl-certfile` i `--ssl-keyfile` sprawiają, że uvicorn serwuje API wyłącznie po HTTPS [CYTOWANIE: https://www.uvicorn.org/settings/#https]. Certyfikat i klucz pochodzą z katalogu `certificates/app/` (5.1.1), montowanego w compose jako `/certs` w trybie tylko do odczytu. Klucz nie jest kopiowany do obrazu, więc nie trafia do żadnej z jego warstw.

Bez tego ruch między serwerem nginx a API odbywałby się zwykłym HTTP. Szyfrowanie TLS kończyłoby się na nginx, a token JWT, dane logowania i odpowiedzi API przechodziłyby przez sieć Dockera jawnym tekstem. Choć sieć ta jest izolowana od hosta, każdy kontener w niej podłączony mógłby taki ruch podsłuchać lub podszyć się pod API.

Konfiguracja połączenia po stronie nginx, w tym weryfikacja certyfikatu API, została opisana w 5.1.6.

Konfiguracja serwisu w `docker-compose.yml`:

```yml
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
      - ./certificates/app:/certs:ro
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
```

`build: .` buduje obraz z opisanego wyżej `Dockerfile`, znajdującego się w katalogu głównym projektu.

Aplikacja wystawiona na porcie 8000 jest również przekierowywana na port 8000 localhost, dzięki czemu API jest widoczne dla developera pod adresem `https://localhost:8000`. Zwykłe żądanie HTTP na ten port nie otrzymuje odpowiedzi.

![[Pasted image 20261115020127.png]]

*API widoczne z przeglądarki*

W produkcyjnym wdrożeniu port 8000 w tym kontenerze nie powinien być wystawiony na hosta. Nie jest on potrzebny do działania systemu: z bazą danych połączenie jest wykonywane po `bolt+s://neo4j:7687`, a aplikacja kliencka widzi API poprzez serwer nginx w kontenerze `frontend`, pełniący rolę odwrotnego proxy (ang. *reverse proxy*). Przeglądarka komunikuje się wyłącznie z nginx po HTTPS, w ramach tego samego *origin* co aplikacja kliencka, a nginx przekazuje żądania kierowane do ścieżek API pod adres `https://app:8000` w wewnętrznej sieci Dockera (5.1.6).

Zmienne środowiskowe przekazują aplikacji konfigurację w postaci adresu bazy danych (`NEO4J_URI`) i danych uwierzytelniających użytkownika systemowego stworzonego przez serwis `init` (`NEO4J_USER` i `NEO4J_PASSWORD`). Dodatkowo przekazywany jest `JWT_SECRET` potrzebny do podpisywania tokenów wydawanych przez API oraz `SSL_CERT_FILE`, czyli ścieżka do certyfikatu. Dzięki tej fladze, certyfikat zostaje załadowany do zaufanych certyfikatów, co pozwala później z nich korzystać.

Składnia `${ZMIENNA:?komunikat}` sprawia, że Docker Compose odmawia uruchomienia, jeśli zmienna nie jest ustawiona w `.env` [CYTOWANIE: https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/].

Wolumeny montują certyfikat CA (`/ca.pem`) oraz certyfikat i klucz API (`/certs`), oba w trybie tylko do odczytu.

Pozostałe opcje ograniczają możliwości kontenera na wypadek przejęcia aplikacji [CYTOWANIE: https://docs.docker.com/reference/compose-file/services/]:
- `read_only: true` – system plików kontenera jest tylko do odczytu, więc atakujący nie może podmienić kodu aplikacji ani zapisać własnych plików wykonywalnych.
- `tmpfs: /tmp` – jedyny zapisywalny katalog, przechowywany w pamięci RAM i znikający po zatrzymaniu kontenera. Jest potrzebny bibliotekom, które zapisują pliki tymczasowe.
- `cap_drop: ALL` – odbiera procesowi wszystkie uprawnienia jądra Linux (ang. *capabilities*), np. możliwość zmiany właściciela plików czy obsługi surowych gniazd sieciowych. Aplikacja nasłuchuje na porcie 8000, powyżej 1024, więc żadne z nich nie jest jej potrzebne.
- `no-new-privileges:true` – uniemożliwia procesowi uzyskanie nowych uprawnień, np. przez uruchomienie programu z bitem setuid. Uzupełnia to działanie jako nieuprzywilejowany użytkownik `api`.

`depends_on` z warunkiem `service_completed_successfully` sprawia, że API startuje dopiero po pomyślnym zakończeniu serwisu `init`, czyli gdy baza zawiera już schemat, dane i konto `app_rw`. Gdyby inicjalizacja się nie powiodła, API w ogóle nie zostanie uruchomione.


5.1.6 Serwis frontend

Serwis `frontend` jest punktem wejścia do systemu dla użytkownika. Działający w nim serwer nginx serwuje aplikację kliencką Vue (5.6) i pełni rolę odwrotnego proxy dla API. Przeglądarka komunikuje się z jednym adresem (`https://localhost:5173`), więc aplikacja kliencka i API dzielą ten sam *origin* i nie jest potrzebna konfiguracja CORS.

Serwis jest budowany z `Dockerfile` znajdującego się w katalogu `frontend/`:

```dockerfile
FROM node:22-bookworm-slim AS build

WORKDIR /app

COPY package.json ./
ARG NPM_REGISTRY=https://registry.npmjs.org/
RUN npm config set registry "${NPM_REGISTRY}" && npm install

COPY . .

ARG VITE_API_URL=
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
```

Wykorzystano budowanie wieloetapowe (ang. *multi-stage build*) [CYTOWANIE: https://docs.docker.com/build/building/multi-stage/]. Etap `build` z obrazem Node.js buduje aplikację kliencką, a do końcowego obrazu `nginx:1.27-alpine` trafiają wyłącznie gotowe pliki statyczne z katalogu `dist`. Środowisko Node.js, npm i `node_modules` nie znajdują się więc w działającym kontenerze, co zmniejsza jego rozmiar i powierzchnię ataku. Kolejność instrukcji, podobnie jak w 5.1.5, pozwala ponownie wykorzystać warstwę z zależnościami przy zmianie samego kodu.

Argument `NPM_REGISTRY` pozwala wskazać inny rejestr pakietów npm, np. w sieci z ograniczonym dostępem do publicznego rejestru. Zmienna `VITE_API_URL` jest wstawiana przez Vite do kodu na etapie budowania [CYTOWANIE: https://vite.dev/guide/env-and-mode] i celowo pozostaje pusta, dzięki czemu aplikacja wysyła żądania pod ścieżki względne, czyli do tego samego serwera nginx.

Konfiguracja serwera nginx, kopiowana do obrazu jako `/etc/nginx/conf.d/default.conf`:

```nginx
server {
    listen 443 ssl;
    server_name localhost;
    ssl_certificate /certificates/public.crt;
    ssl_certificate_key /certificates/private.key;
    root /usr/share/nginx/html;
    index index.html;

    gzip on;
    gzip_types text/css application/javascript application/json;

    location ~ ^/(login|teachers|subjects|curricula|organizational-units|me|opinions|students|groups|admin)(/|$) {
        proxy_pass https://app:8000;
        proxy_ssl_verify on;
        proxy_ssl_trusted_certificate /certificates/ca.pem;
        proxy_ssl_name app;
        proxy_ssl_server_name on;
        proxy_ssl_protocols TLSv1.3;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

Serwer nasłuchuje wyłącznie na porcie 443 z TLS, a blok dla portu 80 nie istnieje, więc nie ma nieszyfrowanej wersji aplikacji. Zwykłe żądanie HTTP jest odrzucane odpowiedzią `400 Bad Request`.

![[Pasted image 20261115022335.png]]

*Odpowiedź nginx na żądanie HTTP*

Certyfikat i klucz to para wygenerowana dla Neo4j (5.1.1), zawierająca nazwę `localhost`. Ponieważ jest podpisana lokalnym CA z mkcert, przeglądarka wyświetla stronę bez ostrzeżeń.

![[Pasted image 20261115022652.png]]
*Aplikacja kliencka pod adresem https://localhost:5173 z informacją o poprawnym certyfikacie*

Pierwszy blok `location` obejmuje ścieżki API. Końcówka `(/|$)` dopasowuje samą ścieżkę (`/teachers`) i jej podścieżki (`/teachers/42`), ale nie np. `/teachersXYZ`. Blok z wyrażeniem regularnym ma pierwszeństwo przed prefiksem `/` [CYTOWANIE: https://nginx.org/en/docs/http/ngx_http_core_module.html#location], więc żądania API zawsze trafiają do proxy.

Samo `https` w `proxy_pass` włącza szyfrowanie, ale nginx domyślnie nie weryfikuje certyfikatu serwera docelowego [CYTOWANIE: https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_ssl_verify]. Byłaby to sytuacja analogiczna do `bolt+ssc` z 5.1.4: połączenie szyfrowane, ale bez pewności, z kim. Dlatego `proxy_ssl_verify` włącza weryfikację, `proxy_ssl_trusted_certificate` wskazuje lokalne CA, a `proxy_ssl_name` i `proxy_ssl_server_name` określają i przekazują w SNI nazwę `app` sprawdzaną w certyfikacie API. Połączenie ograniczono do TLS 1.3, ponieważ obie strony są pod kontrolą projektu. Nagłówki `proxy_set_header` przekazują do API dane oryginalnego żądania (host, adres IP klienta, protokół), które inaczej zostałyby utracone na proxy.

Drugi blok obsługuje aplikację jednostronicową (ang. *Single Page Application*, SPA), w której routing odbywa się w przeglądarce. Adresy widoków, np. `/student/plan`, nie odpowiadają plikom na serwerze, więc `try_files` zwraca w takim przypadku `index.html` [CYTOWANIE: https://router.vuejs.org/guide/essentials/history-mode.html]. Bez tego odświeżenie strony kończyłoby się błędem 404.

W `docker-compose.yml` argument `NPM_REGISTRY` korzysta ze składni `${ZMIENNA:-domyślna}`. W przeciwieństwie do `:?` z 5.1.5 brak zmiennej nie blokuje uruchomienia, tylko powoduje użycie publicznego rejestru [CYTOWANIE: https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/].

Port 443 jest przekierowany na port 5173 hosta, domyślny port serwera deweloperskiego Vite, i tak jak w pozostałych serwisach powiązany wyłącznie z `127.0.0.1`. Bez tego Docker opublikowałby port na wszystkich interfejsach, z pominięciem zapory hosta [CYTOWANIE: https://docs.docker.com/engine/network/packet-filtering-firewalls/], a i tak certyfikat obejmuje tylko `localhost`.

Montowane są wyłącznie trzy potrzebne pliki: `public.crt`, `private.key` i `ca.pem`. Zamontowanie całego katalogu `certificates` dałoby kontenerowi dostęp do klucza prywatnego API, wbrew zasadzie najmniejszych uprawnień z 5.1.1.

```shell
(.venv) ➜  INZYNIERKA_FINAL git:(master) ✗ docker compose exec frontend ls /certificates
ca.pem       private.key  public.crt
```

*Wynik `docker compose exec frontend ls /certificates`*

`depends_on: app` oznacza jedynie, że kontener `app` musi być utworzony, ponieważ nginx przy starcie rozwiązuje jego nazwę. Żądania wysłane, zanim uvicorn zacznie nasłuchiwać, otrzymają `502 Bad Gateway`.

Kontener ma nałożone ograniczenia analogiczne do serwisu `app`, dostosowane do nginx, którego proces główny działa jako `root`, a procesy obsługujące żądania jako użytkownik `nginx`:
- `read_only: true` – atakujący nie może podmienić konfiguracji ani plików aplikacji klienckiej, np. by wstrzyknąć złośliwy skrypt.
- `tmpfs` – nginx wymaga zapisywalnych katalogów `/var/cache/nginx` (bufory proxy) i `/var/run` (plik PID).
- `cap_drop: ALL` z `cap_add` – przywrócone są tylko uprawnienia niezbędne nginx [CYTOWANIE: https://man7.org/linux/man-pages/man7/capabilities.7.html]: `NET_BIND_SERVICE` (port 443), `SETUID` i `SETGID` (przełączenie na użytkownika `nginx`) oraz `CHOWN` (własność katalogów tymczasowych). Bez `CHOWN` nginx nie uruchamia się.
- `no-new-privileges:true` – jak w 5.1.5.

We wdrożeniu produkcyjnym można by użyć obrazu `nginxinc/nginx-unprivileged`, działającego w całości jako zwykły użytkownik na porcie powyżej 1024, co pozwoliłoby odebrać wszystkie uprawnienia jądra.

5.2 Struktura repozytorium

```
.
├── app
│   ├── graph_backend
│   │   ├── auth
│   │   └── routers
│   ├── schemas
│   └── database.py
├── certificates
│   ├── app
│   ├── bolt
│   └── https
├── endpoint_schema
├── frontend
│   ├── Dockerfile
│   ├── nginx.conf
│   └── src
├── import
│   ├── edges
│   └── nodes
├── queries
├── .env.example
├── certs.sh
├── docker-compose.yml
├── Dockerfile
├── init.sh
└── requirements.txt
```

Klient Vue jest w całości zawarty w katalogu `frontend/`, wraz z plikiem `Dockerfile` budującym jego obraz i konfiguracją serwera nginx (`nginx.conf`), który go serwuje.

W katalogu `app/` znajduje się backend, w tym warstwa API. Plik `database.py` tworzy połączenie z bazą Neo4j za pomocą sterownika. W podkatalogu `schemas/` zdefiniowano modele Pydantic, opisujące oczekiwany kształt żądań i odpowiedzi serwera, a w podkatalogu `graph_backend/` – backend grafowy. Punkty końcowe znajdują się w `routers/`, pogrupowane według ról użytkowników, uwierzytelnianie i autoryzacja w `auth/`, a zapytania do bazy danych w pozostałych modułach.

*todo* W tym samym katalogu, w podkatalogu `relation_backend/`, znajdzie się implementacja relacyjna podobnego systemu. Będzie ona działać w ten sam sposób – poprzez sterownik bazy danych zamiast mapowania obiektowo-relacyjnego. Oba backendy będą korzystać z tych samych modeli Pydantic.

Ponieważ eksploracja bazy danych jest szczególnym celem tej pracy, poświęcono jej dużą część repozytorium. Katalog `import/` zawiera dane początkowe, a katalog `queries/` – instrukcje w języku Cypher wykonywane przy inicjalizacji bazy danych przez skrypt `init.sh` (5.3). Katalog `endpoint_schema/` zawiera dokumentację punktów końcowych API (5.4).

Katalog `certificates/` jest tworzony przez skrypt `certs.sh` (5.1.1). Zawiera certyfikaty TLS dla API (`app/`) oraz dla połączeń z bazą danych przez protokół Bolt (`bolt/`) i HTTPS (`https/`).

Dane dostępowe (hasła do bazy danych i klucz podpisujący tokeny) przechowywane są w pliku `.env`.Wymagane zmienne opisano w pliku `.env.example`.

5.3 Inicjalizacja i schemat bazy danych

W katalogu `import/` znajdują się dane w formacie CSV (ang. *Comma-Separated Values*), importowane przy inicjalizacji bazy danych – `nodes/` zawiera węzły, a `edges/` krawędzie. Na każdy typ węzła i na każdy typ krawędzi przypada osobny plik. Wyjątkiem jest etykieta User – dane logowania (adres e-mail i skrót hasła) są kolumnami w plikach studentów, prowadzących i administratorów, a etykieta nadawana jest przy imporcie tym osobom, które mają podany adres e-mail.

Skrypt `init.sh` wykonuje kolejno instrukcje z katalogu `queries/`: `schema.cypher` narzuca kształt węzłów i krawędzi oraz pozostałe ograniczenia, `nodes.cypher` i `edges.cypher` wczytują pliki CSV z węzłami i krawędziami, a `security.cypher` tworzy konto bazodanowe, którym łączy się API (4.4.3).

Definicja typu grafu w `schema.cypher` jest zapisana w wersji Cypher 25 (`CYPHER 25 ALTER CURRENT GRAPH TYPE SET ...`), ponieważ ta funkcja jest dostępna wyłącznie w tej wersji języka. Pozostałe zapytania, zarówno importujące, jak i wykonywane przez API, korzystają z domyślnej wersji języka skonfigurowanej w bazie.

5.3.1 Schema

Plik `schema.cypher` jest ładowany do bazy danych jako pierwszy, poleceniem `cypher-shell` opisanym w 5.1.4. Definiuje on typ grafu (ang. *graph type*), czyli opis dopuszczalnego kształtu węzłów i krawędzi. Typ grafu pozwala określić typy danych właściwości, wymagać ich istnienia oraz narzucić inne ograniczenia, takie jak klucze i unikalność. Funkcja ta jest dostępna wyłącznie w wersji Enterprise Neo4j, co było jednym z powodów wyboru obrazu `neo4j:2026.07.1-enterprise` (5.1.3).

Dla każdego przewidzianego typu węzła powstało w tym pliku odpowiadające mu ograniczenie. Jako przykład posłuży definicja węzła grupy (Group):

```cypher
	(g:Group => {
		id :: STRING,
		weekday :: INTEGER NOT NULL,
		number :: INTEGER NOT NULL,
		pnp :: STRING NOT NULL,
		capacity :: INTEGER NOT NULL,
		start_time :: ZONED TIME NOT NULL,
		end_time :: ZONED TIME NOT NULL
	}) REQUIRE g.id IS KEY,
```

Zgodnie z projektem systemu węzeł grupy przechowuje identyfikator, dzień tygodnia, numer grupy, parzystość tygodni, w których odbywają się zajęcia, pojemność grupy oraz godziny rozpoczęcia i zakończenia zajęć.

Identyfikator (`id`) jest typu `STRING`, nie bardziej intuicyjnego `INTEGER`, ponieważ Neo4j nie obsługuje autoinkrementacji. Identyfikatory liczbowe wymagałyby osobnego, globalnego mechanizmu ich nadawania, z którego korzystałyby wszystkie zapytania tworzące nowe węzły. Alternatywą byłoby wyszukanie w grafie największego istniejącego identyfikatora i zwiększenie go o 1, lecz takie rozwiązanie jest podatne na wyścigi – dwie równoległe transakcje mogą odczytać tę samą wartość i nadać ten sam identyfikator. O wbudowaną autoinkrementację użytkownicy Neo4j proszą co najmniej od 2013 roku [CYTOWANIE: https://gist.github.com/tekiegirl/8012859].

Do tego celu nie nadaje się również wewnętrzny identyfikator elementu, zwracany przez funkcję `elementId()`. Dokumentacja Neo4j zastrzega, że poza pojedynczą transakcją nie ma żadnych gwarancji co do powiązania identyfikatorów z elementami, a identyfikatory usuniętych węzłów i krawędzi są ponownie wykorzystywane [CYTOWANIE: https://neo4j.com/docs/cypher-manual/current/functions/scalar/]:

> *Neo4j reuses its internal IDs when nodes and relationships are deleted. Applications relying on internal Neo4j IDs are, as a result, brittle and can be inaccurate. It is therefore recommended to use application-generated IDs.*

(tłum.: Neo4j ponownie wykorzystuje wewnętrzne identyfikatory po usunięciu węzłów i krawędzi. W związku z tym aplikacje polegające na wewnętrznych identyfikatorach Neo4j są kruche i mogą działać niepoprawnie. Dlatego zaleca się stosowanie identyfikatorów generowanych przez aplikację.)

Problemy te rozwiązuje zastąpienie identyfikatorów liczbowych identyfikatorami UUID (ang. *Universally Unique Identifier*). Wygenerowanie UUID nie wymaga przechowywania stanu ani znajomości identyfikatorów istniejących już w bazie. Cypher udostępnia do tego funkcję `randomUUID()`, która według dokumentacji zwraca „128-bitową wartość z silnymi gwarancjami unikalności” (ang. *a 128-bit value with strong guarantees of uniqueness*) [CYTOWANIE: https://neo4j.com/docs/cypher-manual/current/functions/scalar/]. W tym projekcie UUID jest identyfikatorem prawie wszystkich typów węzłów. Podobne stanowisko pojawia się na forum społeczności Neo4j, gdzie jeden z użytkowników, odradzając liczbową autoinkrementację, pisze [CYTOWANIE: https://community.neo4j.com/t/how-to-auto-increment-to-get-unique-value-for-a-new-nodes-field/12815/7]:

> *Database engines must prioritize performance and stability first, flexibility second, and convenience third. Your solution puts convenience first.*

(tłum.: Silniki baz danych muszą stawiać na pierwszym miejscu wydajność i stabilność, na drugim elastyczność, a dopiero na trzecim wygodę. Twoje rozwiązanie stawia wygodę na pierwszym miejscu.)

Właściwości `weekday`, `number` i `capacity` są liczbami całkowitymi. W przypadku `number` i `capacity` nie budzi to wątpliwości, natomiast `weekday` naturalniej byłoby zapisać jako typ wyliczeniowy (ang. *enum*), dostępny w większości współczesnych języków programowania, a także w relacyjnych bazach danych, np. PostgreSQL [CYTOWANIE: https://www.postgresql.org/docs/current/datatype-enum.html]. Neo4j nie obsługuje jednak typów wyliczeniowych i nie pozwala ograniczyć zbioru dopuszczalnych wartości właściwości z poziomu bazy danych, dlatego poprawność dnia tygodnia sprawdzana jest w warstwie aplikacji – model żądania utworzenia grupy (`GroupCreateRequest`) przyjmuje wyłącznie wartości od 1 do 7.

Innym możliwym rozwiązaniem byłoby utworzenie pseudo-typu wyliczeniowego z węzłów. Zamiast właściwości `weekday: 1` powstałoby siedem węzłów odpowiadających dniom tygodnia (`"Monday"`, `"Tuesday"` itd.), połączonych z węzłem Group krawędzią, np. `HAPPENS_ON`. Wadą tego rozwiązania jest to, że odczytanie podstawowych informacji o grupie wymagałoby dodatkowego kroku przejścia po grafie. Ponadto baza danych nie wymusza istnienia krawędzi (4.3.7), więc dopuściłaby utworzenie grupy bez dnia tygodnia.

Uznano, że dzień tygodnia jest zbyt prostą informacją, by wydzielać go do osobnego węzła. Inaczej potraktowano sale, w których odbywają się zajęcia – są one osobnymi węzłami (Room), połączonymi z grupą krawędzią `IN_ROOM`:

```cypher
	(g)-[:IN_ROOM => {}]->(r),
```

Sala, w przeciwieństwie do dnia tygodnia, jest samodzielnym bytem: ma własne właściwości (budynek i numer sali), w jednej sali odbywa się wiele grup, a zbiór sal zmienia się w czasie – powstają nowe budynki, a istniejące sale są wyłączane z użytku. Gdyby budynek i numer sali były właściwościami grupy, zmiana danych sali wymagałaby aktualizacji wszystkich odbywających się w niej grup, a literówka w nazwie budynku tworzyłaby w praktyce nową salę. Jako osobny węzeł sala jest zapisana w jednym miejscu, a ograniczenie unikalności pary budynek–numer sali (`REQUIRE (r.building, r.room_num) IS UNIQUE`) chroni przed duplikatami.

Zbiór dni tygodnia natomiast się nie zmieni: jest to siedem kolejnych wartości, zrozumiałych dla każdego. Trzeba jedynie ustalić konwencję numeracji, ponieważ w zależności od kraju i systemu tydzień zaczyna się w poniedziałek albo w niedzielę. W projekcie przyjęto, że 1 oznacza poniedziałek, a 7 – niedzielę. Jest to decyzja autora, zgodna z jednym ze standardów – normą ISO 8601, w której tydzień rozpoczyna się w poniedziałek, oznaczony numerem 1 [CYTOWANIE: ISO 8601-1:2019]. Tę samą numerację stosuje Neo4j: dokumentacja typów czasowych opisuje składową `dayOfWeek` jako wartość od 1 do 7, przy czym „pierwszym dniem tygodnia jest poniedziałek” (ang. *the first day of the week is Monday*) [CYTOWANIE: https://neo4j.com/docs/cypher-manual/current/values-and-types/temporal/].

Właściwość `pnp`, określająca parzystość tygodni, w których odbywają się zajęcia, również skorzystałaby na typie wyliczeniowym. Przyjmuje ona jedną z trzech wartości tekstowych: `"P"` (tygodnie parzyste), `"NP"` (tygodnie nieparzyste) oraz `"ALL"` (co tydzień). Parzystość wyznaczana jest na podstawie numeru tygodnia według normy ISO 8601. Tę samą informację mogłyby przechowywać trzy liczby (`0`, `1`, `2`), jednak bez typu wyliczeniowego byłyby to liczby magiczne (ang. *magic numbers*) – programista rozwijający aplikację łatwo mógłby pomylić, czy 0 oznacza tygodnie parzyste, czy nieparzyste. Wartości tekstowe są czytelne same w sobie, a ich poprawność, podobnie jak w przypadku dnia tygodnia, sprawdza warstwa aplikacji – model `GroupCreateRequest` przyjmuje wyłącznie jedną z trzech wymienionych wartości. Rozwiązanie to nie jest w pełni zadowalające, ponieważ sama baza danych nie chroni się przed niepoprawną wartością, ale jest najlepszym, na jakie pozwala Neo4j.

Poza kształtem samego węzła Group typ grafu określa również, jakie krawędzie mogą łączyć grupę z innymi węzłami: `IN_ROOM` (grupa -> sala), `OF_TYPE` (grupa -> typ grupy), `ABOUT` (opinia -> grupa), `REGISTERED_IN` (student -> grupa), `OPENS` (rejestracja -> grupa) oraz `TEACHES` (prowadzący -> grupa). Krawędź `REGISTERED_IN` przechowuje dodatkowo dwie właściwości: `registered_at` typu `ZONED DATETIME` oraz `grade` typu `FLOAT`. W przypadku zapisu istotna jest zarówno data, jak i godzina, a strefa czasowa pozwala jednoznacznie określić ten moment. Ocena jest liczbą zmiennoprzecinkową, ponieważ w skali ocen występują wartości połówkowe (np. 3,5 i 4,5). Właściwość `grade` nie jest oznaczona jako `NOT NULL`, ponieważ student zostaje zapisany do grupy, zanim otrzyma ocenę – do tego czasu wartość pozostaje pusta.

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

Graph type, poza typem danych, określa również, które właściwości są wymagane. Sama deklaracja `nazwa :: TYP` jedynie wymusza typ, jeśli właściwość występuje. Jej istnienie wymusza dopiero modyfikator `NOT NULL`. Wpis `REQUIRE g.id IS KEY` sprawia, że identyfikator grupy musi istnieć i dodatkowo musi być unikatowy.

Ograniczenie typu `KEY` jest równoważne połączeniu ograniczenia unikalności (`IS UNIQUE`) z ograniczeniem istnienia (`IS NOT NULL`) na tym samym zbiorze właściwości [CYTOWANIE: https://neo4j.com/docs/cypher-manual/current/schema/constraints/]:

```cypher
CREATE CONSTRAINT group_id_exists FOR (g:Group) REQUIRE g.id IS NOT NULL;
CREATE CONSTRAINT group_id_unique FOR (g:Group) REQUIRE g.id IS UNIQUE;
```

Group jest węzłem przechowującym najwięcej informacji. Pozostałe węzły służące do definiowania domeny uczelnianej są skonstruowane w bardzo podobny sposób – typy danych określone w projekcie systemu są tłumaczone na typy danych dostępne w silniku Neo4j, a dodatkowe ograniczenia są nakładane analogicznie. Następnie, jeśli między węzłami mają istnieć krawędzie, są one również definiowane.

Wszystko przebiegłoby zgodnie z założeniami projektowymi, gdyby nie pewne ograniczenie mechanizmu graph type. Według dokumentacji (oraz błędu wielokrotnie napotkanego przez autora) nie jest możliwe zdefiniowanie typu węzła, który nie posiada żadnych właściwości ani nie implikuje żadnej etykiety [CYTOWANIE: https://neo4j.com/docs/cypher-manual/25/schema/graph-types/set-graph-types/]. Węzeł SubjectInstance, który zgodnie z projektem nie potrzebuje absolutnie żadnej właściwości, nie może więc otrzymać własnego typu węzła. Próba takiej definicji kończy się błędem 22NC2 – „data exception – node element type has no effect” [CYTOWANIE: https://neo4j.com/docs/status-codes/current/errors/gql-errors/22NC2/].

Surowy komunikat błędu zwracany przez Neo4j (wersja 2026.07.1 Enterprise) przy próbie zdefiniowania węzła bez właściwości:

```cypher
CYPHER 25 ALTER CURRENT GRAPH TYPE SET { (si:SubjectInstance => {}) }
```

```shell
22NC2: data exception - node element type has no effect. The node element type `SubjectInstance` must contain one or more implied labels, or at least one property type.
  42001: syntax error or access rule violation - invalid syntax
```

Pierwszym obejściem, jakie się nasuwa, jest nadanie węzłowi sztucznego identyfikatora, np. `id :: STRING` z ograniczeniem `IS KEY`. Taka właściwość nie byłaby jednak do niczego wykorzystywana – węzeł i tak jest zawsze odnajdywany poprzez krawędzie łączące go z przedmiotem i cyklem akademickim – a wprowadzałaby do modelu informację, której projekt nie przewiduje. Węzeł, którego jedyną rolą jest łączenie innych węzłów krawędziami, jest w pełni poprawnym elementem modelu grafowego, a wymuszenie istnienia w nim właściwości lub implikowanej etykiety nie wnosi do schematu żadnej informacji.

Zamiast tego SubjectInstance nie otrzymała typu węzła wcale. Etykieta pojawia się w typie grafu wyłącznie jako początek krawędzi, które z niej wychodzą:

```cypher
	(:SubjectInstance)-[:INSTANCE_OF => {}]->(su),
	(:SubjectInstance)-[:OFFERED_IN => {}]->(ac),
	(:SubjectInstance)-[:HAS_TYPE => {}]->(gt),
```

Pozostałe węzły i krawędzie opisujące model uczelni nie napotkały podobnego problemu, ponieważ każdy z nich miał uzasadnione właściwości. Jeszcze inny problem pojawił się jednak w modelowaniu ludzi korzystających z platformy.

Jak wspomniano wcześniej, wykorzystano etykiety implikowane i wieloetykietowość, żeby każda osoba pracująca na uczelniioraz student musieli być człowiekiem.

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

Jak widać, w etykietach Teacher, Student, User i Inactive są przechowywane jedynie właściwości ekskluzywne dla tej roli. Admin nie niesie ze sobą żadnych dodatkowych informacji, zatem jedynie implikuje Person. Jest to dozwolony zabieg.

Problem pojawia się dopiero w samej definicji etykiety Person. Wygodne i oczywiste byłoby zdefiniowanie jej jako na przykład:

```cypher
 (p:Person => {
	 idx :: STRING,
	 name :: STRING NOT NULL,
	 surname :: STRING NOT NULL,
	 phone :: STRING NOT NULL,
	 photo :: STRING
 }) REQUIRE p.idx IS KEY,
```

Okazuje się, że próba zdefiniowania etykiet w ten sposób powoduje błąd 22NC4 [CYTOWANIE: https://neo4j.com/docs/status-codes/current/errors/gql-errors/22NC4/], dokładnie: 

```shell
  22NC4: data exception - a label cannot be both identifying and implied. The label(s) `Person` are defined as both identifying and implied. (line 
  2, column 20 (offset: 60))                                                       "    (t:Teacher => :Person {"                                                                                                                
                      ^                                                              42001: syntax error or access rule violation - invalid syntax
```

Jeśli w poleceniu graph type etykieta jest w ogóle zdefiniowana, to staje się ona identyfikująca. Jeśli jest ona identyfikująca, to jednocześnie nie może być implikowana, co zupełnie psuje mechanizm zaplanowany wcześniej.

Sposobem na ominięcie tego mechanizmu proponowanym przez Neo4j w opisie tego błędu jest zastąpienie definicji z graph type zwykłymi instrukcjami CONSTRAINT. Z racji tego, że wspólna etykieta, pseudo-klasa bazowa była potrzebna, etykieta Person jest zdefiniowana w postaci listy ograniczeń.

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
    g.start_time = time(row.start_time),
    g.end_time = time(row.end_time);
```

Zaczyna się od instrukcji `LOAD CSV WITH HEADERS FROM "file:///nodes/groups.csv" AS row`. Odczytuje ona plik wiersz po wierszu, a każdy wiersz udostępnia jako zmienną `row`. Zmienna ta jest mapą, w której kluczami są nazwy kolumn z nagłówka, a wartościami – zawartość odpowiadających im komórek w postaci tekstu. Pozostała część zapytania wykonywana jest osobno dla każdego wiersza.

Zawartość `groups.csv` zaczyna się od:

```csv
id,weekday,number,pnp,capacity,start_time,end_time
131f00c2-a504-550e-8117-167bd6218535,3,1,NP,120,13:15:00+02:00,15:00:00+02:00
74e99473-12fb-5919-9992-db58d514944b,3,1,P,120,13:15:00+02:00,15:00:00+02:00
f1421862-5912-57ee-a1d6-cb357169c3fc,1,1,ALL,120,15:15:00+02:00,16:55:00+02:00
3e1d2221-1124-533d-8e5b-cd97e997453d,4,1,ALL,16,17:05:00+02:00,19:40:00+02:00
```

Plik zawiera więc wszystkie nazwane kolumny konieczne do utworzenia grupy zajęciowej.

Instrukcja `MERGE (g:Group {id: row.id})` szuka węzła z etykietą Group, którego właściwość `id` jest równa wartości kolumny `id` w bieżącym wierszu. Jeśli taki węzeł już istnieje, zostaje przypisany do zmiennej `g`, a jeśli nie, instrukcja go tworzy i dopiero wtedy przypisuje.

Następnie blok instrukcji `SET` ustawia pozostałe właściwości węzła na wartości z pliku. Dzięki temu, jeśli dane w plikach .csv ulegną zmianie, węzły zostaną zaktualizowane przy ponownej inicjalizacji. Zawartość pliku jest odczytywana jako tekst, zatem zapisanie wartości jako czasu lub liczby całkowitej wymaga wywołania wbudowanych funkcji, takich jak `time()` bądź `toInteger()`.

Na koniec instrukcja zamyka się średnikiem. Każde polecenie zakończone średnikiem `cypher-shell` wykonuje w osobnej transakcji, zatem jeśli w którymś z nich wystąpi błąd, zmiany wprowadzone przez wcześniejsze polecenia pozostaną zapisane. Nie stanowi to problemu, ponieważ dzięki użyciu `MERGE` zamiast `CREATE` ponowne uruchomienie importu po usunięciu przyczyny błędu nie utworzy duplikatów.

Gdyby import miał się wykonać w całości albo wcale, można objąć wszystkie polecenia jedną jawną transakcją, umieszczając w pliku przed nimi instrukcję `:begin`, a po nich `:commit` [CYTOWANIE: https://neo4j.com/docs/operations-manual/current/cypher-shell/]. Błąd w dowolnym poleceniu wycofałby wtedy również zmiany wprowadzone przez polecenia wcześniejsze. W projekcie z tej możliwości nie skorzystano, ponieważ przy imporcie opartym na `MERGE` częściowo wykonany import nie pozostawia bazy w stanie, którego nie dałoby się naprawić ponownym uruchomieniem skryptu.

Innym sposobem na osiągnięcie tego samego efektu jest usunięcie średników. Nie jest to jednak sposób dobry. Wszystkie polecenia stałyby się wtedy jednym zapytaniem, w którym kolejne `LOAD CSV` wykonuje się osobno dla każdego wiersza poprzedniego pliku – dla 3 kierunków i 11 planów studiów zapytanie przetwarza 33 wiersze zamiast 14. Ponowne użycie nazwy `row` nie powoduje przy tym jawnego błędu, ale tworzy zachowanie nieoczeniwane. Zmienna nadal wskazuje na wiersz pierwszego pliku. W efekcie poniższe zapytanie próbuje utworzyć plan studiów z identyfikatorem kierunku i bez roku naboru:

```cypher
LOAD CSV WITH HEADERS FROM "file:///nodes/programmes.csv" AS row
MERGE (p:Programme {id: row.id})
SET p.name = row.name

LOAD CSV WITH HEADERS FROM "file:///nodes/curriculums.csv" AS row
MERGE (c:Curriculum {id: row.id})
SET c.intake_year = row.intake_year;
```

Zatrzymuje je dopiero ograniczenie typu grafu, wymagające istnienia właściwości `intake_year`:

```
22N77: data exception - property presence verification failed. NODE (563) with label 'Curriculum' must have the following properties: `intake_year`.
```

Bez zdefiniowanego typu grafu zapytanie zakończyłoby się powodzeniem i zapisało w bazie błędne węzły. Rozwiązaniem mogłoby być nazywanie każdej zmiennej odpowiadającej plikowi .csv w inny sposób, czyli jeden `row` importujący grupę nazywałby się `g_row`, dla cyklu akademickiego `ac_row` i tak dalej, zachowując unikatowość dla każdego pliku. Chociaż to działa, to jest bardzo niewygodne i nieeleganckie. 

W podobny sposób przebiega import większości pozostałych węzłów. Wyjątek stanowią węzły dotyczące nauczycieli i studentów. Wynika to z tego, że każda z tych osób na pewno jest osobą (Person), ale jednocześnie może być użytkownikiem (User). W plikach .csv przechowywane są wszystkie informacje na temat ludzi, wraz z tymi opcjonalnymi. 

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

Początek instrukcji jest podobny, jak wcześniej - do zmiennej `row` są po kolei ładowane wszystkie wiersze z nagłówkami określającymi klucze w mapie. 

```csv
idx,name,surname,phone,photo,joined,email,passwd_hash
285903,Maja,Król,607216739,,2025-10-01T00:00:00+01:00,285903@student.pwr.edu.pl,$2bHIDDEN
285904,Filip,Wieczorek,610000007,285904.jpg,2025-10-01T00:00:00+01:00,,
283501,Aleksandra,Jabłońska,605126225,,2024-10-01T00:00:00+01:00,283501@student.pwr.edu.pl,$2HIDDEN
```

W przykładowym fragmencie pliku widać, że nie każdy student ma zdjęcie, a przede wszystkim nie każdy student ma adres e-mail i hash hasła. Bez danych do logowania nie da się utworzyć etykiety User. 

Podobnie jak wcześniej, instrukcja `MERGE` szuka węzła Student, jednocześnie Person, o wartości `idx` równej tej z `row`.  Jeśli taki istnieje, to przypisuje go do `st`. Jeśli nie, to go tworzy z tymi dwoma etykietami i wtedy przypisuje. Wymagane właściwości, a także opcjonalna właściwość `photo`, są ustawiane w instrukcji `SET`.

Na uwagę zasługuje podzapytanie `CALL (row, st) { ... }`, któremu przekazywane są zmienne `row` i `st`. Wewnątrz niego znajduje się zapytanie warunkowe `WHEN ... THEN`, dostępne w wersji Cypher 25 [CYTOWANIE: https://neo4j.com/docs/cypher-manual/current/queries/composed-queries/conditional-queries/]. Sprawdza ono, czy e-mail jest ustawiony, a jeśli jest, to przypisuje Studentowi etykietę User, wraz z którą obowiązkowo ustawia właściwości `email` i `passwd_hash`. Gdy warunek nie jest spełniony, to nie dzieje się nic - Student pozostaje jedynie Studentem bez Usera.

Bardzo podobny wzorzec jest wykorzystywany w imporcie nauczycieli (Teacher). Podzapytanie do ustawiania etykiety User wygląda tak samo, jedynie różni się nazwą zmiennej przekazywanej do pod-kwerendy - zamiast `CALL (row, st)` widnieje `CALL (row, t)`, co oczywiście wynika z tego, że modyfikowany jest nauczyciel, nie student.

5.3.3 Import krawędzi
Mając węzły należy je ze sobą połączyć. Służą ku temu krawędzie, również przechowywane w pliku .csv. 


5.4 Dokumentacja

Katalog `endpoint_schema/` zawiera dokumentację punktów końcowych API: dozwolone role, kształt żądań i odpowiedzi oraz wykonywane zapytania bazodanowe. Ponadto API generuje interaktywną dokumentację w standardzie OpenAPI [CYTOWANIE: https://fastapi.tiangolo.com/reference/openapi/docs/], na podstawie tych samych modeli, które służą do walidacji.

5.5 API

Na podstawie modeli Pydantic API sprawdza poprawność danych wejściowych i formatuje dane wyjściowe. Obsługa żądania przebiega następująco: API odbiera żądanie na wybranym punkcie końcowym, weryfikuje token i uprawnienia użytkownika, otwiera sesję bazy danych, a następnie – jeśli wykorzystywany jest backend grafowy – wykonuje zapytanie w języku Cypher, przekształca jego wynik do oczekiwanego kształtu i zwraca go klientowi. Zapytania wykonywane są bezpośrednio przez oficjalny, asynchroniczny sterownik Neo4j dla języka Python [CYTOWANIE: https://neo4j.com/docs/api/python-driver/current/].

5.6 Klient