4.1 Architektura systemu

System składa się z następujących części:
- klienta webowego w Vue,
- warstwy API z backendem grafowym,
- warstwy API z backendem relacyjnym (todo),
- warstwy bazy danych,
- warstwy konteneryzacji i wdrożenia,
- dokumentacji.

*todo: diagram - przeglądarka → klient Vue (nginx) → API (FastAPI) → Neo4j, kontener `init`; kto z kim się komunikuje i jakim kontem*

4.2 Struktura repozytorium

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

Klient Vue jest w całości zawarty w katalogu `frontend/`. Jego zadaniem jest umożliwienie wygodnej komunikacji z API, a także wyświetlanie uwierzytelnionemu użytkownikowi jedynie tych zakładek, do których ma on dostęp.

W katalogu `app/` znajduje się backend, w tym warstwa API. W podkatalogu `schemas/` zdefiniowano modele Pydantic, opisujące oczekiwany kształt żądań i odpowiedzi serwera - na ich podstawie API sprawdza poprawność danych wejściowych i formatuje dane wyjściowe. Obsługa żądania przebiega następująco: API odbiera żądanie na wybranym punkcie końcowym, weryfikuje token i uprawnienia użytkownika, otwiera sesję bazy danych, a następnie - jeśli wykorzystywany jest backend grafowy (katalog `graph_backend/`) - wykonuje kwerendę w języku Cypher, przekształca jej wynik do oczekiwanego kształtu i zwraca go klientowi. Zapytania wykonywane są bezpośrednio przez oficjalny, asynchroniczny driver Neo4j dla Pythona, bez warstwy mapowania obiektowo-grafowego (OGM, ang. *Object-Graph Mapping*). Oficjalna biblioteka Neo4j-OGM jest dostępna jedynie dla języka Java (https://neo4j.com/docs/ogm-manual/current/reference/), a dla Pythona istnieje rozwijana w ramach Neo4j Labs biblioteka neomodel [CYTOWANIE]. Zrezygnowano z niej, aby zachować pełną kontrolę nad treścią zapytań oraz aby porównanie z backendem relacyjnym, również korzystającym z surowego drivera, było miarodajne.

*todo* W tym samym katalogu, w podkatalogu `relation_backend/`, znajdzie się implementacja relacyjna podobnego systemu. Będzie ona działać w ten sam sposób - poprzez surowy driver bazy danych zamiast mapowania obiektowo-relacyjnego (ORM, ang. *Object-Relational Mapping*). Oba backendy będą korzystać z tych samych modeli Pydantic, dzięki czemu wymiana backendu będzie dla klienta niezauważalna.

Ponieważ eksploracja bazy danych jest szczególnym celem tej pracy, poświęcono jej dużą część repozytorium. W katalogu `import/` znajdują się dane w formacie `.csv`, importowane przy inicjalizacji bazy danych - `nodes/` zawiera węzły, a `edges/` krawędzie. Na każdy typ węzła i na każdy typ krawędzi przypada osobny plik. Wyjątkiem jest etykieta `User` - dane logowania (adres e-mail i skrót hasła) są kolumnami w plikach studentów, prowadzących i administratorów, a etykieta nadawana jest przy imporcie tym osobom, które mają podany adres e-mail.

W katalogu `queries/` znajdują się instrukcje w języku Cypher wykonywane przy inicjalizacji bazy danych przez skrypt `init.sh`:
- `schema.cypher` - narzucenie kształtu węzłów i krawędzi oraz pozostałych ograniczeń,
- `nodes.cypher` i `edges.cypher` - wczytanie plików `.csv` z węzłami i krawędziami,
- `security.cypher` - utworzenie konta bazodanowego, którym łączy się API, z uprawnieniami ograniczonymi do odczytu i zapisu danych.

Definicja typu grafu (ang. *graph type*) w `schema.cypher` jest zapisana w wersji Cypher 25 (`CYPHER 25 ALTER CURRENT GRAPH TYPE SET ...`), ponieważ ta funkcjonalność jest dostępna wyłącznie w tej wersji języka. Pozostałe kwerendy, zarówno importujące, jak i wykonywane przez API, korzystają z domyślnej wersji języka skonfigurowanej w bazie.

Dane dostępowe (hasła do bazy danych i klucz podpisujący tokeny) przechowywane są w pliku `.env`, który nie trafia do repozytorium. Wymagane zmienne opisano w pliku `.env.example`. Katalog `endpoint_schema/` zawiera dokumentację endpointów API: dozwolone role, kształt żądań i odpowiedzi oraz wykonywane zapytania bazodanowe.

4.3 Model danych

![[Untitled graph(2).png]]

*Wizualizacja proponowanego modelu bazy danych wykonana przy pomocy arrows.app*

4.3.1 Osoby i użytkownicy

W domenie uczelnianej zdefiniowano następujące etykiety osób: Student dla studentów, Teacher dla prowadzących zajęć oraz Admin dla administratorów i innych osób zarządzających uczelnią. Aby jedna osoba mogła mieć jednocześnie kilka ról (np. prowadzący będący zarazem administratorem), etykiety ról przechowują wyłącznie informacje właściwe dla danej roli. Dane wspólne dla każdej osoby, takie jak imię, nazwisko i numer telefonu, znajdują się we współdzielonej etykiecie Person.

![[Pasted image 20261110202719.png]]

*Przykład osoby z wieloma etykietami: Admin, Student, Teacher, User, Inactive i Person jednocześnie*

![[Pasted image 20261110203022.png]]

*Wizualizacja - podział cech na przynależność do etykiety, gdzie nie każda z etykiet dodaje cechy*

Dane służące do uwierzytelniania (adres e-mail i skrót hasła) przechowywane są w etykiecie User - dopiero ona czyni węzeł osoby pełnoprawnym użytkownikiem, który może zalogować się w portalu i uwierzytelnić w API. Osoba bez etykiety User istnieje w danych (np. jako prowadzący widoczny w katalogu zajęć), ale nie ma dostępu do systemu.

Do tego istnieje etykieta Inactive, która pozwala niedestruktywnie odebrać użytkownikowi dostęp do wszystkich punktów końcowych; przechowuje ona moment dezaktywacji. Bez tej lub podobnej funkcyjnie etykiety odebranie dostępu wymagałoby usunięcia etykiety User wraz z danymi logowania, co powodowałoby utratę danych. Charakter platformy uczelnianej nie zakłada rozbudowanego systemu blokad i kar dla użytkowników - tymczasowe odebranie dostępu wynika raczej z sytuacji takich jak zawieszenie w prawach studenta lub cofnięcie uprawnień do prowadzenia zajęć, dlatego jedna etykieta jest wystarczająca.

Każda z etykiet osób ma zdefiniowane właściwości, z których większość jest wymagana; opcjonalne jest jedynie zdjęcie. Kluczem (wartością niepowtarzalną i zawsze obecną) każdej osoby jest `idx` - numer indeksu lub inny sekwencyjny identyfikator. Dodatkowo kluczem etykiety User jest adres e-mail. Ponadto kombinacja imienia, nazwiska i numeru telefonu musi być unikalna, co zapobiega przypadkowemu wprowadzeniu tej samej osoby dwukrotnie pod różnymi identyfikatorami. Etykieta Admin nie ma własnych właściwości - jej obecność sama w sobie nadaje uprawnienia administracyjne.

| Etykieta | Właściwość | Typ | Wymagana | Ograniczenia | Opis |
|---|---|---|---|---|---|
| Person | `idx` | tekst | tak | klucz | numer indeksu lub inny identyfikator osoby |
| | `name` | tekst | tak | unikalne razem z `surname` i `phone` | imię |
| | `surname` | tekst | tak | (j.w.) | nazwisko |
| | `phone` | tekst | tak | (j.w.) | numer telefonu |
| | `photo` | tekst | nie | – | ścieżka do zdjęcia |
| Student | `joined` | data i czas ze strefą | tak | – | moment rozpoczęcia studiów |
| Teacher | `degree` | tekst | tak | – | stopień lub tytuł naukowy |
| | `working_since` | data | tak | – | data zatrudnienia |
| Admin | – | – | – | – | etykieta bez właściwości, nadaje uprawnienia administracyjne |
| User | `email` | tekst | tak | klucz | login |
| | `passwd_hash` | tekst | tak | – | skrót hasła (bcrypt) |
| Inactive | `deactivated_at` | data i czas ze strefą | tak | – | moment dezaktywacji konta |
*Właściwości etykiet osób*

Aby nie było możliwe utworzenie np. węzła z etykietą Student, który nie ma etykiety Person, wykorzystano mechanizm etykiet implikowanych. Każda z etykiet ról - Student, Teacher i Admin - implikuje etykietę Person, zatem nie da się nadać żadnej z nich bez jednoczesnego nadania etykiety Person i uzupełnienia jej wymaganych właściwości. Tak samo etykiety User i Inactive implikują etykietę Person.

![[Pasted image 20261110203108.png]]

*Przykładowa próba utworzenia węzła z etykietą Student bez właściwości wymaganych przez etykietę Person*

4.3.2 Oferta dydaktyczna

*todo: opis etykiet Faculty (wydział), Programme (kierunek), Curriculum (plan studiów dla danego rocznika - intake_year), CurriculumTerm (semestr planu), Subject (przedmiot), SubjectInstance (realizacja przedmiotu w danym cyklu), AcademicCycle (cykl akademicki - rok + semestr zimowy/letni)*

*todo: decyzja projektowa - Subject jako szablon z planu studiów vs SubjectInstance jako jego realizacja w konkretnym cyklu (to do niej podpięte są typy zajęć i grupy); dlaczego student jest zapisany (ENROLLED) na semestr planu, a nie na kierunek*

4.3.3 Zajęcia

*todo: opis etykiet Group (grupa zajęciowa - termin, kod, limit miejsc), GroupType (forma zajęć - wykład, ćwiczenia, laboratorium... - z wagą do oceny), Room (sala - budynek + numer)*

*todo: decyzja projektowa - ocena (grade) i moment zapisu (registered_at) jako właściwości krawędzi REGISTERED_IN między studentem a grupą; porównanie z tabelą łączącą w modelu relacyjnym*

4.3.4 Zapisy na zajęcia

*todo: opis etykiet Registration (zapisy dla danego cyklu i wydziału) i RegistrationTurn (tura - data i godziny), krawędzie OPENS (zapisy otwierają grupy), HAS_TURN, ASSIGNED (student przypisany do tury)*

4.3.5 Opinie

*todo: opis etykiety Opinion (ocena liczbowa, treść, moment wystawienia)*

*todo: decyzja projektowa - dlaczego opinia jest węzłem, a nie krawędzią: łączy trzy byty (autora, grupę, prowadzącego - krawędzie WRITES, ABOUT, ABOUT_TEACHER) i ma własne właściwości (reifikacja relacji)*

4.3.6 Krawędzie i kardynalność

*todo: tabela - typ krawędzi | od | do | znaczenie | kardynalność wynikająca z domeny (22 typy)*

W modelu grafowym nie są potrzebne tabele łączące ani klucze obce - każde powiązanie między węzłami jest krawędzią, niezależnie od tego, czy w modelu relacyjnym byłoby powiązaniem jeden-do-wielu, czy wiele-do-wielu. Kardynalność nadal wynika jednak z domeny (np. grupa zajęciowa odbywa się w jednej sali, a w jednej sali odbywa się wiele grup).

4.3.7 Ograniczenia schematu

Bazy grafowe domyślnie nie wymuszają schematu, a w tym projekcie dane muszą mieć ściśle określoną strukturę. Dlatego zdefiniowano typ grafu (ang. *graph type*), który wymusza:
- etykiety implikowane (opisane w 4.3.1),
- podanie i istnienie właściwości (`NOT NULL`),
- typy danych właściwości (m.in. tekst, liczby całkowite i zmiennoprzecinkowe, daty, godziny i znaczniki czasu ze strefą czasową),
- klucze i ograniczenia unikalności (również złożone, np. budynek i numer sali, rok i semestr cyklu akademickiego),
- typy węzłów na obu końcach każdego typu krawędzi (np. krawędź TEACHES może prowadzić tylko od prowadzącego do grupy).

Typ grafu nie wymusza natomiast kardynalności krawędzi - nic w bazie nie zabrania podpięcia grupy do dwóch sal. Kardynalność pilnowana jest przez punkty końcowe API, które tworzą krawędzie. Kardynalność można by narzucić po stronie aplikacji za pomocą biblioteki neomodel [CYTOWANIE: https://deepwiki.com/neo4j-contrib/neomodel/2.4-relationships-and-cardinality], która integruje się m.in. z frameworkiem Django. Zrezygnowano z niej z powodów opisanych w 4.2 - zachowania pełnej kontroli nad treścią zapytań i miarodajności porównania z backendem relacyjnym - oraz na rzecz modularnego REST API korzystającego bezpośrednio z drivera Neo4j [CYTOWANIE: https://neo4j.com/docs/api/python-driver/current/].

*todo: zdanie o tym, że typ grafu nie zabrania etykiet/właściwości spoza definicji (sprawdzić w dokumentacji, czy graph type w Neo4j jest otwarty)*

4.4 Kontrola dostępu

*todo: uwierzytelnianie (bcrypt, JWT z rolami), autoryzacja (rola przy endpoincie + relacje sprawdzane kwerendą - RBAC/ReBAC), konto bazodanowe o ograniczonych uprawnieniach*

4.5 Interfejs API

*todo: podział na moduły (public, catalogue, student, teacher, admin), konwencje (błędy w polu err, 422 przy walidacji)*
