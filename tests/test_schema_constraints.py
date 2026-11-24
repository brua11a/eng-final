"""Ograniczenia schematu bazy grafowej (3.3, 4.3.7, 5.3.1).

Każdy przypadek to próba zapisu niepoprawnych danych bezpośrednio do bazy, z pominięciem API,
kontem, którym łączy się API (`app`). Sprawdza to, które reguły modelu wymusza sama baza danych
(typ grafu i ograniczenia), a które pilnuje dopiero API lub walidacja Pydantic.

  Część A - reguły, które baza powinna odrzucić (typ grafu, klucze, unikalność, typy krawędzi).
  Część B - reguły, których typ grafu nie wyraża (4.3.7); baza przyjmuje takie dane, a regułę
            egzekwuje API. Ten wynik jest oczekiwany i dokumentuje ograniczenia modelu.

Każdy przypadek jest osobną transakcją zatwierdzaną (część ograniczeń, np. istnienie właściwości,
Neo4j sprawdza dopiero przy zatwierdzeniu). Dane przyjęte przez bazę są usuwane zaraz po próbie;
wszystkie tworzone węzły mają identyfikatory z prefiksem "test-".

Uruchomienie:
    python tests/test_schema_constraints.py [--out wynik.md]
"""

import argparse
from pathlib import Path

from common import finish, in_app, ok, table

# (reguła, zapytanie, sprzątanie po przyjęciu). Parametry $... pochodzą z danych początkowych.
REJECT = [
    ("typ właściwości: dzień tygodnia jako tekst",
     "CREATE (:Group {id: 'test-g', weekday: '1', number: 1, pnp: 'ALL', capacity: 10, "
     "start_time: localtime('08:00'), end_time: localtime('09:00')})"),
    ("wymagana właściwość: grupa bez limitu miejsc",
     "CREATE (:Group {id: 'test-g', weekday: 1, number: 1, pnp: 'ALL', "
     "start_time: localtime('08:00'), end_time: localtime('09:00')})"),
    ("typ właściwości: godzina zajęć jako tekst",
     "CREATE (:Group {id: 'test-g', weekday: 1, number: 1, pnp: 'ALL', capacity: 10, "
     "start_time: '08:00', end_time: localtime('09:00')})"),
    ("klucz: grupa z istniejącym identyfikatorem",
     "CREATE (:Group {id: $group, weekday: 1, number: 1, pnp: 'ALL', capacity: 10, "
     "start_time: localtime('08:00'), end_time: localtime('09:00')})"),
    ("unikalność złożona: sala (budynek, numer)",
     "CREATE (:Room {id: 'test-r', building: $building, room_num: $room_num})"),
    ("unikalność złożona: cykl (rok, semestr)",
     "CREATE (:AcademicCycle {id: 'test-c', year: $year, season: $season, "
     "start_date: date('2030-10-01'), end_date: date('2031-02-15')})"),
    ("etykieta implikowana: Student bez danych osoby (Person)",
     "CREATE (:Student {idx: 'test-s', joined: datetime()})"),
    ("unikalność osoby: imię, nazwisko i telefon",
     "CREATE (:Person:Student {idx: 'test-s', name: $name, surname: $surname, phone: $phone, joined: datetime()})"),
    ("klucz: konto z istniejącym adresem e-mail",
     "CREATE (:Person:Student:User {idx: 'test-s', name: 'T', surname: 'T', phone: 'test', joined: datetime(), "
     "email: $email, passwd_hash: 'x'})"),
    ("wymagana właściwość: Inactive bez momentu dezaktywacji",
     "CREATE (:Person:Inactive {idx: 'test-s', name: 'T', surname: 'T', phone: 'test'})"),
    ("typ węzła na końcu krawędzi: TEACHES od studenta",
     "MATCH (st:Student {idx: $student}), (g:Group {id: $group}) CREATE (st)-[:TEACHES]->(g)"),
    ("typ węzła na końcu krawędzi: IN_ROOM do przedmiotu",
     "MATCH (g:Group {id: $group}), (su:Subject {code: $subject}) CREATE (g)-[:IN_ROOM]->(su)"),
    ("wymagana właściwość krawędzi: zapis bez momentu zapisu",
     "MATCH (st:Student {idx: $student}), (g:Group {id: $free_group}) CREATE (st)-[:REGISTERED_IN]->(g)"),
    ("typ właściwości krawędzi: ocena jako tekst",
     "MATCH (st:Student {idx: $student}), (g:Group {id: $free_group}) "
     "CREATE (st)-[:REGISTERED_IN {registered_at: datetime(), grade: 'bdb'}]->(g)"),
]

