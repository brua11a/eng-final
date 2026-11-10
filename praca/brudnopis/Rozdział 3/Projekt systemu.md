Sam projekt jest podzielony na:
- klienta Vue
- warstwę API z backendem grafowym
- warstwę API z backendem relacyjnym (todo)
- warstwę bazy danych
- warstwę konteneryzacji i wdrożenia
- dokumentację

```
.
├── app
│   ├── graph_backend
│   │   ├── auth
│   │   └── routers
│   ├── models
│   └── schemas
├── endpoint_schema
├── frontend
│   └── src
│       ├── api
│       ├── components
│       │   └── catalogue
│       ├── composables
│       ├── layouts
│       ├── router
│       ├── stores
│       ├── styles
│       ├── utils
│       └── views
│           ├── admin
│           ├── catalogue
│           ├── shared
│           ├── student
│           └── teacher
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.api
├── init.sh
├── requirements.txt
├── import
│   ├── edges
│   └── nodes
└── queries
```

3.1 Ogólny podział
Klient Vue jest w całości zawarty w katalogu `frontend/`. Jego zadaniem jest umożliwienie wygodnej komunikacji z API, a także wyświetlanie zautentykowanemu użytkownikowi jedynie tych zakładek, do których ten ma dostęp.

W katalogu `app/` znajduje się backend, w tym warstwa API. Zdefiniowana tam jest *schema* w postaci oczekiwanych kształtów zapytań i odpowiedzi ze strony serwera. Jest to potrzebne do zaimplementowania funkcji wywoływanych w API. Większość z nich przyjmuje na wybrany endpoint odpowiednie zapytanie. Następnie sprawdzane są uprawnienie osoby wysyłającej zapytanie i uzyskiwana sesja. Jeśli jest wykorzystywany backend grafowy (zawarty w katalogu `graph_backend/`), wykonywana jest kwerenda w języku Cypher, a jej wynik jest transformowany do oczekiwanego kształtu i zwracany klientowi. Kwerendy wykonywane są bezpośrednio przez oficjalny, asynchroniczny driver Neo4j dla Pythona, bez warstwy mapowania obiektowo-grafowego (OGM, ang. *Object-Graph Mapping*). Oficjalna biblioteka Neo4j-OGM jest dostępna jedynie dla języka Java (https://neo4j.com/docs/ogm-manual/current/reference/), a dla Pythona istnieje rozwijana w ramach Neo4j Labs biblioteka neomodel [CYTOWANIE]. Zrezygnowano z niej, aby zachować pełną kontrolę nad treścią zapytań oraz aby porównanie z backendem relacyjnym, również korzystającym z surowego drivera, było miarodajne.

*todo* W tym samym katalogu, w podkatalogu `relation_backend/` znajduje się implementacja relacyjna podobnego systemu. Działa ona w podobny sposób, poprzez surowy driver bazy danych zamiast mapowania obiektowo-relacyjnego (ORM, ang. *Object-Relational Mapping*), żeby porównanie dwóch rozwiązań było miarodajne. Zdefiniowana wcześniej schema może, a nawet powinna być wykorzystywana przy obydwu rozwiązaniach, dzięki temu dla klienta transparentna będzie wymiana backendu.

Z racji tego, że eksploracja bazy danych jest szczególnym celem tej pracy dyplomowej, poświęciłem jej dużo miejsca w repozytorium projektowym. W katalogu `import/` znajdują się dane w formacie `.csv` do importu przy inicjalizacji bazy danych - `nodes/` zawiera węzły, `edges/` zawiera krawędzie. Na każdy typ węzła i na każdy typ krawędzi poświęcony jest osobny plik. Wyjątkiem jest etykieta `User` - dane logowania (adres e-mail i skrót hasła) są kolumnami w plikach studentów, prowadzących i administratorów, a etykieta nadawana jest przy imporcie tym osobom, które mają podany adres e-mail. W modelu grafowym nie są potrzebne tabele łączące ani klucze obce - każde powiązanie między węzłami jest krawędzią, niezależnie od tego, czy w modelu relacyjnym byłoby powiązaniem jeden-do-wielu, czy wiele-do-wielu. Kardynalność nadal wynika jednak z domeny (np. grupa zajęciowa odbywa się w jednej sali), a typ grafu jej nie wymusza - pilnują jej endpointy API, które tworzą krawędzie.

W katalogu `queries/` zawarte są instrukcje w języku Cypher potrzebne do inicjalizacji bazy danych - zarówno narzucenie kształtu węzłów i krawędzi oraz innych ograniczeń (`schema.cypher`), jak i odczytanie i załadowanie do bazy danych plików `.csv` z węzłami i krawędziami (`nodes.cypher`, `edges.cypher`). Definicja typu grafu (ang. *graph type*) w `schema.cypher` jest zapisana w wersji Cypher 25 (`CYPHER 25 ALTER CURRENT GRAPH TYPE SET ...`), ponieważ ta funkcjonalność jest dostępna wyłącznie w tej wersji języka. Pozostałe kwerendy, zarówno importujące, jak i wykonywane przez API, korzystają z domyślnej wersji języka skonfigurowanej w bazie. Szczególne znaczenie będzie miała tutaj schema bazodanowe, ponieważ bazy danych grafowe z natury są "nieograniczone" i "wolne", a nam zależy na ich ustrukturyzowaniu.

3.2 