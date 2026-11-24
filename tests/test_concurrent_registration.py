"""Test współbieżnych zapisów do grup (PUT /api/me/registered-groups/{group_id}).

Scenariusze:
  A. 10 studentów jednocześnie zapisuje się do grupy z 3 miejscami
     -> dokładnie 3 zapisy (204), 7 odmów (409 "Group is full").
  B. 5 studentów wysyła jednocześnie po dwa żądania zapisu do dwóch różnych grup
     tego samego typu -> każdy student kończy w dokładnie jednej grupie.
  D. Dwa jednoczesne żądania odebrania dwóch różnych ról osobie, która ma dokładnie
     dwie role (DELETE /api/admin/users/{idx}/roles/{role}) -> jedno się udaje (200),
     drugie dostaje 409 "Cannot remove last role"; osobie zostaje jedna rola.
  C. (kontrola) scenariusz A wykonany zapytaniem _REGISTER bez blokad zapisu
     (bez linii SET), bezpośrednio przez sterownik -> wynik tylko raportowany.

Dane testowe (rejestracja, tura trwająca teraz, grupy, osoba z dwiema rolami) tworzone są w bazie przed
testem i usuwane po nim; mają identyfikatory z prefiksem "test-". Tokeny studentów
są generowane kluczem JWT_SECRET w kontenerze app, więc studenci nie muszą mieć kont.
Wymaga uruchomionego stacka (`docker compose up`).

Uruchomienie:
    python tests/test_concurrent_registration.py [--out wynik.md]
"""

import argparse
import json
import ssl
import subprocess
import threading
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://localhost:8000/api"
_ctx = ssl.create_default_context(cafile=str(ROOT / "certificates" / "ca.pem"))