# Grupa tymczasowa używana w części B.
_TEST_GROUP = ("CREATE (g:Group {id: 'test-g', weekday: 1, number: 1, pnp: 'ALL', capacity: 10, "
               "start_time: localtime('08:00'), end_time: localtime('09:00')}) ")
_CLEAN = "MATCH (n) WHERE n.id STARTS WITH 'test-' OR n.idx STARTS WITH 'test-' DETACH DELETE n"

ACCEPT = [
    ("dzień tygodnia spoza 1-7 (Pydantic, 5.3.1)",
     "CREATE (:Group {id: 'test-g', weekday: 9, number: 1, pnp: 'ALL', capacity: 10, "
     "start_time: localtime('08:00'), end_time: localtime('09:00')})", _CLEAN),
    ("parzystość tygodni spoza P/NP/ALL (Pydantic, 5.3.1)",
     "CREATE (:Group {id: 'test-g', weekday: 1, number: 1, pnp: 'X', capacity: 10, "
     "start_time: localtime('08:00'), end_time: localtime('09:00')})", _CLEAN),
    ("ocena spoza skali 2.0-5.0 (Pydantic, 5.5.4)",
     "MATCH (st:Student {idx: $student}), (g:Group {id: $free_group}) "
     "CREATE (st)-[:REGISTERED_IN {registered_at: datetime(), grade: 7.5}]->(g)",
     "MATCH (:Student {idx: $student})-[r:REGISTERED_IN]->(:Group {id: $free_group}) DELETE r"),
    ("grupa bez formy zajęć (API, 4.3.7)", _TEST_GROUP, _CLEAN),
    ("grupa w dwóch salach (API, 4.3.7)",
     _TEST_GROUP + "WITH g MATCH (r:Room) WITH g, r LIMIT 2 CREATE (g)-[:IN_ROOM]->(r)", _CLEAN),
    ("dwie grupy o tym samym numerze w jednej formie zajęć (4.3.3)",
     "MATCH (gt:GroupType {id: $group_type}) UNWIND ['test-g1', 'test-g2'] AS id "
     "CREATE (:Group {id: id, weekday: 1, number: 1, pnp: 'ALL', capacity: 10, "
     "start_time: localtime('08:00'), end_time: localtime('09:00')})-[:OF_TYPE]->(gt)", _CLEAN),
    ("druga instancja przedmiotu w tym samym cyklu (API, 4.3.2)",
     "MATCH (su:Subject {code: $subject}), (ac:AcademicCycle {id: $cycle}) "
     "CREATE (si:SubjectInstance)-[:INSTANCE_OF]->(su), (si)-[:OFFERED_IN]->(ac) "
     "CREATE (si)-[:HAS_TYPE]->(:GroupType {id: 'test-gt', g_type: 'W', weight: 1.0})",
     "MATCH (si:SubjectInstance)-[:HAS_TYPE]->(gt:GroupType {id: 'test-gt'}) DETACH DELETE si, gt"),
    ("wagi form zajęć niesumujące się do 1 (API, 4.3.2)",
     "MATCH (si:SubjectInstance)-[:INSTANCE_OF]->(:Subject {code: $subject}) WITH si LIMIT 1 "
     "CREATE (si)-[:HAS_TYPE]->(:GroupType {id: 'test-gt', g_type: 'P', weight: 0.9})", _CLEAN),
    ("Inactive bez etykiety User (API, 5.3.1)",
     "CREATE (:Person:Inactive {idx: 'test-s', name: 'T', surname: 'T', phone: 'test', "
     "deactivated_at: datetime()})", _CLEAN),
    ("student w dwóch turach jednych zapisów (API, 4.3.4)",
     "MATCH (st:Student {idx: $student}), (reg:Registration {id: $registration}) "
     "CREATE (reg)-[:HAS_TURN]->(:RegistrationTurn {id: 'test-t1', turn_number: 98, date: date(), "
     "start_time: localtime('08:00'), end_time: localtime('09:00')})<-[:ASSIGNED]-(st) "
     "CREATE (reg)-[:HAS_TURN]->(:RegistrationTurn {id: 'test-t2', turn_number: 99, date: date(), "
     "start_time: localtime('08:00'), end_time: localtime('09:00')})<-[:ASSIGNED]-(st)", _CLEAN),
]

