"""Opinie o zajęciach i prowadzących (3.2, 3.4, 3.5, 4.3.5, 5.5.9, 5.5.10).

Część A - reguły wystawiania opinii (POST /api/opinions):
  ocena spoza skali i za długa treść (422), student niezapisany do grupy (403), prowadzący, który nie
  prowadzi grupy (403), poprawna opinia (201), ponowna opinia o tej samej grupie i prowadzącym (409),
  opinia o drugim prowadzącym tej samej grupy (201).
Część B - współbieżność: ten sam student wysyła jednocześnie 10 identycznych opinii; w bazie może
  powstać dokładnie jedna (blokada studenta przed ponownym sprawdzeniem duplikatu, 5.5.10).
Część C - pseudonimizacja: GET /api/opinions nie zwraca danych autora, a moment wystawienia jest
  ograniczony do samej daty (4.5.1).

Dane tymczasowe: grupa "test-..." z dwoma prowadzącymi i trzema zapisanymi studentami z danych
początkowych; po teście grupa i opinie o niej są usuwane.

Uruchomienie:
    python tests/test_opinions.py [--out wynik.md]
"""

import argparse
import json
import re
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from common import detail, finish, in_app, ok, request, table

_FIXTURE = r'''
async def main(args):
    if args["cmd"] == "teardown":
        await q("""MATCH (g:Group {id: $g}) OPTIONAL MATCH (o:Opinion)-[:ABOUT]->(g) DETACH DELETE o, g""", g=args["group"])
        return {}
    if args["cmd"] == "count":
        return (await q("""MATCH (:Student {idx: $st})-[:WRITES]->(o:Opinion)-[:ABOUT]->(:Group {id: $g})
                           RETURN count(o) AS n""", st=args["student"], g=args["group"]))[0]
    gt = (await q("MATCH (:SubjectInstance)-[:HAS_TYPE]->(gt:GroupType) RETURN gt.id AS id LIMIT 1"))[0]["id"]
    teachers = [r["idx"] for r in await q("MATCH (t:Teacher) WHERE NOT t:Student RETURN t.idx AS idx ORDER BY t.idx LIMIT 3")]
    students = [r["idx"] for r in await q("MATCH (s:Student) WHERE NOT s:Teacher RETURN s.idx AS idx ORDER BY s.idx LIMIT 4")]
    g = new_id()
    await q("""MATCH (gt:GroupType {id: $gt})
               CREATE (g:Group {id: $g, weekday: 1, number: 99, pnp: 'ALL', capacity: 10,
                                start_time: localtime('08:00'), end_time: localtime('09:00')})-[:OF_TYPE]->(gt)
               WITH g
               UNWIND $teachers AS t MATCH (te:Teacher {idx: t}) CREATE (te)-[:TEACHES]->(g)
               WITH DISTINCT g
               UNWIND $students AS s MATCH (st:Student {idx: s})
               CREATE (st)-[:REGISTERED_IN {registered_at: datetime()}]->(g)""",
            gt=gt, g=g, teachers=teachers[:2], students=students[:3])
    return {"group": g, "teachers": teachers, "students": students,
            "tokens": {s: token(s, ["Student"]) for s in students}, "teacher_token": token(teachers[0], ["Teacher"])}
'''


