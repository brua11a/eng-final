"""Okno czasowe tury zapisów (3.2, 4.3.4, 5.5.10).

Student może zapisać się do grupy i wypisać z niej tylko w czasie trwania swojej tury i tylko w
zapisach otwierających tę grupę.

Część A (API). Administrator zakłada przez API dwoje zapisów (POST /admin/registrations) z turami:
wczorajszą, dzisiejszą (trwającą cały dzień) i jutrzejszą, i przydziela do nich studentów. Godziny
tur są wysyłane z przesunięciem +01:00, tak jak robiła to pierwsza wersja klienta - API powinno je
zapisać jako czas lokalny (LOCAL TIME), bez przesunięcia. Następnie studenci wywołują
PUT i DELETE /me/registered-groups/{group_id}.

Część B (strefa czasowa). Godziny tur są czasem lokalnym uczelni, łączonym z datą tury w strefie
Europe/Warsaw (4.3.3). Sprawdzane jest to samo wyrażenie co w kwerendzie _REGISTER: tura o 8:00 ma
zaczynać się o 8:00 czasu polskiego zarówno zimą, jak i latem, również w dniach zmiany czasu.
Dla porównania pokazano dawny zapis godziny ze stałym przesunięciem (13:15+01:00, 5.3.1).

Dane tymczasowe (zapisy, tury, grupy) są usuwane po teście.

Uruchomienie:
    python tests/test_registration_turn.py [--out wynik.md]
"""

import argparse
from datetime import date, timedelta
from pathlib import Path

from common import detail, finish, in_app, ok, request, table

_FIXTURE = r'''
from app.graph_backend.routers.student import _REGISTER, _DEREGISTER

EXPR = "datetime({date: rt.date, time: rt.start_time, timezone: 'Europe/Warsaw'})"

async def main(args):
    if args["cmd"] == "teardown":
        await q("""MATCH (reg:Registration) WHERE reg.id IN $regs
                   OPTIONAL MATCH (reg)-[:HAS_TURN]->(rt) DETACH DELETE rt, reg""", regs=args["regs"])
        await q("MATCH (g:Group) WHERE g.id STARTS WITH $tag DETACH DELETE g", tag=TAG)
        return {}
    if args["cmd"] == "turns":
        return await q("""MATCH (reg:Registration)-[:HAS_TURN]->(rt) WHERE reg.id IN $regs
                          RETURN reg.id AS reg, rt.id AS id, rt.turn_number AS turn_number,
                                 rt.date AS date, rt.start_time AS start, rt.end_time AS end,
                                 valueType(rt.start_time) AS type ORDER BY rt.date""", regs=args["regs"])
    if args["cmd"] == "tz":
        rows = []
        for d in args["dates"]:
            r = (await q("""
                WITH {date: date($d), start_time: localtime('08:00')} AS rt
                RETURN toString(datetime({date: rt.date, time: rt.start_time, timezone: 'Europe/Warsaw'})) AS local_turn,
                       toString(datetime({datetime: datetime({date: date($d), time: time('08:00+01:00')}),
                                          timezone: 'Europe/Warsaw'})) AS fixed_offset""",
                d=d))[0]
            rows.append({"date": d, **r})
        return {"rows": rows, "in_register": EXPR in _REGISTER and EXPR in _DEREGISTER}
    # setup: dwie grupy jednej formy zajęć bez zapisanych studentów, studenci, wydział, cykl, token administratora
    gt = (await q("""MATCH (gt:GroupType) WHERE NOT EXISTS { (:Student)-[:REGISTERED_IN]->(:Group)-[:OF_TYPE]->(gt) }
                     RETURN gt.id AS id LIMIT 1"""))[0]["id"]
    groups = [new_id(), new_id()]
    await q("""UNWIND $ids AS id MATCH (gt:GroupType {id: $gt})
               CREATE (g:Group {id: id, weekday: 1, number: 99, pnp: 'ALL', capacity: 10,
                                start_time: localtime('08:00'), end_time: localtime('09:00')})-[:OF_TYPE]->(gt)""",
            ids=groups, gt=gt)
    students = [r["idx"] for r in await q("MATCH (st:Student) RETURN st.idx AS idx ORDER BY st.idx LIMIT 4")]
    ref = (await q("MATCH (fa:Faculty), (ac:AcademicCycle) RETURN fa.id AS faculty, ac.id AS cycle LIMIT 1"))[0]
    admin = (await q("MATCH (a:Admin) RETURN a.idx AS idx LIMIT 1"))[0]["idx"]
    return {"groups": groups, "students": students, **ref, "admin": token(admin, ["Admin"]),
            "tokens": {s: token(s, ["Student"]) for s in students}}
'''


def turn(number: int, day: date, start: str, end: str) -> dict:
    return {"turn_number": number, "date": day.isoformat(), "start": start + "+01:00", "end": end + "+01:00"}