# Wykonywane w kontenerze app (sterownik Neo4j, konto API, JWT_SECRET).
_HELPER = r'''
import asyncio, json, os, sys, time, uuid
import jwt
from app.graph_backend.database import driver
from app.graph_backend.routers.student import _REGISTER

TAG = "test-"

async def setup():
    async with driver.session() as s:
        types = [r["id"] async for r in await s.run("""
            MATCH (gt:GroupType)
            WHERE NOT EXISTS { (:Student)-[:REGISTERED_IN]->(:Group)-[:OF_TYPE]->(gt) }
            RETURN gt.id AS id LIMIT 2""")]
        students = [r["idx"] async for r in await s.run(
            "MATCH (st:Student) RETURN st.idx AS idx ORDER BY st.idx LIMIT 15")]
        reg, turn = TAG + str(uuid.uuid4()), TAG + str(uuid.uuid4())
        groups = {
            "small": (TAG + str(uuid.uuid4()), types[0], 3),
            "a": (TAG + str(uuid.uuid4()), types[0], 50),
            "b": (TAG + str(uuid.uuid4()), types[0], 50),
            "ctrl": (TAG + str(uuid.uuid4()), types[1], 3),
        }
        await s.run("""
            CREATE (reg:Registration {id: $reg, name: 'TEST', reg_type: 'TEST'})
            CREATE (reg)-[:HAS_TURN]->(:RegistrationTurn {id: $turn, turn_number: 1, date: date({timezone: 'Europe/Warsaw'}),
                // +-20 minutes, clipped to the current day: near midnight the window would otherwise
                // wrap around and start after it ends.
                start_time: CASE WHEN localtime({timezone: 'Europe/Warsaw'}) < localtime('00:20')
                    THEN localtime('00:00') ELSE localtime({timezone: 'Europe/Warsaw'}) - duration('PT20M') END,
                end_time: CASE WHEN localtime({timezone: 'Europe/Warsaw'}) > localtime('23:39')
                    THEN localtime('23:59:59') ELSE localtime({timezone: 'Europe/Warsaw'}) + duration('PT20M') END})
            WITH reg
            UNWIND $groups AS gr
            MATCH (gt:GroupType {id: gr.type})
            CREATE (reg)-[:OPENS]->(g:Group {id: gr.id, weekday: 1, number: 99, pnp: 'ALL',
                capacity: gr.capacity, start_time: localtime('08:00'), end_time: localtime('09:00')})
            CREATE (g)-[:OF_TYPE]->(gt)""",
            reg=reg, turn=turn,
            groups=[{"id": g, "type": t, "capacity": c} for g, t, c in groups.values()])
        await s.run("""
            MATCH (rt:RegistrationTurn {id: $turn})
            UNWIND $students AS idx
            MATCH (st:Student {idx: idx})
            CREATE (st)-[:ASSIGNED]->(rt)""", turn=turn, students=students)
        person = TAG + str(uuid.uuid4())[:8]
        await s.run("""
            CREATE (:Person:Teacher:Student {idx: $idx, name: 'Test', surname: $idx, phone: '000',
                degree: 'mgr', working_since: date(), joined: datetime()})""", idx=person)
    secret = os.environ["JWT_SECRET"]
    tokens = {idx: jwt.encode({"sub": f"{idx}@test", "idx": idx, "roles": ["Student"],
                               "iat": time.time(), "exp": int(time.time()) + 600}, secret, algorithm="HS256")
              for idx in students}
    admin = jwt.encode({"sub": "admin@test", "idx": TAG + "admin", "roles": ["Admin"],
                        "iat": time.time(), "exp": int(time.time()) + 600}, secret, algorithm="HS256")
    return {"reg": reg, "turn": turn, "groups": {k: v[0] for k, v in groups.items()},
            "students": students, "tokens": tokens, "person": person, "admin": admin}

async def roles(idx):
    async with driver.session() as s:
        r = await (await s.run(
            "MATCH (p:Person {idx: $idx}) RETURN [l IN labels(p) WHERE l IN ['Admin','Teacher','Student']] AS r",
            idx=idx)).single()
        return r["r"]

async def count(group_id):
    async with driver.session() as s:
        r = await (await s.run(
            "MATCH (:Student)-[r:REGISTERED_IN]->(:Group {id: $g}) RETURN count(r) AS n", g=group_id)).single()
        return r["n"]

async def per_student(group_ids, students):
    async with driver.session() as s:
        rows = await s.run("""
            UNWIND $students AS idx
            MATCH (st:Student {idx: idx})
            RETURN idx, COUNT { (st)-[:REGISTERED_IN]->(g:Group) WHERE g.id IN $groups } AS n""",
            students=students, groups=group_ids)
        return {r["idx"]: r["n"] async for r in rows}

async def no_lock(group_id, students):
    query = _REGISTER.replace("SET st.idx = st.idx\n", "").replace("SET g.capacity = g.capacity\n", "")
    assert "SET st.idx" not in query and "SET g.capacity" not in query
    async def one(idx):
        async with driver.session() as s:
            r = await (await s.run(query, student_idx=idx, group_id=group_id)).single()
            return r["status"] if r else None
    statuses = await asyncio.gather(*(one(idx) for idx in students))
    return {"statuses": statuses, "count": await count(group_id)}

async def teardown(reg, turn, person):
    async with driver.session() as s:
        await s.run("MATCH (p:Person {idx: $idx}) DETACH DELETE p", idx=person)
        await s.run("""
            MATCH (reg:Registration {id: $reg})
            OPTIONAL MATCH (reg)-[:OPENS]->(g:Group)
            OPTIONAL MATCH (rt:RegistrationTurn {id: $turn})
            DETACH DELETE g, rt, reg""", reg=reg, turn=turn)

async def main():
    cmd, args = sys.argv[1], json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    try:
        out = await {"setup": setup, "count": count, "per_student": per_student,
                     "no_lock": no_lock, "teardown": teardown, "roles": roles}[cmd](**args)
        print(json.dumps(out))
    finally:
        await driver.close()

asyncio.run(main())
'''


def helper(cmd: str, **args):
    out = subprocess.run(
        ["docker", "compose", "exec", "-T", "app", "python", "-", cmd, json.dumps(args)],
        input=_HELPER, capture_output=True, text=True, cwd=ROOT,
    )
    if out.returncode:
        raise RuntimeError(f"helper {cmd}: {out.stderr.strip()[-500:]}")
    return json.loads(out.stdout)


def request(method: str, path: str, token: str) -> tuple[int, str]:
    req = urllib.request.Request(f"{API}{path}", method=method, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, context=_ctx) as resp:
            return resp.status, ""
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read() or b"{}").get("detail", "")


def put(group_id: str, token: str) -> tuple[int, str]:
    return request("PUT", f"/me/registered-groups/{group_id}", token)