_RUN = r'''
from neo4j.exceptions import Neo4jError

async def attempt(query, params):
    async with driver.session() as s:
        try:
            tx = await s.begin_transaction()
            await (await tx.run(query, **params)).consume()
            await tx.commit()
            return {"accepted": True}
        except Neo4jError as e:
            return {"accepted": False, "gql": getattr(e, "gql_status", None) or "",
                    "message": (getattr(e, "message", None) or str(e)).splitlines()[0][:160]}

async def main(args):
    p = (await q("""
        MATCH (g:Group)-[:IN_ROOM]->(r:Room) WITH g, r LIMIT 1
        MATCH (ac:AcademicCycle) WITH g, r, ac LIMIT 1
        MATCH (st:Student) WHERE NOT st:Teacher WITH g, r, ac, st ORDER BY st.idx LIMIT 1
        MATCH (u:User) WITH g, r, ac, st, u LIMIT 1
        MATCH (su:Subject)<-[:INSTANCE_OF]-(si:SubjectInstance)-[:OFFERED_IN]->(sc:AcademicCycle)
        WITH g, r, ac, st, u, su, sc LIMIT 1
        MATCH (gt:GroupType) WITH g, r, ac, st, u, su, sc, gt LIMIT 1
        MATCH (reg:Registration) WITH g, r, ac, st, u, su, sc, gt, reg LIMIT 1
        MATCH (fg:Group) WHERE NOT EXISTS { (st)-[:REGISTERED_IN]->(fg) } WITH * LIMIT 1
        RETURN g.id AS group, r.building AS building, r.room_num AS room_num, ac.year AS year, ac.season AS season,
               st.idx AS student, st.name AS name, st.surname AS surname, st.phone AS phone, u.email AS email,
               su.code AS subject, sc.id AS cycle, gt.id AS group_type, reg.id AS registration, fg.id AS free_group"""))[0]
    out = {"reject": [], "accept": []}
    for query in args["reject"]:
        out["reject"].append(await attempt(query, p))
        await q("MATCH (n) WHERE n.id STARTS WITH 'test-' OR n.idx STARTS WITH 'test-' DETACH DELETE n")
    for query, clean in args["accept"]:
        out["accept"].append(await attempt(query, p))
        await q(clean, **p)
    out["leftover"] = (await q("MATCH (n) WHERE n.id STARTS WITH 'test-' OR n.idx STARTS WITH 'test-' RETURN count(n) AS n"))[0]["n"]
    out["user"] = os.environ["NEO4J_USER"]
    return out
'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    out = in_app(_RUN, reject=[query for _, query in REJECT], accept=[[query, clean] for _, query, clean in ACCEPT])
    errors, rows_a, rows_b = [], [], []
    for (rule, _), res in zip(REJECT, out["reject"]):
        good = not res["accepted"]
        rows_a.append([rule, "przyjęto" if res["accepted"] else "odrzucono",
                       res.get("gql", ""), res.get("message", "").replace("`", "") if not res["accepted"] else "–", ok(good)])
        if not good:
            errors.append(f"baza przyjęła: {rule}")
    for (rule, _, _), res in zip(ACCEPT, out["accept"]):
        rows_b.append([rule, "przyjęto" if res["accepted"] else f"odrzucono ({res.get('gql', '')})"])
        if not res["accepted"]:
            # Nie błąd modelu, ale opis w pracy (4.3.7) byłby nieaktualny.
            errors.append(f"baza odrzuciła regułę opisaną jako niewymuszana: {rule}: {res.get('message')}")
    if out["leftover"]:
        errors.append(f"po teście zostało {out['leftover']} węzłów testowych")
    md = "\n\n".join([
        f"Konto bazy danych: `{out['user']}` (konto API).",
        "## A. Reguły wymuszane przez bazę",
        table(["Reguła", "Wynik", "Kod GQL", "Komunikat", "Zgodny"], rows_a),
        "## B. Reguły pilnowane przez API (baza przyjmuje dane)",
        table(["Reguła (gdzie egzekwowana)", "Wynik w bazie"], rows_b),
    ])
    finish(md, errors, args.out)


if __name__ == "__main__":
    main()
