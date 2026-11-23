zrobie na samym koncu 

najwazniejsze wnioski to:
- nowy mechanizm GRAPH TYPE nie jest w stanie zastąpić CONSTRAINT pomimo tego, co piszą twórcy - nie da sie nim chociażby zdefiniować pustego węzła
- tradycyjna konwencja nazywania krawędzi i węzłów nie skaluje się dobrze
- brak możliwości określania poziomu izolacji bez ustawiania zmiennej to calkiem spore faux pas
- nie istnieje (z tego co wiem) wbudowany mechanizm inicjalizacji grafowej bazy danych; cypher-shell traktuje wartość `--param` jako wyrażenie Cypher, więc przekazanie hasła tą drogą było podatne na wstrzyknięcie kodu → konieczny własny skrypt ze sterownikiem (`init_db.py`)
- cos o performance ale to jak porobie testy
- wieloetykietowość, choć konceptualnie dobrze modeluje uprawnienia, nie skaluje się dobrze w tym rozwiązaniu przez brak hierarchii, przynajmniej z poziomu bazy danych
- implikowane etykiety sprawdzają się, ale obawiam się, że poleganie na nich w znacznym stopniu może się źle skalować
- graph type nie wyraża zależności między etykietami: `Inactive => User` jest niemożliwe, bo `User` ma własną definicję; obejście przez CONSTRAINT usuwa implikację `User => Person`, a implikacje nie są przechodnie (5.3.1)
- role w tokenie JWT: role `Student`/`Teacher` przestają działać od razu, bo kwerendy dopasowują etykietę w grafie; rola `Admin` wymagała unieważniania tokenów po stronie API (4.4.1, 5.5.6)
- o ile podział na węzły i etykiety ułatwia refractor (w stosunku bazy relacyjnej), to dalej nie jest on wygodny (https://neo4j.com/docs/getting-started/data-modeling/tutorial-refactoring/)
- "wolność" i "nieograniczoność" grafowych baz danych, chociaż brzmi dobrze, to zaczyna przeszkadzać, gdy trzeba zmodelować nimi prawdziwą platformę
- pisanie kwerend z wieloma krawędziami nie jest dużo wygodniejsze od pisania kwerend z wieloma joinami (aczkolwiek moze performance to uzasadni???? to sie okaze)
- Neo4j dostarczają dobry produkt z bardzo dobrą dokumentacją i zasobami do uczenia się, wady grafowej bazy danych wydają się wynikać z decyzji implementacyjnych wykonanych na poziomie języka Cypher, chociaż może w związku z wyjściem Cypher 25 będzie więcej dobrych zmian (chociażby GRAPH TYPE jest krokiem w dobrą stronę)
- jeszcze raz cos o performacne
- obecnie, w listopadzie 2026 RACZEJ w sposób grafowy bym konceptualizował strukturę, a potem przepisywał ją w sposób relacyjny, identyfikując przede wszystkim różnice wynikajace z istnienia kluczy obcych

**Podsumowanie:**

- czy udało się Wam zrealizować plan?
w sumie tak, na potrzeby prototypu jest ok
- jeśli nie, to co się nie udało?
ograniczenia baz grafowych sprawiają, że projektu nie ma sensu kończyć, póki technologia nie dojrzeje
- jakie są ograniczenia projektu? jakie ma wady?
skalowalność rozwiązania jest niezadowalająca, obecne zarządzanie dostępem jest kruche
- świadome uproszczenia: ocena na krawędzi `REGISTERED_IN` (brak historii zmian oceny w tej samej grupie, 4.3.3); lista unieważnionych tokenów w pamięci API (jeden proces, restart wylogowuje wszystkich); jedna strefa czasowa uczelni; `Inactive` bez etykiety `User` możliwe na poziomie bazy, regułę pilnuje API
- co można zrobić w przyszłości by to rozwinąć?
w sumie można zrobic wiecej tego samego, wiecej endpointow wiecej ekranow, ewentualnie mozna zrobic refractor samej bazy danych jesli funkcja bedzie tego wymagala
- ocena jako osobny węzeł `Grade` (reifikacja jak przy `Opinion`) → historia ocen; w grafie to tania refaktoryzacja: jedna kwerenda migrująca i zmiana 4 kwerend korzystających z `r.grade`
- lista unieważnionych tokenów we współdzielonym magazynie (np. Redis) przy kilku instancjach API
- co polecacie innym, by robili jak Wy, co NIE polecacie?
przy projektowaniu schematu bazy polecam myslec o tym, ze jeśli coś jest ogólnie mówiąc bytem (fizycznym lub niefizycznym) to jest to węzeł, a jeśli coś jest czynnością to jest to krawędź, trzymając tą zasadę w glowie układanie schematu okazuje sie duzo przyjemniejsze
nie polecam stawiac calej aplikacji na backendzie grafowym jesli struktura jest ważna