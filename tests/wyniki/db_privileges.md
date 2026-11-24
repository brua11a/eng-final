## Neo4j (konto `app`)

| Operacja | Zapytanie | Powinna się udać | Udała się | Komunikat | Zgodny |
| --- | --- | --- | --- | --- | --- |
| odczyt danych (kontrola) | `MATCH (g:Group) RETURN count(g)` | tak | tak | – | tak |
| zapis danych (kontrola) | `CREATE (r:Room {id: 'test-r', building: 'test', room_num: '0'}) DELETE r` | tak | tak | – | tak |
| LOAD CSV: plik z katalogu importu serwera | `LOAD CSV FROM 'file:///nodes/groups.csv' AS row RETURN count(row)` | nie | nie | LOAD on URL 'file:///import/nodes/groups.csv' is denied for user 'app' with roles [PUBLIC, app_rw]. | tak |
| LOAD CSV: adres usługi w sieci wewnętrznej (SSRF) | `LOAD CSV FROM 'https://app:8000/api/openapi.json' AS row RETURN count(row)` | nie | nie | LOAD on URL 'https://app:8000/api/openapi.json' is denied for user 'app' with roles [PUBLIC, app_rw]. | tak |
| nowa etykieta spoza schematu | `CREATE (n:Janitor {name: 'test'}) DELETE n` | nie | nie | Creating new node label on database 'neo4j' is not allowed for user 'app' with roles [PUBLIC, app_rw]. See GRANT CREATE NEW NODE LABEL ON DATABASE 'ne | tak |
| nowe ograniczenie | `CREATE CONSTRAINT test_constraint FOR (g:Group) REQUIRE g.number IS NOT NULL` | nie | nie | Schema operation 'create_constraint' on database 'neo4j' is not allowed for user 'app' with roles [PUBLIC, app_rw]. | tak |
| usunięcie ograniczenia | `DROP CONSTRAINT person_idx` | nie | nie | Schema operation 'drop_constraint' on database 'neo4j' is not allowed for user 'app' with roles [PUBLIC, app_rw]. | tak |
| nowy indeks | `CREATE INDEX test_index FOR (g:Group) ON (g.number)` | nie | nie | Schema operation 'create_index' on database 'neo4j' is not allowed for user 'app' with roles [PUBLIC, app_rw]. | tak |
| lista kont bazy | `SHOW USERS` | nie | nie | Permission has not been granted for SHOW USER. Try executing SHOW USER PRIVILEGES to determine the missing or denied privileges. In case of missing pr | tak |
| utworzenie konta | `CREATE USER test_user SET PASSWORD 'test-password-123'` | nie | nie | Permission has not been granted for CREATE USER. Try executing SHOW USER PRIVILEGES to determine the missing or denied privileges. In case of missing  | tak |
| nadanie sobie roli admin | `GRANT ROLE admin TO app` | nie | nie | Permission has not been granted for ASSIGN ROLE. Try executing SHOW USER PRIVILEGES to determine the missing or denied privileges. In case of missing  | tak |

## PostgreSQL (konto `app`)

| Operacja | Zapytanie | Powinna się udać | Udała się | Komunikat | Zgodny |
| --- | --- | --- | --- | --- | --- |
| odczyt danych (kontrola) | `SELECT count(*) FROM person` | tak | tak | – | tak |
| zapis danych (kontrola) | `INSERT INTO room (id, building, room_num) VALUES ('test-r', 'test', '0')` | tak | tak | – | tak |
| COPY z pliku serwera | `COPY person FROM '/data/person.csv' WITH (FORMAT csv, HEADER match)` | nie | nie | permission denied to COPY from a file | tak |
| odczyt pliku serwera (pg_read_file) | `SELECT pg_read_file('/etc/passwd')` | nie | nie | permission denied for function pg_read_file | tak |
| zapis pliku serwera (COPY TO) | `COPY (SELECT 1) TO '/tmp/test.csv'` | nie | nie | permission denied to COPY to a file | tak |
| nowa tabela | `CREATE TABLE test_table (x int)` | nie | nie | permission denied for schema public | tak |
| zmiana tabeli | `ALTER TABLE person ADD COLUMN test int` | nie | nie | must be owner of table person | tak |
| usunięcie tabeli | `DROP TABLE opinion_content` | nie | nie | must be owner of table opinion_content | tak |
| TRUNCATE | `TRUNCATE opinion_content` | nie | nie | permission denied for table opinion_content | tak |
| skróty haseł kont (pg_authid) | `SELECT rolpassword FROM pg_authid` | nie | nie | permission denied for table pg_authid | tak |
| utworzenie konta | `CREATE ROLE test_role` | nie | nie | permission denied to create role | tak |

Wynik: OK
