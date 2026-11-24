"""Średnia ocen studenta (3.2): testy jednostkowe funkcji `average_grade()` (5.5.5).

Reguły z wymagań:
  - ocena z przedmiotu to średnia ocen z form zajęć ważona ich wagami,
  - ocena niższa niż 3.0 z którejkolwiek formy zajęć oznacza 2.0 z przedmiotu,
  - średnia ze studiów to średnia ocen z przedmiotów ważona punktami ECTS,
  - liczy się ostatnie w pełni ocenione podejście do przedmiotu,
  - przedmiot bez kompletu ocen lub bez punktów ECTS nie wchodzi do średniej.

Funkcja jest wywoływana w kontenerze app (tam są zależności aplikacji), z wierszami w kształcie
zwracanym przez zapytanie _STUDENT_GRADES. Na końcu administrator wystawia przez API brakującą
ocenę studentowi z danych początkowych, a średnia z GET /students/{idx} jest porównywana z wynikiem
funkcji dla tych samych danych; ocena jest potem usuwana.

Uruchomienie:
    python tests/test_average_grade.py [--out wynik.md]
"""

import argparse
from pathlib import Path

from common import finish, in_app, ok, request, table


def row(subject, ects, cycle, type_, weight, grade):
    year, season = cycle.split()
    return {"subject": subject, "ects": ects, "year": year, "season": season,
            "type": type_, "weight": weight, "grade": grade}


# (opis, wiersze, oczekiwana średnia)
CASES = [
    ("jedna forma zajęć", [row("P1", 5, "2025/26 Z", "W", 1.0, 4.0)], 4.0),
    ("średnia ważona form zajęć: 0,7·5.0 + 0,3·4.0",
     [row("P1", 5, "2025/26 Z", "W", 0.7, 5.0), row("P1", 5, "2025/26 Z", "L", 0.3, 4.0)], 4.7),
    ("ocena negatywna z jednej formy: 0,7·5.0 + 0,3·2.0 daje 2.0, nie 4.1",
     [row("P1", 5, "2025/26 Z", "W", 0.7, 5.0), row("P1", 5, "2025/26 Z", "L", 0.3, 2.0)], 2.0),
    ("średnia ważona ECTS: (5·4.0 + 2·5.0) / 7",
     [row("P1", 5, "2025/26 Z", "W", 1.0, 4.0), row("P2", 2, "2025/26 Z", "W", 1.0, 5.0)], 4.286),
    ("poprawa przedmiotu: liczy się późniejsze podejście",
     [row("P1", 5, "2024/25 L", "W", 1.0, 2.0), row("P1", 5, "2025/26 Z", "W", 1.0, 4.5)], 4.5),
    ("kolejność cykli: semestr letni po zimowym tego samego roku",
     [row("P1", 5, "2025/26 L", "W", 1.0, 3.0), row("P1", 5, "2025/26 Z", "W", 1.0, 5.0)], 3.0),
    ("niepełne podejście (brak oceny z laboratorium) jest pomijane",
     [row("P1", 5, "2024/25 Z", "W", 1.0, 3.5),
      row("P1", 5, "2025/26 Z", "W", 0.5, 5.0), row("P1", 5, "2025/26 Z", "L", 0.5, None)], 3.5),
    ("brak żadnej pełnej oceny", [row("P1", 5, "2025/26 Z", "W", 1.0, None)], None),
    ("przedmiot bez punktów ECTS nie wchodzi do średniej",
     [row("P1", 5, "2025/26 Z", "W", 1.0, 3.0), row("P2", None, "2025/26 Z", "W", 1.0, 5.0)], 3.0),
    ("dwie grupy tej samej formy w jednym podejściu: średnia z nich",
     [row("P1", 5, "2025/26 Z", "L", 1.0, 3.0), row("P1", 5, "2025/26 Z", "L", 1.0, 5.0)], 4.0),
    ("wagi niesumujące się do 1 są normalizowane: (2·5.0 + 2·3.0) / 4",
     [row("P1", 5, "2025/26 Z", "W", 2.0, 5.0), row("P1", 5, "2025/26 Z", "L", 2.0, 3.0)], 4.0),
]

_RUN = r'''
from app.graph_backend.grades import average_grade
from app.graph_backend.routers.teacher import _STUDENT_GRADES

async def main(args):
    if args["cmd"] == "restore":
        await q("MATCH (:Student {idx: $idx})-[r:REGISTERED_IN]->(:Group {id: $g}) REMOVE r.grade",
                idx=args["idx"], g=args["group"])
        return {}
    results = [average_grade(rows) for rows in args["cases"]]
    # Ocena brakująca do kompletu w jakimś przedmiocie studenta z danych początkowych: po jej
    # wystawieniu przez API średnia z GET /students/{idx} musi się zgadzać z funkcją.
    pick = (await q("""
        MATCH (st:Student)-[r:REGISTERED_IN]->(g:Group)-[:OF_TYPE]->(gt:GroupType)<-[:HAS_TYPE]-(si)
        WHERE r.grade IS NULL
          AND all(t IN COLLECT { MATCH (si)-[:HAS_TYPE]->(o:GroupType) WHERE o <> gt RETURN o } WHERE
                  EXISTS { (st)-[x:REGISTERED_IN]->(:Group)-[:OF_TYPE]->(t) WHERE x.grade IS NOT NULL })
          AND COUNT { (si)-[:HAS_TYPE]->() } > 1
        RETURN st.idx AS idx, g.id AS group, gt.id AS type LIMIT 1"""))[0]
    rows = await q(_STUDENT_GRADES, student_idx=pick["idx"])
    rows = [{**r, "grade": args["grade"]} if r["type"] == pick["type"] else r for r in rows]
    admin = (await q("MATCH (a:Admin) RETURN a.idx AS idx LIMIT 1"))[0]["idx"]
    return {"results": results, **pick, "expected": average_grade(rows), "token": token(admin, ["Admin"])}
'''

GRADE = 3.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    out = in_app(_RUN, cmd="run", cases=[rows for _, rows, _ in CASES], grade=GRADE)
    rows, errors = [], []
    for (name, _, expected), got in zip(CASES, out["results"]):
        good = got == expected
        rows.append([name, expected, got, ok(good)])
        if not good:
            errors.append(f"{name}: {got} zamiast {expected}")
    idx, group = out["idx"], out["group"]
    try:
        _, before = request("GET", f"/students/{idx}", out["token"])
        put = request("PUT", f"/groups/{group}/students/{idx}/grade", out["token"], {"grade": GRADE})[0]
        code, body = request("GET", f"/students/{idx}", out["token"])
    finally:
        in_app(_RUN, cmd="restore", idx=idx, group=group)
    api_avg = body.get("avg_grade") if code == 200 else None
    api_ok = put == 200 and api_avg == out["expected"]
    if not api_ok:
        errors.append(f"API: PUT {put}, GET /students/{idx} -> {code}, avg_grade {api_avg}, oczekiwano {out['expected']}")
    md = "\n\n".join([
        table(["Przypadek", "Oczekiwano", "Wynik", "Zgodny"], rows),
        f"Test przez API: student {idx}, średnia przed wystawieniem oceny {before.get('avg_grade')}; "
        f"po `PUT .../grade` z oceną {GRADE} (kod {put}) `GET /students/{idx}` zwraca {api_avg}, "
        f"funkcja dla tych samych danych {out['expected']} – zgodne: {ok(api_ok)}. Ocena została potem usunięta.",
    ])
    finish(md, errors, args.out)


if __name__ == "__main__":
    main()
