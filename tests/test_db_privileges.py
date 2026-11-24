"""Uprawnienia kont bazodanowych API (zasada najmniejszych uprawnień, 3.3, 4.4.3, 6.3).

API łączy się z bazami kontami z ograniczonymi uprawnieniami: wolno im odczytywać i zapisywać dane,
ale nie zmieniać schematu, zarządzać kontami ani czytać plików serwera bazy. Skrypt wykonuje
w kontenerze app, tymi samymi kontami co API, operacje dozwolone (kontrola) i zabronione.

Odmowa jest uznawana tylko wtedy, gdy komunikat bazy wskazuje brak uprawnień (a nie np. błąd sieci).
Operacje wykonywane są w transakcjach, które zawsze są wycofywane, więc nawet operacja błędnie
dozwolona nie zmieni bazy (w PostgreSQL również instrukcje DDL podlegają transakcjom).

Uruchomienie:
    python tests/test_db_privileges.py [--out wynik.md]
"""

import argparse
from pathlib import Path

from common import finish, in_app, ok, table

# (opis, baza Neo4j "neo4j"/"system", zapytanie, czy powinno się udać)
NEO4J = [
    ("odczyt danych (kontrola)", "neo4j", "MATCH (g:Group) RETURN count(g)", True),
    ("zapis danych (kontrola)", "neo4j",
     "CREATE (r:Room {id: 'test-r', building: 'test', room_num: '0'}) DELETE r", True),
    ("LOAD CSV: plik z katalogu importu serwera", "neo4j",
     "LOAD CSV FROM 'file:///nodes/groups.csv' AS row RETURN count(row)", False),
    ("LOAD CSV: adres usługi w sieci wewnętrznej (SSRF)", "neo4j",
     "LOAD CSV FROM 'https://app:8000/api/openapi.json' AS row RETURN count(row)", False),
    ("nowa etykieta spoza schematu", "neo4j", "CREATE (n:Janitor {name: 'test'}) DELETE n", False),
    ("nowe ograniczenie", "neo4j",
     "CREATE CONSTRAINT test_constraint FOR (g:Group) REQUIRE g.number IS NOT NULL", False),
    ("usunięcie ograniczenia", "neo4j", "DROP CONSTRAINT person_idx", False),
    ("nowy indeks", "neo4j", "CREATE INDEX test_index FOR (g:Group) ON (g.number)", False),
    ("lista kont bazy", "system", "SHOW USERS", False),
    ("utworzenie konta", "system", "CREATE USER test_user SET PASSWORD 'test-password-123'", False),
    ("nadanie sobie roli admin", "system", "GRANT ROLE admin TO app", False),
]

POSTGRES = [
    ("odczyt danych (kontrola)", "SELECT count(*) FROM person", True),
    ("zapis danych (kontrola)", "INSERT INTO room (id, building, room_num) VALUES ('test-r', 'test', '0')", True),
    ("COPY z pliku serwera", "COPY person FROM '/data/person.csv' WITH (FORMAT csv, HEADER match)", False),
    ("odczyt pliku serwera (pg_read_file)", "SELECT pg_read_file('/etc/passwd')", False),
    ("zapis pliku serwera (COPY TO)", "COPY (SELECT 1) TO '/tmp/test.csv'", False),
    ("nowa tabela", "CREATE TABLE test_table (x int)", False),
    ("zmiana tabeli", "ALTER TABLE person ADD COLUMN test int", False),
    ("usunięcie tabeli", "DROP TABLE opinion_content", False),
    ("TRUNCATE", "TRUNCATE opinion_content", False),
    ("skróty haseł kont (pg_authid)", "SELECT rolpassword FROM pg_authid", False),
    ("utworzenie konta", "CREATE ROLE test_role", False),
]

_RUN = r'''
import psycopg
from neo4j.exceptions import Neo4jError

async def neo4j_try(db, query):
    async with driver.session(database=db) as s:
        tx = await s.begin_transaction()
        try:
            await (await tx.run(query)).consume()
            return {"allowed": True, "message": ""}
        except Neo4jError as e:
            return {"allowed": False, "message": (getattr(e, "message", None) or str(e)).splitlines()[0][:150]}
        finally:
            await tx.rollback() if not tx.closed() else None

async def pg_try(conn, query):
    try:
        async with conn.transaction(force_rollback=True):
            await conn.execute(query)
        return {"allowed": True, "message": ""}
    except psycopg.Error as e:
        return {"allowed": False, "message": str(e).splitlines()[0][:150]}

async def main(args):
    neo = [await neo4j_try(db, query) for db, query in args["neo4j"]]
    conn = await psycopg.AsyncConnection.connect(os.environ["PG_CONNINFO"], password=os.environ["PG_PASSWORD"])
    async with conn:
        pg = [await pg_try(conn, query) for query in args["postgres"]]
        who = (await (await conn.execute("SELECT current_user")).fetchone())[0]
    return {"neo4j": neo, "postgres": pg, "neo4j_user": os.environ["NEO4J_USER"], "pg_user": who}
'''


# Odmowa musi wynikać z braku uprawnień, a nie np. z błędu sieci czy składni.
_DENIAL = ("denied", "not allowed", "not been granted", "permission denied", "must be owner")


def rows_for(cases, results, prefix: str, errors: list) -> list[list]:
    rows = []
    for case, res in zip(cases, results):
        name, query, should = case[0], case[-2], case[-1]
        denied_by_privilege = any(m in res["message"].lower() for m in _DENIAL)
        good = res["allowed"] if should else (not res["allowed"] and denied_by_privilege)
        rows.append([name, f"`{query}`", "tak" if should else "nie", "tak" if res["allowed"] else "nie",
                     res["message"].replace("`", "'").replace("|", "/") or "–", ok(good)])
        if not good:
            errors.append(f"{prefix}: {name}: {'dozwolone' if res['allowed'] else 'zabronione'} ({res['message']})")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    out = in_app(_RUN, neo4j=[[db, query] for _, db, query, _ in NEO4J], postgres=[query for _, query, _ in POSTGRES])
    errors = []
    header = ["Operacja", "Zapytanie", "Powinna się udać", "Udała się", "Komunikat", "Zgodny"]
    md = "\n\n".join([
        f"## Neo4j (konto `{out['neo4j_user']}`)",
        table(header, rows_for(NEO4J, out["neo4j"], "Neo4j", errors)),
        f"## PostgreSQL (konto `{out['pg_user']}`)",
        table(header, rows_for(POSTGRES, out["postgres"], "PostgreSQL", errors)),
    ])
    finish(md, errors, args.out)


if __name__ == "__main__":
    main()
