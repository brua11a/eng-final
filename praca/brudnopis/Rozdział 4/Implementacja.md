zrob szybko

5.x Struktura repozytorium

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

W katalogu `app/` znajduje się backend, w tym warstwa API. W podkatalogu `schemas/` zdefiniowano modele Pydantic, opisujące oczekiwany kształt żądań i odpowiedzi serwera – na ich podstawie API sprawdza poprawność danych wejściowych i formatuje dane wyjściowe. Obsługa żądania przebiega następująco: API odbiera żądanie na wybranym punkcie końcowym, weryfikuje token i uprawnienia użytkownika, otwiera sesję bazy danych, a następnie – jeśli wykorzystywany jest backend grafowy (katalog `graph_backend/`) – wykonuje zapytanie w języku Cypher, przekształca jego wynik do oczekiwanego kształtu i zwraca go klientowi. Zapytania wykonywane są bezpośrednio przez oficjalny, asynchroniczny sterownik Neo4j dla języka Python [CYTOWANIE: https://neo4j.com/docs/api/python-driver/current/].

*todo* W tym samym katalogu, w podkatalogu `relation_backend/`, znajdzie się implementacja relacyjna podobnego systemu. Będzie ona działać w ten sam sposób – poprzez sterownik bazy danych zamiast mapowania obiektowo-relacyjnego. Oba backendy będą korzystać z tych samych modeli Pydantic.

Ponieważ eksploracja bazy danych jest szczególnym celem tej pracy, poświęcono jej dużą część repozytorium. W katalogu `import/` znajdują się dane w formacie CSV (ang. *Comma-Separated Values*), importowane przy inicjalizacji bazy danych – `nodes/` zawiera węzły, a `edges/` krawędzie. Na każdy typ węzła i na każdy typ krawędzi przypada osobny plik. Wyjątkiem jest etykieta User – dane logowania (adres e-mail i skrót hasła) są kolumnami w plikach studentów, prowadzących i administratorów, a etykieta nadawana jest przy imporcie tym osobom, które mają podany adres e-mail.

W katalogu `queries/` znajdują się instrukcje w języku Cypher wykonywane przy inicjalizacji bazy danych przez skrypt `init.sh`: `schema.cypher` narzuca kształt węzłów i krawędzi oraz pozostałe ograniczenia, `nodes.cypher` i `edges.cypher` wczytują pliki CSV z węzłami i krawędziami, a `security.cypher` tworzy konto bazodanowe, którym łączy się API (4.4.3).

Definicja typu grafu w `schema.cypher` jest zapisana w wersji Cypher 25 (`CYPHER 25 ALTER CURRENT GRAPH TYPE SET ...`), ponieważ ta funkcja jest dostępna wyłącznie w tej wersji języka. Pozostałe zapytania, zarówno importujące, jak i wykonywane przez API, korzystają z domyślnej wersji języka skonfigurowanej w bazie.

Dane dostępowe (hasła do bazy danych i klucz podpisujący tokeny) przechowywane są w pliku `.env`, który nie trafia do repozytorium. Wymagane zmienne opisano w pliku `.env.example`. Katalog `endpoint_schema/` zawiera dokumentację punktów końcowych API: dozwolone role, kształt żądań i odpowiedzi oraz wykonywane zapytania. Ponadto API generuje interaktywną dokumentację w standardzie OpenAPI [CYTOWANIE: https://fastapi.tiangolo.com/reference/openapi/docs/], na podstawie tych samych modeli, które służą do walidacji.