def concurrently(calls: list[tuple], fn=put) -> list[tuple[int, str]]:
    """Fires all requests at once (threads released together by a barrier)."""
    barrier = threading.Barrier(len(calls))

    def run(call):
        barrier.wait()
        return fn(*call)

    with ThreadPoolExecutor(len(calls)) as pool:
        return list(pool.map(run, calls))


def scenario_a(data) -> dict:
    group = data["groups"]["small"]
    students = data["students"][5:15]
    results = concurrently([(group, data["tokens"][s]) for s in students])
    return {"codes": Counter(code for code, _ in results), "details": Counter(d for _, d in results if d),
            "count": helper("count", group_id=group)}


def scenario_b(data) -> dict:
    groups = [data["groups"]["a"], data["groups"]["b"]]
    students = data["students"][:5]
    results = concurrently([(g, data["tokens"][s]) for s in students for g in groups])
    return {"codes": Counter(code for code, _ in results), "details": Counter(d for _, d in results if d),
            "per_student": helper("per_student", group_ids=groups, students=students)}


def scenario_d(data) -> dict:
    person = data["person"]
    calls = [("DELETE", f"/admin/users/{person}/roles/{role}", data["admin"]) for role in ("Teacher", "Student")]
    results = concurrently(calls, fn=request)
    return {"codes": Counter(code for code, _ in results), "details": Counter(d for _, d in results if d),
            "roles": helper("roles", idx=person)}


def to_markdown(a: dict, b: dict, c: dict, d: dict) -> str:
    fmt = lambda counter: ", ".join(f"{k}: {v}" for k, v in sorted(counter.items()))
    ctrl = Counter(c["statuses"])
    return "\n".join([
        "| Scenariusz | Żądania | Odpowiedzi | Stan bazy | Oczekiwano |",
        "| --- | ---: | --- | --- | --- |",
        f"| A: 10 studentów, grupa z 3 miejscami | 10 | {fmt(a['codes'])} | {a['count']} zapisanych | 3 zapisanych |",
        f"| B: 5 studentów × 2 grupy tego samego typu | 10 | {fmt(b['codes'])} | "
        f"{fmt(Counter(b['per_student'].values()))} (grup na studenta: liczba studentów) | każdy w 1 grupie |",
        f"| D: odebranie obu ról osobie z dwiema rolami | 2 | {fmt(d['codes'])} | "
        f"pozostałe role: {', '.join(d['roles'])} | jedna rola |",
        f"| C (kontrola): jak A, zapytanie bez blokad | 10 | statusy: {fmt(ctrl)} | {c['count']} zapisanych | – |",
    ])


def check(a: dict, b: dict, d: dict) -> list[str]:
    errors = []
    if a["count"] != 3 or a["codes"] != Counter({204: 3, 409: 7}):
        errors.append(f"A: {dict(a['codes'])}, zapisanych {a['count']}")
    if set(b["per_student"].values()) != {1} or b["codes"] != Counter({204: 5, 409: 5}):
        errors.append(f"B: {dict(b['codes'])}, {b['per_student']}")
    if len(d["roles"]) != 1 or d["codes"] != Counter({200: 1, 409: 1}):
        errors.append(f"D: {dict(d['codes'])}, role {d['roles']}")
    return errors


def run_all() -> tuple[dict, dict, dict, dict]:
    data = helper("setup")
    try:
        a = scenario_a(data)
        b = scenario_b(data)
        d = scenario_d(data)
        c = helper("no_lock", group_id=data["groups"]["ctrl"], students=data["students"][5:15])
    finally:
        helper("teardown", reg=data["reg"], turn=data["turn"], person=data["person"])
    return a, b, c, d


def test_concurrent_registration() -> None:
    a, b, _, d = run_all()
    assert not check(a, b, d)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    a, b, c, d = run_all()
    md = to_markdown(a, b, c, d)
    print(md)
    print("\nKomunikaty 409 (A):", dict(a["details"]))
    print("Komunikaty 409 (B):", dict(b["details"]))
    print("Komunikaty 409 (D):", dict(d["details"]))
    if args.out:
        args.out.write_text(md + "\n")
    errors = check(a, b, d)
    print("\nWYNIK:", "OK" if not errors else "BŁĄD - " + "; ".join(errors))
    raise SystemExit(1 if errors else 0)