def post(token: str, body: dict) -> tuple[int, object]:
    return request("POST", "/opinions", token, body)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    f = in_app(_FIXTURE, cmd="setup")
    g, (t1, t2, t_other), (s1, s2, s3, s_out) = f["group"], f["teachers"], f["students"]
    tok = f["tokens"]
    errors = []
    try:
        cases = [
            ("ocena spoza skali (7.0)", s1, {"group_id": g, "teacher_idx": t1, "grade": 7.0}, 422),
            ("ocena spoza skali (4.2)", s1, {"group_id": g, "teacher_idx": t1, "grade": 4.2}, 422),
            ("treść dłuższa niż 1000 znaków", s1, {"group_id": g, "teacher_idx": t1, "grade": 4.0, "content": "x" * 1001}, 422),
            ("student niezapisany do grupy", s_out, {"group_id": g, "teacher_idx": t1, "grade": 4.0}, 403),
            ("prowadzący, który nie prowadzi grupy", s1, {"group_id": g, "teacher_idx": t_other, "grade": 4.0}, 403),
            ("poprawna opinia", s1, {"group_id": g, "teacher_idx": t1, "grade": 4.5, "content": "Dobre zajęcia"}, 201),
            ("ta sama grupa i prowadzący drugi raz", s1, {"group_id": g, "teacher_idx": t1, "grade": 3.0}, 409),
            ("drugi prowadzący tej samej grupy", s1, {"group_id": g, "teacher_idx": t2, "grade": 5.0}, 201),
            ("inny student, ta sama grupa i prowadzący", s3, {"group_id": g, "teacher_idx": t1, "grade": 3.5}, 201),
        ]
        rows_a = []
        for name, student, body, expected in cases:
            code, res = post(tok[student], body)
            rows_a.append([name, expected, f"{code} {detail(res)}".strip(), ok(code == expected)])
            if code != expected:
                errors.append(f"{name}: {code} {detail(res)} (oczekiwano {expected})")

        # B: 10 identycznych opinii naraz
        n = 10
        barrier = threading.Barrier(n)
        body = {"group_id": g, "teacher_idx": t1, "grade": 4.0}

        def fire(_):
            barrier.wait()
            return post(tok[s2], body)[0]

        with ThreadPoolExecutor(n) as pool:
            codes = Counter(pool.map(fire, range(n)))
        stored = in_app(_FIXTURE, cmd="count", student=s2, group=g)["n"]
        b_ok = codes == Counter({201: 1, 409: n - 1}) and stored == 1
        if not b_ok:
            errors.append(f"współbieżność: {dict(codes)}, w bazie {stored}")

        # C: pseudonimizacja
        code, res = request("GET", f"/opinions?group_id={g}", f["teacher_token"])
        opinions = res.get("opinions", []) if code == 200 else []
        text = json.dumps(opinions)
        author_leak = [s for s in (s1, s2, s3) if s in text]
        fields = sorted({k for o in opinions for k in o})
        dates = {o["submit"] for o in opinions}
        date_only = all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) for d in dates)
        rows_c = [
            ["liczba opinii o grupie", 4, len(opinions), ok(len(opinions) == 4)],
            ["identyfikatory autorów w odpowiedzi", "brak", ", ".join(author_leak) or "brak", ok(not author_leak)],
            ["moment wystawienia", "sama data", ", ".join(sorted(dates)), ok(date_only)],
        ]
        if len(opinions) != 4 or author_leak or not date_only:
            errors.append(f"odczyt opinii: {len(opinions)} opinii, autorzy {author_leak}, daty {dates}")
    finally:
        in_app(_FIXTURE, cmd="teardown", group=g)

    md = "\n\n".join([
        "## A. Reguły wystawiania opinii",
        table(["Przypadek", "Oczekiwano", "Odpowiedź", "Zgodny"], rows_a),
        "## B. Jednoczesne opinie tego samego studenta",
        table(["Żądania", "Odpowiedzi", "Opinii w bazie", "Zgodny"],
              [[n, ", ".join(f"{k}: {v}" for k, v in sorted(codes.items())), stored, ok(b_ok)]]),
        "## C. Odczyt opinii (`GET /opinions?group_id=...`, jako prowadzący)",
        table(["Sprawdzenie", "Oczekiwano", "Wynik", "Zgodny"], rows_c),
        "Pola opinii w odpowiedzi: " + ", ".join(f"`{x}`" for x in fields) + ".",
    ])
    finish(md, errors, args.out)


if __name__ == "__main__":
    main()
