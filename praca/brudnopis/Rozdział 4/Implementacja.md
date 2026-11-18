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

Żeby połączenie między bazą a API było odporne na podsłuch, wprowadzono szyfrowanie poprzez TLS/SSL. W związku z tym, że SSL jest włączony z Bolt, URI zmienia się z `bolt` na `bolt+s`. Certyfikaty opisano w 5.1.1, a wady alternatywnego schematu `bolt+ssc` w 5.1.4.

Pozostałe porty domyślnie włączone na instancjach Neo4j, takie jak "Cluster routing connector" czy "Remote debugging" uznano za niepotrzebne. W związku z tym, że nie są one potrzebne, to nie powinny być wystawiane.

Konfiguracja bazowego obrazu Neo4j odbywa się poprzez ustawianie zmiennych środowiskowych. Poza wcześniej wymienioną zmienną potrzebną do akceptowania licencji enterprise, należało włączyć szyfrowanie (https i bolt+s), wyłączyć domyślnie włączone, niebezpieczne protokoły (http), przekazać katalog z zaufanymi certyfikatami, a także przekazać dane do inicjalizacji konta administratora, wyciągane z `.env`.

Wolumeny zamontowane w ramach tego serwisu to `neo4j_data`, `import` i `certificates`. Certyfikaty są konieczne do wdrożenia szyfrowania SSL/TLS. Import zawiera dane, które będą importowane do bazy danych po tym, jak ta wstanie. neo4j_data służy do przechowywania danych w samej bazie już po inicjalizacji, w tym zmian wprowadzonych na żywej instancji pomiędzy uruchomieniami kontenera.

Ostatnim elementem kontenera będzie healthcheck, który będzie warunkiem uruchomienia innych serwisów polegających na bazie danych. Obywa się on po minucie co 30s z timeoutem 10s w pięciu próbach. Po pięciu próbach compose wyrzuci error.

5.1.4 Serwis init

Neo4j nie ma możliwości uruchomienia skryptu inicjalizacyjnego po uruchomieniu bazy danych. Zdecydowano zatem, że do importu danych i innych niezbędnych operacji będzie służył osobny serwis nazwany `init`. 

Polega on na tym samym obrazie, co serwis neo4j. Zdecydowano się na takie rozwiązanie, ponieważ do inicjalizacji jest potrzebne narzędzie cypher-shell, które już jest w tym obrazie. Oznacza to też mniej pobierania, bo bazowy obraz neo4j i tak na pewno już jest.

Serwis init polega na serwisie neo4j, czyli uruchomi się dopiero, gdy tamten będzie w stanie "zdrowym" (ang. *healthy*). Zdrowie serwisu jest sprawdzane healthcheck opisanym wcześniej.

Zmienne przekazane do kontenera to adres bazy danych (port 7687 po `bolt+s` dla adresu kontenera `neo4j`) oraz dane do logowania administratora i użytkownika. Dane administratora są potrzebne do inicjalizacji schemy, w tym ograniczeń, a także zapełnienia bazy danymi przygotowanymi w plikach .csv. Login i hasło użytkownika są potrzebne do stworzenia konta z ograniczonymi uprawnieniami, którym baza danych będzie się komunikowała z API.

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

Konfiguracja serwisu w `docker-compose.yml` znajduje się w 5.1.2.

`build: .` buduje obraz z opisanego wyżej `Dockerfile`, znajdującego się w katalogu głównym projektu.

Aplikacja wystawiona na porcie 8000 jest również przekierowywana na port 8000 localhost, dzięki czemu API jest widoczne dla developera pod adresem `https://localhost:8000/api`. Zwykłe żądanie HTTP na ten port nie otrzymuje odpowiedzi.

![[Pasted image 20261115020127.png]]

*API widoczne z przeglądarki*

> [!todo] [A6] Nowy zrzut ekranu, np. `https://localhost:8000/api/docs`
> Stary zrzut pokazuje API sprzed dodania prefiksu `/api`.

W produkcyjnym wdrożeniu port 8000 w tym kontenerze nie powinien być wystawiony na hosta. Nie jest on potrzebny do działania systemu: z bazą danych połączenie jest wykonywane po `bolt+s://neo4j:7687`, a aplikacja kliencka widzi API poprzez serwer nginx w kontenerze `frontend`, pełniący rolę odwrotnego proxy (ang. *reverse proxy*). Przeglądarka komunikuje się wyłącznie z nginx po HTTPS, w ramach tego samego *origin* co aplikacja kliencka, a nginx przekazuje żądania kierowane do ścieżek zaczynających się od `/api` pod adres `https://app:8000` w wewnętrznej sieci Dockera (5.1.6).

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