def setup(f: dict, regs: list) -> None:
    """Zakłada zapisy przez API; identyfikatory dopisuje do `regs` od razu, by zawsze je posprzątać."""
    today = date.today()
    adm = f["admin"]
    turns = {}
    for name, group, specs in (
        ("TEST główne", f["groups"][0], {"past": turn(1, today - timedelta(days=1), "08:00:00", "20:00:00"),
                                          "now": turn(2, today, "00:00:00", "23:59:59"),
                                          "future": turn(3, today + timedelta(days=1), "08:00:00", "20:00:00")}),
        ("TEST inne", f["groups"][1], {"other": turn(1, today, "00:00:00", "23:59:59")}),
    ):
        code, body = request("POST", "/admin/registrations", adm, {
            "name": name, "cycle_id": f["cycle"], "faculty_id": f["faculty"], "reg_type": "zapisowa",
            "turns": list(specs.values()), "group_ids": [group]})
        assert code == 201, (code, body)
        regs.append(body["id"])
        stored = in_app(_FIXTURE, cmd="turns", regs=[body["id"]])
        by_number = {t["turn_number"]: t["id"] for t in stored}
        turns.update({key: by_number[spec["turn_number"]] for key, spec in specs.items()})
    s_now, s_past, s_future, s_other = f["students"]
    for key, student in (("now", s_now), ("past", s_past), ("future", s_future), ("other", s_other)):
        code, body = request("POST", "/admin/registrations/turns/students", adm,
                             {"turn_id": turns[key], "student_idxs": [student]})
        assert code == 200, (code, body)
    # Student z zakończoną turą zapisany wcześniej przez dziekanat - do próby wypisu po turze.
    code, body = request("POST", "/admin/groups/students", adm, {"student_idx": s_past, "group_id": f["groups"][0]})
    assert code == 201, (code, body)


def part_a(f: dict) -> tuple[list[list], list[str]]:
    g, g_other = f["groups"]
    s_now, s_past, s_future, _ = f["students"]
    tok = f["tokens"]
    cases = [
        ("tura trwa: zapis", s_now, "PUT", g, 204),
        ("tura trwa: ponowny zapis do tej samej grupy (PUT idempotentny)", s_now, "PUT", g, 204),
        ("tura trwa: wypis", s_now, "DELETE", g, 204),
        ("tura trwa: wypis z grupy, do której nie jest zapisany", s_now, "DELETE", g, 404),
        ("tura trwa: zapis do grupy z innych zapisów (bez przydziału do tury)", s_now, "PUT", g_other, 403),
        ("tura zakończona: zapis", s_past, "PUT", g, 403),
        ("tura zakończona: wypis (zapisany wcześniej przez dziekanat)", s_past, "DELETE", g, 403),
        ("tura jutro: zapis", s_future, "PUT", g, 403),
    ]
    rows, errors = [], []
    for name, student, method, group, expected in cases:
        code, body = request(method, f"/me/registered-groups/{group}", tok[student])
        rows.append([name, f"`{method}`", expected, code, detail(body) or "–", ok(code == expected)])
        if code != expected:
            errors.append(f"{name}: {code} {detail(body)} (oczekiwano {expected})")
    return rows, errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    f = in_app(_FIXTURE, cmd="setup")
    regs = []
    try:
        setup(f, regs)
        stored = in_app(_FIXTURE, cmd="turns", regs=regs)
        rows_a, errors = part_a(f)
    finally:
        in_app(_FIXTURE, cmd="teardown", regs=regs)

    stored_rows = [[t["date"], t["start"], t["end"], t["type"]] for t in stored]
    for t in stored:
        if not t["type"].startswith("LOCAL TIME"):
            errors.append(f"tura {t['date']}: typ {t['type']} zamiast LOCAL TIME")
    if not any(t["start"].startswith("08:00") for t in stored):
        errors.append("godzina 08:00+01:00 nie została zapisana jako 08:00")

    # Dni: zima, latem, dni zmiany czasu w 2026 r. (29 marca i 25 października).
    tz = in_app(_FIXTURE, cmd="tz", dates=["2026-01-15", "2026-03-28", "2026-03-29", "2026-07-01",
                                             "2026-10-24", "2026-10-25"])
    tz_rows = []
    for r in tz["rows"]:
        good = r["local_turn"][11:16] == "08:00"
        tz_rows.append([r["date"], r["local_turn"], r["fixed_offset"], ok(good)])
        if not good:
            errors.append(f"{r['date']}: tura o 8:00 zaczyna się {r['local_turn']}")
    if not tz["in_register"]:
        errors.append("kwerendy _REGISTER/_DEREGISTER nie zawierają sprawdzanego wyrażenia")

    md = "\n\n".join([
        "## A. Zapis i wypis względem tury",
        table(["Przypadek", "Metoda", "Oczekiwano", "Kod", "Komunikat", "Zgodny"], rows_a),
        "Tury zapisane w bazie (wysłane jako godzina z przesunięciem +01:00):",
        table(["Data", "Początek", "Koniec", "Typ"], stored_rows),
        "## B. Początek tury o 8:00 w strefie Europe/Warsaw",
        table(["Data", "Czas lokalny + strefa (obecnie)", "08:00+01:00 w czasie polskim (dawniej)", "8:00 czasu polskiego"],
              tz_rows),
        f"Wyrażenie występuje w kwerendach `_REGISTER` i `_DEREGISTER`: {ok(tz['in_register'])}.",
    ])
    finish(md, errors, args.out)


if __name__ == "__main__":
    main()