Argument `NPM_REGISTRY` pozwala wskazać inny rejestr pakietów npm, np. w sieci z ograniczonym dostępem do publicznego rejestru. Zmienna `VITE_API_URL` jest wstawiana przez Vite do kodu na etapie budowania [CYTOWANIE: https://vite.dev/guide/env-and-mode] i celowo pozostaje pusta, dzięki czemu aplikacja wysyła żądania pod ścieżki względne z prefiksem `/api`, czyli do tego samego serwera nginx.

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

    location /api/ {
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

    location /assets/ {
        try_files $uri =404;
        add_header Cache-Control "public, max-age=31536000, immutable";
    }

    location / {
        try_files $uri $uri/ /index.html;
        add_header Cache-Control "no-cache";
    }
}
```

Serwer nasłuchuje wyłącznie na porcie 443 z TLS, a blok dla portu 80 nie istnieje, więc nie ma nieszyfrowanej wersji aplikacji. Zwykłe żądanie HTTP jest odrzucane odpowiedzią `400 Bad Request`.

![[Pasted image 20261115022335.png]]

*Odpowiedź nginx na żądanie HTTP*

Certyfikat i klucz to para wygenerowana dla Neo4j (5.1.1), zawierająca nazwę `localhost`. Ponieważ jest podpisana lokalnym CA z mkcert, przeglądarka wyświetla stronę bez ostrzeżeń.

![[Pasted image 20261115022652.png]]
*Aplikacja kliencka pod adresem https://localhost:5173 z informacją o poprawnym certyfikacie*

Pierwszy blok `location` obejmuje ścieżki API. Wszystkie punkty końcowe API są udostępniane pod wspólnym prefiksem `/api`, a nginx wybiera blok o najdłuższym pasującym prefiksie [CYTOWANIE: https://nginx.org/en/docs/http/ngx_http_core_module.html#location], więc każde żądanie zaczynające się od `/api/` trafia do proxy, a każde inne do aplikacji klienckiej. Ponieważ `proxy_pass` nie zawiera ścieżki, adres jest przekazywany do API bez zmian, łącznie z prefiksem.

Wcześniejsza wersja konfiguracji wymieniała ścieżki API w wyrażeniu regularnym (`/login`, `/teachers`, `/admin` itd.). Takie rozwiązanie wymagało pamiętania o aktualizacji listy przy każdym nowym zasobie, a przede wszystkim powodowało kolizję adresów: widoki aplikacji klienckiej `/login` i `/admin/...` pasowały do wyrażenia, więc po odświeżeniu strony lub wejściu na nią z linku przeglądarka dostawała odpowiedź API w formacie JSON zamiast aplikacji. Wspólny prefiks rozdziela obie przestrzenie adresów raz na zawsze.

Samo `https` w `proxy_pass` włącza szyfrowanie, ale nginx domyślnie nie weryfikuje certyfikatu serwera docelowego [CYTOWANIE: https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_ssl_verify]. Byłaby to sytuacja analogiczna do `bolt+ssc` z 5.1.4: połączenie szyfrowane, ale bez pewności, z kim. Dlatego `proxy_ssl_verify` włącza weryfikację, `proxy_ssl_trusted_certificate` wskazuje lokalne CA, a `proxy_ssl_name` i `proxy_ssl_server_name` określają i przekazują w SNI nazwę `app` sprawdzaną w certyfikacie API. Połączenie ograniczono do TLS 1.3, ponieważ obie strony są pod kontrolą projektu. Nagłówki `proxy_set_header` przekazują do API dane oryginalnego żądania (host, adres IP klienta, protokół), które inaczej zostałyby utracone na proxy.

Drugi blok obsługuje aplikację jednostronicową (ang. *Single Page Application*, SPA), w której routing odbywa się w przeglądarce. Adresy widoków, np. `/student/plan`, nie odpowiadają plikom na serwerze, więc `try_files` zwraca w takim przypadku `index.html` [CYTOWANIE: https://router.vuejs.org/guide/essentials/history-mode.html]. Bez tego odświeżenie strony kończyłoby się błędem 404.

Wyjątkiem są pliki zbudowanej aplikacji w katalogu `/assets/`. Vite umieszcza w ich nazwach skrót zawartości, np. `CyclesView-D5yd3d5K.js`, więc każda nowa wersja aplikacji ma nowe nazwy plików. Brakujący plik kończy się błędem 404, a nie zwróceniem `index.html`: strona otwarta przed wdrożeniem nowej wersji żąda plików, których już nie ma, a przeglądarka odrzuciłaby otrzymany w ich miejsce dokument HTML jako niepoprawny moduł JavaScript. Ponieważ zawartość pliku o danej nazwie nigdy się nie zmienia, może on być przechowywany w pamięci podręcznej przeglądarki bezterminowo (`immutable`). Sam `index.html`, wskazujący aktualne nazwy plików, nie jest natomiast buforowany (`no-cache`), dzięki czemu po wdrożeniu przeglądarka od razu pobiera nową wersję. Strony otwarte jeszcze przed wdrożeniem obsługuje router aplikacji klienckiej: gdy nie uda się załadować modułu widoku, przeładowuje stronę jeden raz.

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
│   │   ├── routers
│   │   └── database.py
│   └── schemas
├── certificates
│   └── app
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

W katalogu `app/` znajduje się backend, w tym warstwa API. W podkatalogu `schemas/` zdefiniowano modele Pydantic, opisujące oczekiwany kształt żądań i odpowiedzi serwera, niezależne od bazy danych. W podkatalogu `graph_backend/` znajduje się backend grafowy, czyli cały kod zależny od Neo4j. Plik `database.py` tworzy w nim połączenie z bazą za pomocą sterownika, punkty końcowe znajdują się w `routers/`, pogrupowane według ról użytkowników, uwierzytelnianie i autoryzacja w `auth/`, wspólna obsługa błędów w `errors.py`, a zapytania do bazy danych w pozostałych modułach.

*todo* W tym samym katalogu, w podkatalogu `relation_backend/`, znajdzie się implementacja relacyjna podobnego systemu. Będzie ona działać w ten sam sposób – poprzez sterownik bazy danych zamiast mapowania obiektowo-relacyjnego. Oba backendy będą korzystać z tych samych modeli Pydantic.

Ponieważ eksploracja bazy danych jest szczególnym celem tej pracy, poświęcono jej dużą część repozytorium. Katalog `import/` zawiera dane początkowe, a katalog `queries/` – instrukcje w języku Cypher wykonywane przy inicjalizacji bazy danych przez skrypt `init.sh` (5.3). Katalog `endpoint_schema/` zawiera dokumentację punktów końcowych API (5.4).

Katalog `certificates/` jest tworzony przez skrypt `certs.sh` (5.1.1). Zawiera certyfikat lokalnego CA (`ca.pem`), certyfikat i klucz współdzielone przez Neo4j i nginx oraz certyfikat i klucz API (`app/`).

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

Identyfikator (`id`) jest typu `STRING`, nie bardziej intuicyjnego `INTEGER`, ponieważ Neo4j nie obsługuje autoinkrementacji. Identyfikatory liczbowe wymagałyby osobnego, globalnego mechanizmu ich nadawania, z którego korzystałyby wszystkie zapytania tworzące nowe węzły. Alternatywą byłoby wyszukanie w grafie największego istniejącego identyfikatora i zwiększenie go o 1, lecz takie rozwiązanie jest podatne na wyścigi – dwie równoległe transakcje mogą odczytać tę samą wartość i nadać ten sam identyfikator. O wbudowaną autoinkrementację użytkownicy Neo4j proszą co najmniej od 2013 roku [CYTOWANIE: https://gist.github.com/tekiegirl/8012859]. Ten sposób wykorzystano jedynie w punkcie końcowym `GET /admin/people/next-idx`, który podpowiada administratorowi kolejny numer osoby (`idx`). Jest to wyłącznie podpowiedź: jeśli dwóch administratorów otrzyma ten sam numer, drugą próbę utworzenia osoby odrzuci ograniczenie `idx IS KEY`, a API zwróci kod 409.

Do tego celu nie nadaje się również wewnętrzny identyfikator elementu, zwracany przez funkcję `elementId()`. Dokumentacja Neo4j zastrzega, że poza pojedynczą transakcją nie ma żadnych gwarancji co do powiązania identyfikatorów z elementami, a identyfikatory usuniętych węzłów i krawędzi są ponownie wykorzystywane [CYTOWANIE: https://neo4j.com/docs/cypher-manual/current/functions/scalar/]:

> *Neo4j reuses its internal IDs when nodes and relationships are deleted. Applications relying on internal Neo4j IDs are, as a result, brittle and can be inaccurate. It is therefore recommended to use application-generated IDs.*

(tłum.: Neo4j ponownie wykorzystuje wewnętrzne identyfikatory po usunięciu węzłów i krawędzi. W związku z tym aplikacje polegające na wewnętrznych identyfikatorach Neo4j są kruche i mogą działać niepoprawnie. Dlatego zaleca się stosowanie identyfikatorów generowanych przez aplikację.)

Problemy te rozwiązuje zastąpienie identyfikatorów liczbowych identyfikatorami UUID (ang. *Universally Unique Identifier*). Wygenerowanie UUID nie wymaga przechowywania stanu ani znajomości identyfikatorów istniejących już w bazie. Cypher udostępnia do tego funkcję `randomUUID()`, która według dokumentacji zwraca „128-bitową wartość z silnymi gwarancjami unikalności” (ang. *a 128-bit value with strong guarantees of uniqueness*) [CYTOWANIE: https://neo4j.com/docs/cypher-manual/current/functions/scalar/]. W tym projekcie UUID jest identyfikatorem prawie wszystkich typów węzłów. Nowe identyfikatory generuje API funkcją `uuid4()` z biblioteki standardowej Pythona, a dane początkowe mają je zapisane w plikach CSV. Podobne stanowisko pojawia się na forum społeczności Neo4j, gdzie jeden z użytkowników, odradzając liczbową autoinkrementację, pisze [CYTOWANIE: https://community.neo4j.com/t/how-to-auto-increment-to-get-unique-value-for-a-new-nodes-field/12815/7]:

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
Mając węzły należy je ze sobą połączyć. Służą ku temu krawędzie, również przechowywane w plikach .csv. Prawie każdy z nich przechowuje jedynie identyfikatory odpowiednich węzłów, które mają być ze sobą połączone. Przykładem jest `curriculum_terms.csv`, który odpowiada za krawędź `HAS_TERM`

```csv
curriculum_id,term_id
69fa951f-504c-5034-ad7c-e301998a6017,f66570ad-4751-5f8e-9f5a-231975f69cd7
69fa951f-504c-5034-ad7c-e301998a6017,f6af6573-d17f-57c7-a4f2-68e6e089b100
69fa951f-504c-5034-ad7c-e301998a6017,11bf9d83-0f5a-56b2-b99b-3f706379192e
```

Krawędź jest tworzona poprzez instrukcję Cypher, w której szukane są węzły odpowiedniego typu o danym id, a następnie jest tworzona wybrana krawędź między nimi, po kolei dla każdego wiersza pliku .csv:

```cypher
LOAD CSV WITH HEADERS FROM "file:///edges/curriculum_terms.csv" AS row
MATCH (c:Curriculum {id: row.curriculum_id})
MATCH (ct:CurriculumTerm {id: row.term_id})
MERGE (c)-[:HAS_TERM]->(ct);
```

Jedną krawędzi, która wymagała dodatkowego obsłużenia to `REGISTERED_IN`, która dodatkowo przechowywał właściwość `registered_at`, odczytywaną z dokumentu. Drugą taką specjalną zależnością okazało się połaczenie przedmiotu, instancji przedmiotu i cyklu akademickiego. Ponieważ SubjectInstance nie ma trwałego identyfikatora, jest importowane jako "krok" pomiędzy przedmiotem a cyklem akademickim. 

```cypher
LOAD CSV WITH HEADERS FROM "file:///edges/instance_group_types.csv" AS row
MATCH (:Subject {code: row.subject_code})<-[:INSTANCE_OF]-(si:SubjectInstance)-[:OFFERED_IN]->(:AcademicCycle {id: row.cycle_id})
MATCH (gt:GroupType {id: row.group_type_id})
MERGE (si)-[:HAS_TYPE]->(gt);
```

5.3.4 Udany import
Po wykonaniu się pliku `init.sh`, bazę danych można obejrzeć chociażby poprzez konsolę Neo4j wystawioną po HTTPS. Z poziomu konta administrskiego `neo4j` wygląda to następująco:

![[Pasted image 20261116175212.png]]

*Konsola Neo4j z zaimportowanymi elementami*

Możliwy jest również login jako konto użytkowe `app` z ograniczonymi uprawnieniami. Jak widać, nie jest możliwe z tego konta między innymi stworzenie węzła o etykiecie, która nie została zdefiniowana w schemie lub nie ma jej jeszcze w bazie danych. Dla porównania, z konta `neo4j` jest to jak najbardziej możliwe. Broni to przed przyszłymi sytuacjami, w których literówka w kwerendzie po stronie aplikacji może spowodować zapis danych w złym miejscu, który się wykona bez ostrzeżenia.

![[Pasted image 20261116175608.png]]

*Udane stworzenie węzła z etykietą Professor jako użytkownik neo4j*

![[Pasted image 20261116175715.png]]

*Nieudana próba stworzenia węzła z etykietą Janitor jako użytkownik app*

Wszystkie zaimportowane węzły i krawędzie są widoczne po użyciu funkcji `db.schema.visualization()`. Niestety, przez wieloetykietowość ten wykres jest mało czytelny.

![[visualisation(1)-cropped.svg]]

*Wynik funkcji CALL db.schema.visualization()*

5.4 Dokumentacja

Katalog `endpoint_schema/` zawiera dokumentację punktów końcowych API: dozwolone role, kształt żądań i odpowiedzi oraz wykonywane zapytania bazodanowe. Każdy plik odpowiada roli, która może wykonywać dane zapytanie.

Ponadto API generuje interaktywną dokumentację w standardzie OpenAPI [CYTOWANIE: https://fastapi.tiangolo.com/reference/openapi/docs/], na podstawie tych samych modeli, które służą do walidacji. Jest ona dostępna pod adresem `/api/docs`.

5.4.1 Konwencje

Każdy punkt końcowy jest opisany według tego samego schematu: kto może go wywołać (**Allowed**), kształt żądania (**Request**), kształt odpowiedzi (**Response**) oraz zapytania Cypher, które wykonuje (**Query**). `X?` oznacza pole opcjonalne lub mogące przyjąć wartość `null`, a `List[X]` tablicę JSON. Każdy punkt końcowy poza `POST /login` wymaga nagłówka `Authorization: Bearer <token>`. Ścieżki podawane są względem prefiksu `/api`, np. `GET /subjects` jest dostępny pod adresem `/api/subjects`.

Poniżej opisano wybrane, najważniejsze punkty końcowe - po co najmniej jednym dla każdej roli.

5.4.2 Logowanie - POST /login

Jedyny punkt końcowy dostępny bez tokenu. Przyjmuje adres e-mail i hasło, a w odpowiedzi zwraca token oraz listę ról użytkownika.

```json
// Request
{
	"email": String,
	"password": String
}

// Response
{
	"email": String,
	"idx": String?,
	"roles": List["Admin" | "Teacher" | "Student"],
	"token": String
}
```

Błędny e-mail lub hasło skutkuje kodem 401, a konto zablokowane lub bez żadnej roli kodem 403.

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

Zapytanie dobrze pokazuje zaletę wieloetykietowości. Role są po prostu etykietami tego samego węzła. Wyrażenia `u:Admin`, `u:Teacher` itd. zwracają wartość logiczną, więc jednym odczytem węzła uzyskiwany jest komplet informacji o uprawnieniach. Podobnie działa blokada konta - dezaktywowany użytkownik dostaje etykietę `Inactive`.

5.4.3 Katalog przedmiotów - GET /subjects

Zwraca listę przedmiotów w postaci siatki: wiersze to przedmioty, a kolumny to cykle akademickie. Każda komórka mówi, czy przedmiot jest w danym cyklu prowadzony, ile ma grup i czy trwają na niego zapisy. Opcjonalne parametry `name` i `code` zawężają wyniki do przedmiotów, których nazwa lub kod zawiera podany tekst.

```http
GET /subjects?name=sieci&code=SI00
```

```json
// Response
{
	"cycle_columns": List[String],
	"subjects": List[SubjectCatalogueItem]

	SubjectCatalogueItem = {
		"code": String,
		"name": String,
		"ects": Integer?,
		"faculty": String,
		"cycles": List[SubjectCycleCell]
	}

	SubjectCycleCell = {
		"offered": Boolean,
		"group_count": Integer,
		"registration_open": Boolean
	}
}
```

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
           min(datetime({date: rt.date, time: rt.start_time})) AS opens,
           max(datetime({date: rt.date, time: rt.end_time})) AS closes
      WHERE opens <= datetime() < closes
    }
  }] AS cycles
ORDER BY su.name
```

Warunek `$name IS NULL OR ...` sprawia, że to samo zapytanie obsługuje zarówno wyszukiwanie z filtrem, jak i bez niego. Podzapytanie `COLLECT` przechodzi ścieżką od przedmiotu, przez semestr programu i program studiów, aż do wydziału.

Komórki siatki powstają w wyrażeniu listowym `[cycle_id IN $cycle_ids | { ... }]`, w kolejności zgodnej z kolumnami. Każde pole komórki to osobne pytanie o istnienie ścieżki w grafie: `EXISTS { ... }` sprawdza, czy taka ścieżka istnieje, a `COUNT { ... }` liczy jej wystąpienia. Przedmiot jest oferowany w cyklu, jeśli należy do semestru programu studiów realizowanego w tym cyklu. Zapisy są otwarte, jeśli bieżący moment mieści się w okresie zapisów (Registration) obejmujących którąkolwiek grupę przedmiotu z tego cyklu. Zapisy nie mają własnych dat, więc ich okres trwa od początku pierwszej do końca ostatniej tury. Wzorzec zawierający przecinek opisuje dwie ścieżki, które muszą być spełnione jednocześnie i mają wspólny węzeł `si`.

5.4.4 Lista grup w zapisach - GET /me/registrations/{registration_id}/groups
Punkt końcowy studenta, wywoływany po wybraniu przedmiotu w trakcie zapisów. Zwraca wszystkie grupy tego przedmiotu otwarte przez dane zapisy, wraz z liczbą zajętych miejsc i informacją, czy student już jest w danej grupie zapisany. Zapisy są wskazywane w ścieżce, a przedmiot w parametrze zapytania, ponieważ jedynie zawęża listę grup otwartych przez zapisy:

```http
GET /me/registrations/8324f6b2-bd39-589e-88a0-a61423325d54/groups?subject_code=W04CBE-SI0404G
```

```json
// Response
{
	"groups": List[OpenGroup]

	OpenGroup = {
		"id": String,
		"g_type": String,
		"number": Integer,
		"weekday": Integer,
		"start": Time,
		"end": Time,
		"capacity": Integer,
		"filled": Integer,
		"room": String?,
		"teacher": String?,
		"registered": Boolean
	}
}
```

Najpierw wykonywane jest sprawdzenie dostępu - student musi mieć przydzieloną turę w tych zapisach, w przeciwnym razie API zwraca kod 403:

```cypher
MATCH (st:Student {idx: $student_idx})-[:ASSIGNED]->(:RegistrationTurn)<-[:HAS_TURN]-(reg:Registration {id: $registration_id})
RETURN reg.id AS id
```

Następnie pobierane są same grupy:

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

Sala i prowadzący są dołączane przez `OPTIONAL MATCH`, ponieważ nowo utworzona grupa może ich jeszcze nie mieć - wtedy odpowiednie pola mają wartość `null`, a grupa nadal jest zwracana. Liczba zajętych miejsc nie jest przechowywana jako licznik, tylko liczona na bieżąco jako liczba krawędzi `REGISTERED_IN` wchodzących do grupy. Dzięki temu nie istnieje ryzyko rozjechania się licznika z faktycznym stanem.

5.4.5 Zapis do grupy - PUT /me/registered-groups/{group_id}
Najważniejszy punkt końcowy całego systemu, a zarazem najbardziej obciążony - w momencie otwarcia tury zapisów wywołuje go jednocześnie wielu studentów. Zasobem jest tu miejsce studenta w grupie, wskazane identyfikatorem grupy w ścieżce.

```http
PUT /me/registered-groups/96992b82-07dc-58c0-b3bf-4d64e58ad87f
```

Zapis jest odrzucany z kodem 403, gdy student nie ma dostępu do grupy lub jego tura nie trwa, oraz z kodem 409, gdy jest już zapisany do innej grupy tego samego typu z tego przedmiotu albo grupa jest pełna. Ponowny zapis do grupy, w której student już jest, kończy się sukcesem bez żadnych zmian. Wypis z grupy to analogiczne żądanie `DELETE` pod tym samym adresem.

Wszystkie te warunki są sprawdzane w tym samym zapytaniu, w którym tworzona jest krawędź `REGISTERED_IN`. Nie jest to przypadek - rozbicie sprawdzenia i zapisu na dwa osobne zapytania prowadziłoby do sytuacji wyścigu. Sposób jej rozwiązania został szczegółowo opisany w podrozdziale [TODO: numer podrozdziału o race condition].

5.4.6 Wystawienie oceny - PUT /groups/{group_id}/students/{student_idx}/grade
Punkt końcowy prowadzącego. Pozwala wystawić ocenę studentowi zapisanemu do grupy. Grupa i student są wskazani w ścieżce, a treść żądania zawiera wyłącznie ocenę.

```http
PUT /groups/96992b82-07dc-58c0-b3bf-4d64e58ad87f/students/279413/grade
```

```json
// Request
{
	"grade": Float
}

// Response
{
	"group_id": String,
	"student_idx": String,
	"grade": Float
}
```

Ocena musi być jedną z wartości `2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0`. Jest to sprawdzane już przez model Pydantic, więc każda inna wartość jest odrzucana z kodem 422, zanim żądanie w ogóle dotrze do bazy danych. Nauczyciel może wystawiać oceny tylko w grupach, które prowadzi - administrator w dowolnych:

```cypher
// 1. Sprawdzenie dostępu (tylko dla nauczyciela)
MATCH (t:Teacher {idx: $teacher_idx})-[:TEACHES]->(g:Group {id: $group_id})
RETURN g.id AS id

// 2. Wystawienie oceny
MATCH (st:Student {idx: $student_idx})-[r:REGISTERED_IN]->(g:Group {id: $group_id})
SET r.grade = $grade
RETURN g.id AS group_id, st.idx AS student_idx, r.grade AS grade
```

Ocena jest właściwością krawędzi `REGISTERED_IN` (4.3.3). Jeśli student nie jest zapisany do grupy, wzorzec nie zostanie dopasowany, oceny nie da się wystawić, a API odpowiada kodem 404.

5.4.7 Dodanie studenta - POST /admin/students
Punkt końcowy administratora, tworzący nowego studenta i od razu przypisujący go do semestru programu studiów.

```json
// Request
{
	"idx": String,
	"name": String,
	"surname": String,
	"phone": String,
	"photo": String?,
	"joined": DateTime,
	"programme": String,
	"term_id": String?
}

// Response
{
	"idx": String,
	"name": String,
	"surname": String,
	"phone": String,
	"photo": String?,
	"joined": DateTime
}
```

Pole `term_id` jest opcjonalne. Bez niego student trafia na pierwszy semestr najnowszego programu (Curriculum) danego kierunku. Podanie go pozwala zapisać studenta na dowolny semestr, co przydaje się przy przeniesieniach z innej uczelni. Najpierw ustalany jest właściwy semestr:

```cypher
MATCH (p:Programme {id: $programme})
RETURN
  COUNT { (p)-[:HAS_CURRICULUM]->(:Curriculum) } AS curricula,
  COLLECT {
    MATCH (p)-[:HAS_CURRICULUM]->(c:Curriculum)-[:HAS_TERM]->(ct:CurriculumTerm)
    WHERE ($term_id IS NULL AND ct.sem = 1) OR ct.id = $term_id
    RETURN ct.id ORDER BY c.intake_year DESC
  } AS terms
```

Na podstawie wyniku API albo wybiera pierwszy element listy `terms`, albo odrzuca żądanie: z kodem 404, gdy kierunek nie istnieje, z kodem 409, gdy kierunek nie ma jeszcze programu lub pierwszego semestru, oraz z kodem 422, gdy podany semestr nie należy do kierunku. Dopiero potem tworzony jest węzeł:

```cypher
MATCH (ct:CurriculumTerm {id: $term_id})
CREATE (st:Student:Person {
  idx: $idx, name: $name, surname: $surname, phone: $phone,
  joined: datetime($joined), photo: $photo
})
CREATE (st)-[:ENROLLED]->(ct)
RETURN st.idx AS idx, st.name AS name, st.surname AS surname,
       st.phone AS phone, st.photo AS photo, st.joined AS joined
```

Udane utworzenie zwraca kod 201 z nagłówkiem `Location: /api/students/{idx}`, czyli adresem, pod którym można od razu odczytać nowego studenta. Zajęty numer indeksu zostaje wykryty przez ograniczenie `idx IS KEY` w bazie i zwrócony jako 409.

Student jest tworzony bez etykiety `User`, czyli bez możliwości logowania - konto nadaje się osobnym punktem końcowym `POST /admin/users`.

5.5 API

API odbiera żądanie na wybranym punkcie końcowym, weryfikuje token i uprawnienia użytkownika, otwiera sesję bazy danych, wykonuje zapytanie w języku Cypher, a jego wynik przekształca do oczekiwanego kształtu i zwraca klientowi. Poprawność danych wejściowych i format odpowiedzi wyznaczają modele Pydantic. Zapytania są wykonywane bezpośrednio przez oficjalny, asynchroniczny sterownik Neo4j dla języka Python.[CYTOWANIE: https://neo4j.com/docs/api/python-driver/current/].

5.5.1 Struktura aplikacji

```
.
├── graph_backend
│   ├── auth
│   │   ├── deps.py
│   │   └── __init__.py
│   ├── cycles.py
│   ├── database.py
│   ├── errors.py
│   ├── grades.py
│   ├── __init__.py
│   ├── query.py
│   ├── routers
│   │   ├── admin.py
│   │   ├── catalogue.py
│   │   ├── __init__.py
│   │   ├── public.py
│   │   ├── student.py
│   │   └── teacher.py
│   └── teaching.py
├── __init__.py
└── schemas
    ├── academic_cycle.py
    ├── admin_links.py
    ├── admin_lists.py
    ├── auth.py
    ├── curriculum.py
    ├── curriculum_term.py
    ├── dashboard.py
    ├── faculty.py
    ├── generic.py
    ├── grades.py
    ├── group.py
    ├── __init__.py
    ├── opinion.py
    ├── registration.py
    ├── room.py
    ├── student.py
    ├── subject.py
    └── teacher.py

5 directories, 34 files
```

*Struktura katalogu `app/` (bez katalogów `__pycache__`)*

W pliku `app/__init__.py` jest tworzony obiekt `app`, instancja klasy `FastAPI`. To do niego podłączane są wszystkie elementy backendu: punkty końcowe, obsługa błędów i obsługa cyklu życia aplikacji. Ten sam obiekt wykorzystuje polecenie `uvicorn app:app` z 5.1.5.

5.5.2 Inicjalizacja i błędy

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await verify_connectivity()
    yield
    await close_driver()


API_PREFIX = "/api"

app = FastAPI(
    title="mini-usos",
    lifespan=lifespan,
    docs_url=f"{API_PREFIX}/docs",
    redoc_url=f"{API_PREFIX}/redoc",
    openapi_url=f"{API_PREFIX}/openapi.json",
)
register_exception_handlers(app)
app.include_router(public_router, prefix=API_PREFIX)
# ... pozostałe routery
```

*Fragment `app/__init__.py`*

Do konstruktora `FastAPI` przekazywane są tytuł, funkcja `lifespan` oraz ścieżki do automatycznie generowanej dokumentacji.

Funkcja `lifespan` obejmuje cały czas działania aplikacji [CYTOWANIE: https://fastapi.tiangolo.com/advanced/events/#lifespan]. FastAPI wymaga, by była ona asynchronicznym menedżerem kontekstu, a staje się nim poprzez dekorator `@asynccontextmanager`. Kod przed `yield` wykonuje się raz, przy uruchomieniu, a kod po `yield` też raz, przy zamknięciu. Pomiędzy nimi funkcja jest wstrzymana na słowie `yield`, aplikacja przez ten czas obsługuje żądania. Obie wywoływane funkcje są asynchroniczne, dlatego poprzedza je `await`. Wywołanie funkcji asynchronicznej zwraca jedynie obiekt korutyny (ang. *coroutine*), jej kod wykonuje się dopiero po użyciu `await`. [CYTOWANIE: https://docs.python.org/3/library/asyncio-task.html]

![[Pasted image 20261117184011.png]]

*Dokumentacja metody `verify_connectivity` [CYTOWANIE: https://neo4j.com/docs/api/python-driver/current/async_api.html#neo4j.AsyncDriver.verify_connectivity]*

Przy starcie `verify_connectivity()` sprawdza, czy sterownik może połączyć się z bazą i zalogować. Jeśli baza jest niedostępna, aplikacja nie uruchamia się wcale. Przy zamknięciu `close_driver()` zamyka sterownik wraz z jego pulą połączeń.

Na poziomie całej aplikacji są rejestrowane procedury obsługi wyjątków (ang. *exception handlers*). Określają one, jaki kod statusu i jaki komunikat w formacie JSON zwrócić, gdy podczas obsługi żądania zostanie zgłoszony wyjątek danego typu [CYTOWANIE: https://fastapi.tiangolo.com/tutorial/handling-errors/#install-custom-exception-handlers]. Zdefiniowano je w funkcji `register_exception_handlers()` w pliku `errors.py`.

```python
def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ConstraintError)
    async def constraint_error_handler(_request: Request, exc: ConstraintError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": db_err(exc)})

    @app.exception_handler(ClientError)
    async def client_error_handler(_request: Request, exc: ClientError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": db_err(exc)})
```

*Fragment funkcji `register_exception_handlers`*

Dzięki temu punkty końcowe nie muszą same przechwytywać błędów bazy danych. Naruszenie ograniczenia ze schematu (5.3.1), np. duplikat klucza, kończy się kodem 409, a odrzucenie zapytania przez bazę, np. z powodu niepoprawnej daty, kodem 400. `ConstraintError` dziedziczy po `ClientError`, a ten po `Neo4jError`. Pozostałe błędy – inne błędy bazy, niezgodność odpowiedzi z modelem Pydantic i nieobsłużone wyjątki – kończą się kodem 500. Ich szczegóły trafiają do logów serwera, a klient otrzymuje ogólny komunikat.

W tym samym pliku zdefiniowano funkcje pomocnicze tworzące `HTTPException` dla najczęstszych kodów: `unauthorized` (401), `forbidden` (403), `not_found` (404), `conflict` (409) i `invalid` (422). Punkty końcowe zgłaszają błędy wyłącznie przez nie, co pozwala ustandaryzować odpowiedzi.

```python
def not_found(what: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{what} not found")
```

Na końcu `app/__init__.py` podłączane są routery z katalogu `routers/` (5.5.1), pogrupowane według ról użytkowników. Każdy jest dołączany z argumentem `prefix=API_PREFIX`, więc wszystkie punkty końcowe zaczynają się od `/api`.

5.5.3 Połączenie z bazą danych

Baza danych Neo4j wykorzystywana przez aplikację komunikuje się z aplikacją przez asynchroniczny sterownik zdefiniowany w `graph_backend/database.py`. Pojedyncza instancja `AsyncGraphDatabase.driver` jest współdzielona w całej aplikacji. Zgodnie z testami wykonanymi na potrzeby biblioteki neomodel, asynchroniczny sterownik jest szybszy od zrównoleglonego i o wiele szybszy od szeregowego.  [CYTOWANIE: https://github.com/mariusconjeaud/neomodel-locust]

Konstruktor sterownika przyjmuje URI bazy danych oraz login i hasło użytkownika aplikacji. Wszystkie trzy wartości są odczytywane ze zmiennych środowiskowych ustawianych przez Docker Compose (5.1.5). URI ma schemat `bolt+s`, więc cały ruch między API a bazą jest szyfrowany TLS.

Moduł udostępnia też funkcje `verify_connectivity()` i `close_driver()`, wywoływane w `lifespan` (5.5.2), oraz zależność `get_session()`, przez którą punkty końcowe otrzymują sesję bazy danych.

```python
async def get_session():
    async with driver.session() as session:
        yield session
```

*Funkcja pozyskiwania sesji*

Sesja jest otwierana w bloku `async with`, czyli przez asynchroniczny menedżer kontekstu (ang. *context manager*). Przy wejściu do bloku wywoływana jest metoda `__aenter__()`, która otwiera sesję, a przy wyjściu – `__aexit__()`, która ją zamyka, również wtedy, gdy w bloku wystąpi wyjątek [CYTOWANIE: https://docs.python.org/3/reference/datamodel.html#async-context-managers]. Wewnątrz bloku funkcja zatrzymuje się na `yield` i przekazuje sesję. Resztą zarządza FastAPI: wstrzykuje sesję do punktu końcowego jako zależność, a po jego zakończeniu wznawia funkcję, która wychodzi z bloku `async with` i zamyka sesję [CYTOWANIE: https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/].

Sesja jest tworzona raz na żądanie. Zgodnie z dokumentacją sterownika, tworzenie sesji jest lekką operacją, ale sesje nie są bezpieczne przy współbieżnym użyciu [CYTOWANIE: https://neo4j.com/docs/api/python-driver/current/async_api.html#asyncsessions-asynctransactions]. Dlatego sesja nie jest współdzielona: każde żądanie dostaje własną, a współdzielony jest jedynie sterownik. To on utrzymuje pulę połączeń, z której sesje pobierają połączenie przy pierwszym zapytaniu i do której je oddają przy zamknięciu.

Transakcje są wykorzystywane na dwa sposoby. Pojedyncze wywołanie `session.run()` jest wykonywane jako transakcja automatyczna (ang. *auto-commit*): zapytanie wykonuje się w całości albo wcale. Większość punktów końcowych wykonuje jedno zapytanie, więc to wystarcza. Gdy kilka zapytań musi się udać razem, otwierana jest jawna transakcja i zatwierdzana przez `commit()`. Tak działa m.in. usuwanie roli użytkownika oraz otwarcie zapisów, w którym utworzenie rejestracji, jej tur i powiązań z grupami jest jedną operacją.

```python
tx = await session.begin_transaction()
try:
    row = None
    if await one(tx, _LOCK_PERSON, idx=idx) is not None:
        row = await one(tx, _REMOVE_ROLE[role], idx=idx)
    await tx.commit()
finally:
    await tx.close()
```

*Jawna transakcja przy usuwaniu roli*

Zapytania w transakcji są wykonywane tą samą funkcją `one()` co w sesji (5.5.5), ponieważ sesja i transakcja udostępniają metodę `run()` o tej samej sygnaturze. Jeśli przed `commit()` zostanie zgłoszony wyjątek, `close()` w bloku `finally` wycofuje transakcję i żadna ze zmian nie trafia do bazy. Neo4j zawsze działa na poziomie izolacji *read committed*, którego nie da się podnieść, dlatego spójność przy współbieżnych żądaniach zapewniają jawne blokady zapisu, takie jak `_LOCK_PERSON` powyżej (5.5.8) [CYTOWANIE: https://neo4j.com/docs/operations-manual/current/database-internals/concurrent-data-access/].

5.5.4 Modele danych (schema)

Kształt żądań i odpowiedzi został zdefiniowany w katalogu `schemas/` w postaci modeli Pydantic. Pydantic działa w obie strony: dane JSON z żądania zamienia na zwalidowany obiekt Pythona, a wynik zapytania – na odpowiedź JSON. Pliki są podzielone według dziedziny (przedmioty, grupy, opinie itd.), a nazwy modeli stosują konwencję `…Request` dla treści żądania i `…Response` dla odpowiedzi. Kształt odpowiedzi określono dla każdego punktu końcowego zwracającego dane, a kształt żądania – dla każdego, który przyjmuje treść.

Walidacja działa po obu stronach punktu końcowego. Żądanie niezgodne z modelem jest odrzucane z kodem 422, zanim funkcja punktu końcowego zostanie wywołana, więc błędne dane nie docierają do bazy danych (5.4.6). Odpowiedź niezgodna z modelem podanym w `response_model` kończy się kodem 500 (5.5.2), ponieważ jest to błąd serwera, a nie klienta.

Definiowanie modelu Pydantic polega na stworzeniu klasy dziedziczącej po `BaseModel` i określeniu, jakie pola i jakiego typu ma zawierać. Typ `Optional[X]`, równoważny `X | None`, oznacza, że pole może przyjąć wartość `null` [CYTOWANIE: https://docs.python.org/3/library/typing.html#typing.Optional].

Od Pydantic v2 `Optional` nie oznacza jednak, że pole można pominąć. O tym decyduje wyłącznie wartość domyślna: pole `Optional` bez niej jest wymagane, a żądanie, które go nie zawiera, zostaje odrzucone z kodem 422 [CYTOWANIE: https://docs.pydantic.dev/latest/migration/#required-optional-and-nullable-fields]. Dlatego wszystkie pola opcjonalne w projekcie mają jawnie ustawione `= None`.

```python
class SubjectUpsertRequest(BaseModel):
    name: str
    ects: Optional[int] = None
```

*Przykładowy model z opcjonalnym polem*

Ograniczenia wartości pola można określić funkcją `Field()`, działającą podobnie do funkcji `field()` dla klas danych (ang. *dataclasses*) [CYTOWANIE: https://pydantic.dev/docs/validation/latest/concepts/fields/]. Choć zapisuje się ją po prawej stronie `=`, sama nie ustawia wartości domyślnej – robią to dopiero argumenty `default` lub `default_factory`.

```python
class GroupCreateRequest(BaseModel):
    weekday: int = Field(ge=1, le=7)
    pnp: Literal["P", "NP", "ALL"]
    # ...
```

*Przykładowy model z ograniczeniem zakresu wartości pola*

`Field(ge=1, le=7)` dopuszcza jako dzień tygodnia wyłącznie liczby całkowite od 1 do 7, a `Literal` ogranicza pole `pnp` do trzech podanych wartości.

Bardziej złożoną walidację zapewniają własne walidatory [CYTOWANIE: https://pydantic.dev/docs/validation/latest/concepts/validators/]. Metoda oznaczona dekoratorami `@field_validator()` i `@classmethod` jest wywoływana dla pól podanych w argumentach dekoratora. Domyślnie metoda uruchamia się po standardowej walidacji typu, więc otrzymuje wartość już przekonwertowaną na Pythonowy typ danych. 

W projekcie własny walidator sprawdza, czy liczba jest oceną ze skali 2.0, 2.5, …, 5.0. Nie można było użyć `Literal[2.0, 2.5, …]`, ponieważ `Literal` z założenia nie przyjmuje liczb zmiennoprzecinkowych [CYTOWANIE: https://peps.python.org/pep-0586/#illegal-parameters-for-literal-at-type-check-time]. Sama funkcja `check_grade()` znajduje się w osobnym pliku `grades.py`, ponieważ korzystają z niej dwa modele: `OpinionCreateRequest` (ocena prowadzącego w opinii) i `SetGroupGradeRequest` (ocena wystawiana studentowi).

```python
# opinion.py

class OpinionCreateRequest(BaseModel):
    grade: float
    content: Optional[str] = Field(default=None, max_length=1000)
    group_id: str
    teacher_idx: str
    student_idx: Optional[str] = None

    @field_validator("grade")
    @classmethod
    def grade_on_scale(cls, value: float) -> float:
        return check_grade(value)

# grades.py

GRADE_SCALE = (2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0)


def check_grade(value: float) -> float:
    if value not in GRADE_SCALE:
        raise ValueError(f"grade must be one of {', '.join(map(str, GRADE_SCALE))}")
    return value
```

*Walidacja oceny w modelu Pydantic*

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "grade"],
      "msg": "Value error, grade must be one of 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0",
      "input": 4.2,
      "ctx": {"error": {}}
    }
  ]
}
```

*Odpowiedź 422 na `PUT /groups/{group_id}/students/{student_idx}/grade` z oceną 4.2*

Pole `loc` wskazuje miejsce błędu – pole `grade` w treści żądania – a `msg` zawiera komunikat zgłoszony przez `check_grade()`. Żądanie zostało odrzucone przed sprawdzeniem, czy grupa i student w ogóle istnieją.

5.5.5 Funkcje współdzielone

Zapytania do bazy danych są wykonywane przez dwie funkcje z pliku `query.py`: `run()` i `one()`. Są to cienkie nakładki (ang. *wrappers*) na metodę `run()` sesji i transakcji sterownika, które poza wykonaniem zapytania zamieniają jego wynik na listę słowników z typami Pythona. Funkcja `one()` korzysta z `run()`, ale zwraca jedynie pierwszy wiersz albo `None`, gdy wynik jest pusty. Jest przeznaczona dla zapytań, które z założenia zwracają najwyżej jeden wiersz. Takich jest w projekcie dużo – w szczególności zapytania kontroli dostępu. Wynik `None` oznacza, że szukany element nie istnieje, co punkty końcowe zamieniają na odpowiedź 404.

```python
Runner = AsyncSession | AsyncTransaction

async def run(runner: Runner, query: str, **params: Any) -> list[dict[str, Any]]:
    result = await runner.run(query, params)
    return [native(record.data()) async for record in result]


async def one(runner: Runner, query: str, **params: Any) -> dict[str, Any] | None:
    rows = await run(runner, query, **params)
    return rows[0] if rows else None
```

*Funkcje do wykonywania zapytań*

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

Zapisy `$id`, `$name` i `$full_name` to parametry zapytania [CYTOWANIE: https://neo4j.com/docs/cypher-manual/current/syntax/parameters/]. Ich wartości nie są wstawiane do tekstu zapytania – sterownik wysyła do bazy tekst i parametry osobno, a podstawia je dopiero baza. Dzięki temu dane od użytkownika nigdy nie stają się częścią kodu zapytania, co chroni przed wstrzykiwaniem kodu Cypher (ang. *Cypher injection*). Tekst zapytania pozostaje przy tym stały, więc baza może ponownie wykorzystać raz przygotowany plan jego wykonania. Dane od użytkownika trafiają do zapytań w projekcie wyłącznie w ten sposób.

Python 3.14 wprowadził szablony tekstowe (ang. *template strings*, t-stringi), które pozwalają zapisać zapytanie podobnie do f-stringa, a mimo to przekazać wartości osobno. Biblioteka psycopg, służąca do łączenia z bazą PostgreSQL, już je obsługuje [CYTOWANIE: https://www.psycopg.org/psycopg3/docs/basic/tstrings.html], natomiast sterownik Neo4j w wykorzystanej wersji 6.2.0 – nie. Jest to jednak różnica w wygodzie zapisu, a nie w bezpieczeństwie.

Ostatnią funkcją z `query.py` jest `new_id()`, która generuje losowy identyfikator funkcją `uuid4()` i od razu zamienia go na napis. Neo4j nie ma typu UUID, dlatego identyfikatory są w schemacie zadeklarowane jako `STRING`. Powody wyboru UUID zamiast identyfikatorów liczbowych omówiono w 5.3.1.

Pozostałe funkcje współdzielone wynikają z logiki dziedziny:
- `teacher_groups()` (`teaching.py`) – zapytanie zwracające grupy prowadzącego, wykorzystywane przez trzy punkty końcowe: `/me/groups`, `/teachers/{idx}` oraz `/teachers/{idx}/groups`. Dzięki temu lista grup prowadzącego ma wszędzie ten sam kształt i kolejność.
- `cycle_sort_key()` (`cycles.py`) – klucz sortowania cykli akademickich: najpierw rok, a w jego obrębie semestr zimowy przed letnim. Zwykłe sortowanie alfabetyczne dałoby odwrotną kolejność, ponieważ „L” poprzedza „Z”.
- `average_grade()` (`grades.py`) – średnia ocen studenta ważona punktami ECTS, liczona z ostatniego w pełni ocenionego podejścia do każdego przedmiotu. Do wyboru ostatniego podejścia wykorzystuje `cycle_sort_key()`. Średnia jest liczona w Pythonie, a nie w zapytaniu Cypher, ponieważ wybór podejścia i uśrednianie ocen z kilku grup tego samego typu byłyby w Cypher znacznie mniej czytelne.

5.5.6 Uwierzytelnianie

Uwierzytelnianie zrealizowano w pliku `graph_backend/auth/deps.py`. Zawiera on funkcje obsługi haseł i tokenów, z których korzystają punkt końcowy `POST /login` (5.4.2) oraz tworzenie kont w module administratora, a także zależność `get_caller()`, przez którą wszystkie pozostałe punkty końcowe ustalają, kto wysłał żądanie. Założenia tego mechanizmu, w tym powody wyboru tokenów JWT, opisano w 4.4.1.

Hasła są obsługiwane przez bibliotekę bcrypt w wersji 5.0.0 [CYTOWANIE: https://pypi.org/project/bcrypt/].

```python
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False
```

*Funkcje obsługi haseł*

`hashpw()` przyjmuje jako argumenty surowe hasło i sól. Funkcja `gensalt()` przy każdym wywołaniu losuje nową sól i ustala współczynnik kosztu (ang. *salt rounds*), domyślnie 12, co oznacza 2^12 rund rozwinięcia klucza. Wynikiem `hashpw()` jest napis w postaci:

```
$2b$12$.lG2u6PuGdo7F5TdxxeEDuTQiGb/6nF5zkc04Qq9sf0SfD0egQsmq
```

*Skrót hasła konta administratora z danych początkowych*

Kolejne fragmenty oddzielone znakiem `$` to wariant algorytmu (`2b`), koszt (`12`), a następnie 22 znaki soli i 31 znaków właściwego skrótu [CYTOWANIE: https://www.usenix.org/legacy/events/usenix99/provos/provos.pdf]. Skrót zawiera więc wszystko, co jest potrzebne do jego weryfikacji poprzez odtworzenie.

Koszt obliczeniowy jest wyraźnie odczuwalny: na maszynie testowej żądanie `POST /login` z istniejącym adresem trwało ok. 190 ms, z czego niemal cały czas zajmuje bcrypt. Dla pojedynczego logowania jest to niezauważalne, ale atakującemu, który zdobyłby skróty z bazy, ogranicza liczbę sprawdzanych haseł do kilku na sekundę na jeden rdzeń procesora.

Algorytm bcrypt uwzględnia wyłącznie pierwsze 72 bajty hasła. Wcześniejsze wersje biblioteki obcinały dłuższe hasła bez ostrzeżenia, zgodnie z oryginalną implementacją zaproponowaną prze OpenBSD. Od wersji 5.0.0 zgłaszany jest wyjątek `ValueError` [CYTOWANIE: https://github.com/pyca/bcrypt/blob/main/CHANGELOG.rst].

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

**Wydanie tokenu**

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

Test `tests/test_login_timing.py` wykazał, że odpowiedź dla nieistniejącego konta przychodziła po ok. 4 ms, a dla istniejącego konta z błędnym hasłem po ok. 184 ms. Po samym czasie odpowiedzi dało się więc jednoznacznie sprawdzić, czy konto o danym adresie istnieje (atak czasowy, ang. *timing attack*) [CYTOWANIE: OWASP Authentication Cheat Sheet, https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html#authentication-responses].

Obecnie, gdy użytkownik nie istnieje, hasło jest sprawdzane względem `DUMMY_PASSWORD_HASH`, czyli skrótu losowego hasła, wyliczanego raz przy starcie aplikacji z tym samym kosztem co prawdziwe skróty. bcrypt wykonuje się zawsze, a wynik i tak jest odrzucany warunkiem `row is None`.

```python
DUMMY_PASSWORD_HASH = hash_password(os.urandom(16).hex())
```

*Skrót zastępczy (`auth/deps.py`)*

| Przypadek | Kod | Mediana przed poprawką [ms] | Mediana po poprawce [ms] |
| --- | :---: | ---: | ---: |
| istniejące konto, poprawne hasło | 200 | 185,1 | 183,6 |
| istniejące konto, błędne hasło | 401 | 183,7 | 183,3 |
| nieistniejące konto | 401 | 4,0 | 183,2 |

*Czas odpowiedzi `POST /api/login`, 30 prób na przypadek*

Stan konta i role są sprawdzane dopiero po poprawnej weryfikacji hasła, więc odpowiedź 403 („konto nieaktywne” albo „brak roli”) otrzymuje tylko ktoś, kto zna hasło. Funkcja `roles_from_flags()` zamienia trzy wartości logiczne z zapytania na krotkę nazw ról: `Admin`, `Teacher`, `Student`.

```python
def create_token(caller: Caller) -> str:
    payload = {
        "sub": caller.email,
        "idx": caller.idx,
        "roles": list(caller.roles),
        "exp": datetime.now(timezone.utc) + timedelta(hours=12),
    }
    return jwt.encode(payload, _secret, algorithm=_algorithm)
```

*Tworzenie tokenu*

Token jest tworzony biblioteką PyJWT [CYTOWANIE: https://pyjwt.readthedocs.io/]. Zawiera cztery roszczenia (ang. *claims*). Dwa z nich są zdefiniowane w standardzie: `sub` (ang. *subject*) wskazuje, kogo dotyczy token, w tym wypadku jest to adres e-mail, a `exp` (ang. *expiration time*) określa moment wygaśnięcia [CYTOWANIE: RFC 7519, sekcja 4.1]. PyJWT sam zamienia obiekt `datetime` na wymaganą przez standard liczbę sekund od 1 stycznia 1970 r. Pozostałe dwa, `idx` i `roles`, to roszczenia prywatne, specyficzne dla tej aplikacji. Token jest ważny przez 12 godzin, po czym użytkownik musi zalogować się ponownie.

Token jest podpisywany algorytmem HS256, czyli kodem HMAC z funkcją skrótu SHA-256 [CYTOWANIE: RFC 7518, sekcja 3.2]. Jest to algorytm symetryczny - ten sam klucz służy do podpisania tokenu i do sprawdzenia podpisu. Wystarcza to, ponieważ token wydaje i weryfikuje wyłącznie to samo API. Klucz pochodzi ze zmiennej środowiskowej `JWT_SECRET` (5.1.5) i jest odczytywany przez `os.environ["JWT_SECRET"]` już przy imporcie modułu

```json
{
  "email": "279413@student.pwr.edu.pl",
  "idx": "279413",
  "roles": ["Student"],
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyNzk0MTNAc3R1ZGVudC5wd3IuZWR1LnBsIiwiaWR4IjoiMjc5NDEzIiwicm9sZXMiOlsiU3R1ZGVudCJdLCJleHAiOjE3OTUwNjI3NTR9.Mp85du5sH9UgkPx4Bmjugjcm9Py7KKuYHiePbQconbQ"
}
```

*Odpowiedź 200 na `POST /api/login` dla konta studenta*

Token składa się z trzech części oddzielonych kropkami: nagłówka, treści (ang. *payload*) i podpisu. Nagłówek i treść są zakodowane w base64url, de facto jawne.

![[Pasted image 20261118175909.png]]

*Token JWT zdekodowany przy pomocy https://www.jwt.io/*

Podpis gwarantuje jedynie, że treść nie została zmieniona - nie ukrywa jej. Próba zmiany treści, na przykład dopisania roli `Admin`, unieważnia podpis, a nowego podpisu nie da się wyliczyć bez znajomości klucza.

**Weryfikacja tokenu**

Każdy punkt końcowy poza `POST /login` wymaga tokenu. Jest on sprawdzany przez zależność `get_caller()`.

```python
_bearer = HTTPBearer()


async def get_caller(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
) -> Caller:
    try:
        payload = jwt.decode(
            creds.credentials, _secret, algorithms=[_algorithm], options={"require": ["sub", "exp"]}
        )
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

`HTTPBearer` to klasa FastAPI, która odczytuje nagłówek `Authorization` i oddziela schemat `Bearer` od samego tokenu [CYTOWANIE: https://fastapi.tiangolo.com/reference/security/#fastapi.security.HTTPBearer]. Jeśli nagłówka brakuje lub ma on inny schemat niż `Bearer`, `HTTPBearer` sam przerywa obsługę żądania i zwraca błąd 401 `Not authenticated`, a `get_caller()` ani funkcja punktu końcowego nie zostają wywołane. Dodatkowo `HTTPBearer` rejestruje schemat zabezpieczeń w dokumentacji OpenAPI, dzięki czemu w `/api/docs` pojawia się przycisk *Authorize*, którym można wkleić token i wywoływać chronione punkty końcowe bezpośrednio z przeglądarki.

`jwt.decode()` sprawdza podpis tokenu i jego datę ważności. Wygaśnięty lub zmodyfikowany token zwróci błąd. Domyślnie PyJWT sprawdza datę ważności tylko wtedy, gdy pole `exp` znajduje się w tokenie – token bez niego byłby ważny bezterminowo. Dlatego opcja `require` wymusza obecność pól `sub` i `exp`, a token bez któregoś z nich jest odrzucany wyjątkiem `MissingRequiredClaimError` [CYTOWANIE: https://pyjwt.readthedocs.io/en/stable/api.html#jwt.decode]. Serwer decyduje o dozwolonych algorytmach podpisu, a klient w tokenie jedynie informuje który z tych algorymtów wykorzystuje. Chroni to przed znanymi atakami, w których atakujący zmienia algorytm w nagłówku, np. na `none`, czyli token bez podpisu [CYTOWANIE: RFC 8725, sekcja 2.1].

Poprawnie podpisany token jest dodatkowo sprawdzany: `roles` musi być niepustą listą znanych ról. Każdy z tych przypadków kończy się tą samą odpowiedzią 401 `Invalid token`, więc klient nie dowiaduje się, dlaczego token został odrzucony.

| Sytuacja                                                    | Kod | Treść odpowiedzi                          |
| ----------------------------------------------------------- | :-: | ----------------------------------------- |
| brak nagłówka `Authorization` lub schemat inny niż `Bearer` | 401 | `{"detail": "Not authenticated"}`         |
| zmieniony, wygasły lub uszkodzony token                     | 401 | `{"detail": "Invalid token"}`             |
| błędny e-mail lub hasło przy logowaniu                      | 401 | `{"detail": "Invalid email or password"}` |
| konto z etykietą Inactive                                   | 403 | `{"detail": "Account inactive"}`          |
| konto bez żadnej roli                                       | 403 | `{"detail": "Account has no role"}`       |

*Odpowiedzi przy nieudanym uwierzytelnieniu*

Wynikiem `get_caller()` jest obiekt klasy danych `Caller` z adresem e-mail, identyfikatorem osoby i krotką ról. Funkcja nie wykonuje żadnego zapytania do bazy - całą potrzebną informację zawiera token. Na tym obiekcie opiera się autoryzacja opisana w 5.5.7.

5.5.7 Autoryzacja
Autoryzacja przypisuje funkcje aplikacji do ról, które może otrzymać użytkownik. Opiera się na pokazanym wcześniej mechanizmie `Depends()`, dzięki któremu FastAPI wywołuje funkcję sprawdzającą uprawnienia, zanim uruchomi funkcję punktu końcowego.

Do kontroli dostępu opartej na rolach (RBAC) wykorzystywana jest fabryka zależności `require(*roles)`, której wynik przekazuje się do `Depends()` w argumentach funkcji punktu końcowego.

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

Kod `require` działa w dwóch różnych momentach. Sama funkcja `require` jest wywoływana raz, przy imporcie modułu routera. Niczego wtedy nie sprawdza, tylko tworzy i zwraca nową funkcję `checker`, która zapamiętuje przekazaną krotkę ról jako domknięcie (ang. *closure*). Dopiero `checker` jest wywoływana przez FastAPI przy każdym żądaniu, po rozwiązaniu jej własnej zależności `get_caller`. Dlatego `require` jest zwykłą funkcją, a `checker` – asynchroniczną: gdyby `require` była zadeklarowana jako `async def`, jej wywołanie zwróciłoby obiekt korutyny (5.5.2) zamiast funkcji, której oczekuje `Depends()`.

Zależności dla poszczególnych zestawów ról są tworzone raz, na początku modułów routerów, i współdzielone przez ich punkty końcowe.

| Zmienna | Role | Moduł | Liczba punktów końcowych |
| --- | --- | --- | ---: |
| `_logged_in` | Student, Teacher, Admin | `catalogue.py` | 10 |
| `_student` | Student | `student.py` | 9 |
| `_opinion_roles` | Student, Admin | `student.py` | 1 |
| `_teacher` | Teacher | `teacher.py` | 1 |
| `_staff` | Teacher, Admin | `teacher.py` | 3 |
| `_admin` | Admin | `admin.py` | 34 |

*Zależności sprawdzające role*

```http
GET /admin/people/next-idx
Authorization: Bearer <token studenta>
```

```json
{
  "detail": "Forbidden"
}
```

*Odpowiedź 403 na żądanie studenta do punktu końcowego administratora*

Jak wspominano wcześniej, RBAC służy jedynie do wstępnej kontroli dostępu. Jeśli są planowane szczegółowe dostępy, wykorzystywany jest ReBAC. O ile RBAC był wykonywany w zależnościach funkcji, ReBAC jest egzekwowany już w jej definicji. Z racji tego, że baza danych służy zarówno do reprezentacji domeny, jak i do kontroli dostępu, można wykorzystać krawędzie i węzły zdefiniowane bezpośrednio w bazie danych, by sprawdzić, jakie kwerendy są dozwolone, a jakie nie.

W większości przypadków ReBAC polega na sprawdzeniu, czy ścieżka między wyznaczonymi węzłami istnieje. Jeśli istnieje, jest wykonywane docelowe zapytanie, a jeśli nie, to zwracany jest błąd 403 Forbidden. W praktyce ReBAC to po prostu wykonanie dodatkowej kwerendy walidacyjnej przed wykonaniem kwerendy docelowej i podjęcie decyzji o dostępie na podstawie wyniku tej pierwszej.

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

Funkcja `_require_registration()` jest najprostszą postacią ReBAC. Sprawdza, czy w grafie istnieje ścieżka od studenta, przez przypisaną mu turę (`ASSIGNED`), do rejestracji, do której ta tura należy (`HAS_TURN`). Wzorzec w `MATCH` jest jednocześnie regułą dostępu: student ma dostęp do rejestracji wtedy i tylko wtedy, gdy przypisano go do którejś z jej tur. Funkcja niczego nie zwraca – albo kończy się bez błędu, albo zgłasza 403. Nie wie też, kto wysłał żądanie: oba węzły dostaje jako argumenty, więc ta sama reguła mogłaby posłużyć do sprawdzenia dostępu dowolnego studenta. Jedna funkcja obsługuje dwa punkty końcowe, `GET /me/registrations/{registration_id}/subjects` i `GET /me/registrations/{registration_id}/groups`.

Kolejnym elementem granularnej kontroli dostępu jest ustalenie, czyich danych dotyczy żądanie. Identyfikator osoby trafia do obiektu `Caller` z roszczenia `idx` tokenu (5.5.6), a do tokenu – z właściwości `idx` węzła użytkownika, odczytanej przy logowaniu (5.4.2). Jest to ten sam identyfikator, którym osoba jest oznaczona w grafie, np. numer indeksu `279413` dla studenta albo `T001` dla prowadzącego. Ponieważ token jest podpisany, klient nie może go zmienić bez unieważnienia podpisu, więc `caller.idx` jest wiarygodny w takim samym stopniu jak role.

Punkty końcowe operujące na danych zalogowanego użytkownika mają w ścieżce prefiks `/me/` – jest ich dziesięć, np. plan studiów, zapisy do grup czy prowadzone grupy. Nie przyjmują one identyfikatora osoby ani w ścieżce, ani w treści żądania – biorą go wyłącznie z tokenu.

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

Zapytanie zaczyna się od węzła studenta wskazanego przez `caller.idx` i przechodzi wyłącznie po jego krawędziach, więc z założenia nie może zwrócić danych innego studenta. Taki punkt końcowy nie potrzebuje osobnego sprawdzenia uprawnień ani odpowiedzi 403 – jeśli student nie jest zapisany na żaden kierunek, otrzymuje po prostu pustą listę.

Gdyby identyfikator był przekazywany przez klienta, np. jako `GET /students/{student_idx}/enrolments`, student mógłby podmienić go na numer indeksu kolegi i odczytać jego dane.

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

W tej funkcji kwerenda sprawdza, czy nauczycielowi wolno wystawić ocenę. Z zależności wyciągana jest informacja o sesji i osobie wołającej ten punkt końcowy. Z ciała zapytania wyciągane są informacje o ocenie, a ze ścieżki zasobu – identyfikatory grupy i studenta. Do sprawdzenia uprawnień wystarczą dwa z nich: `caller.idx` z tokenu i `group_id` ze ścieżki. Kwerenda sprawdza, czy prowadzący o tym identyfikatorze uczy (`TEACHES`) grupę o podanym UUID. Jeśli tak, to zostanie zwrócona grupa. Jeśli nie, to zostanie zwrócone `None`, co skutkuje przedwczesnym zatrzymaniem wykonania funkcji przez błąd 403 Forbidden.

Reguła ReBAC sprawia, że podmiana `group_id` na cudzą grupę nic nie daje, ponieważ nie będzie oczekiwanej ścieżki od nauczyciela zaszytego w tokenie do cudzej grupy. 

Jednocześnie administracja omija tę zasadę poprzez instrukcję warunkową na początku funkcji. Warunek sprawdza obie role, ponieważ osoba może mieć jednocześnie rolę prowadzącego i administratora – wtedy obowiązują uprawnienia szersze.

W ten sam sposób łączy oba mechanizmy pokazana wcześniej funkcja `_require_registration()`: punkty końcowe `/me/registrations/{registration_id}/...` wywołują ją z `caller.idx` jako identyfikatorem studenta i `registration_id` ze ścieżki.

```http
PUT /groups/543cca5f-00db-5e15-a47b-b826bb7009d9/students/280601/grade
Authorization: Bearer <token prowadzącego T001>

{"grade": 5.0}
```

```json
{
  "detail": "Forbidden"
}
```

*Odpowiedź 403 na próbę wystawienia oceny w grupie, której prowadzący nie uczy*

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

```json
{
    "idx": "279413",
    "name": "Anna",
    "surname": "Kowalska",
    "phone": "600111222",
    "photo": "279413.jpg",
    "joined": "2023-10-01T00:00:00+01:00",
    "avg_grade": 4.026,
    "term_ids": [
        "69b50b3d-04e3-54d1-a39a-b2a4eeba7d72"
    ]
}
```

*Odpowiedź 200 na `GET /api/students/279413` (administrator)*

```http
PUT /me/registered-groups/c798fc10-c169-58c8-9c55-c0fd2d104535
```

```json
{
  "detail": "Group is full"
}
```

*Żądanie zapisu studenta do pełnej grupy i odpowiedź 409*

```json
// TODO: przykładowa odpowiedź 201 z nagłówkiem Location – np. POST /api/admin/groups
```

5.5.9 Przykładowe żądania i odpowiedzi
- po jednym na moduł z 4.5.1 (public, catalogue, student, teacher, admin)

```json
// TODO: GET /api/subjects?name=Algebra
```

```json
// TODO: GET /api/me/registered-groups
```

```json
// TODO: GET /api/groups/{group_id}/students
```

```json
// TODO: GET /api/admin/people/next-idx
```

5.6 Klient