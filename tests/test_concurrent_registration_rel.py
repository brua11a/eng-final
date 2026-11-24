"""Test współbieżnych zapisów do grup w backendzie relacyjnym (PUT /api/rel/me/registered-groups/{group_id}).

Odpowiednik tests/test_concurrent_registration.py dla PostgreSQL. Scenariusze:
  A. 10 studentów jednocześnie zapisuje się do grupy z 3 miejscami
     -> dokładnie 3 zapisy (204), 7 odmów (409 "Group is full").
  B. 5 studentów wysyła jednocześnie po dwa żądania zapisu do dwóch różnych grup
     tego samego typu -> każdy student kończy w dokładnie jednej grupie.
  C1. (kontrola) scenariusz A wykonany samym zapytaniem REGISTER, bez instrukcji blokujących.
  C2. (kontrola) scenariusz A wykonany jedną instrukcją, która najpierw blokuje grupę
      (FOR UPDATE), a potem w tej samej instrukcji liczy zapisanych - wzorzec, który
      w Cypher wystarcza (5.5.10).
  Kontrole wykonywane są bezpośrednio przez psycopg, każda w osobnym połączeniu
  i transakcji; wynik jest tylko raportowany.

Scenariusz D z testu grafowego (odebranie ról) nie ma odpowiednika: backend relacyjny
nie implementuje tego punktu końcowego.

Dane testowe (rejestracja, tura trwająca teraz, grupy) tworzone są przed testem i usuwane
po nim; mają identyfikatory z prefiksem "test-". Tokeny studentów są generowane kluczem
JWT_SECRET w kontenerze app. Wymaga uruchomionego stacka (`docker compose up`).

Uruchomienie:
    python tests/test_concurrent_registration_rel.py [--out wynik.md]
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
API = "https://localhost:8000/api/rel"
_ctx = ssl.create_default_context(cafile=str(ROOT / "certificates" / "ca.pem"))

# Wykonywane w kontenerze app (psycopg, konto API, JWT_SECRET).
_HELPER = r'''
import asyncio, json, os, sys, time, uuid
import jwt
import psycopg
from psycopg.rows import dict_row
from app.relation_backend.routers.student import REGISTER

TAG = "test-"

async def connect():
    return await psycopg.AsyncConnection.connect(
        os.environ["PG_CONNINFO"], password=os.environ["PG_PASSWORD"], row_factory=dict_row)

async def setup():
    async with await connect() as c:
        types = [r["id"] for r in await (await c.execute("""
            SELECT gt.id FROM group_type gt
            WHERE NOT EXISTS (SELECT 1 FROM registered_in ri JOIN class_group g ON g.id = ri.group_id
                              WHERE g.group_type_id = gt.id)
            ORDER BY gt.id LIMIT 2""")).fetchall()]
        students = [r["idx"] for r in await (await c.execute(
            "SELECT idx FROM student ORDER BY idx LIMIT 15")).fetchall()]
        ref = await (await c.execute("SELECT (SELECT id FROM academic_cycle LIMIT 1) AS cycle, "
                                     "(SELECT id FROM faculty LIMIT 1) AS faculty")).fetchone()
        reg, turn = TAG + str(uuid.uuid4()), TAG + str(uuid.uuid4())
        groups = {
            "small": (TAG + str(uuid.uuid4()), types[0], 3, 99),
            "a": (TAG + str(uuid.uuid4()), types[0], 50, 98),
            "b": (TAG + str(uuid.uuid4()), types[0], 50, 97),
            "ctrl1": (TAG + str(uuid.uuid4()), types[1], 3, 99),
            "ctrl2": (TAG + str(uuid.uuid4()), types[1], 3, 98),
        }
        await c.execute("INSERT INTO registration VALUES (%s, 'TEST', 'TEST', %s, %s)",
                        (reg, ref["cycle"], ref["faculty"]))
        # Turn in progress: wall-clock time in the university's zone, +-20 minutes.
        await c.execute("""
            INSERT INTO registration_turn (id, turn_number, date, start_time, end_time, registration_id)
            SELECT %s, 1, local::date, (local - interval '20 minutes')::time, (local + interval '20 minutes')::time, %s
            FROM (SELECT now() AT TIME ZONE 'Europe/Warsaw' AS local) t""", (turn, reg))
        for gid, gtype, capacity, number in groups.values():
            await c.execute("""
                INSERT INTO class_group (id, number, capacity, weekday, start_time, end_time, pnp, group_type_id)
                VALUES (%s, %s, %s, 1, '08:00', '09:00', 'ALL', %s)""", (gid, number, capacity, gtype))
            await c.execute("INSERT INTO opens VALUES (%s, %s)", (reg, gid))
        for idx in students:
            await c.execute("INSERT INTO assigned VALUES (%s, %s, %s)", (idx, turn, reg))
        await c.commit()
    secret = os.environ["JWT_SECRET"]
    tokens = {idx: jwt.encode({"sub": f"{idx}@test", "idx": idx, "roles": ["Student"],
                               "iat": time.time(), "exp": int(time.time()) + 600}, secret, algorithm="HS256")
              for idx in students}
    return {"reg": reg, "turn": turn, "groups": {k: v[0] for k, v in groups.items()},
            "students": students, "tokens": tokens}

async def count(group_id):
    async with await connect() as c:
        return (await (await c.execute(
            "SELECT count(*) AS n FROM registered_in WHERE group_id = %s", (group_id,))).fetchone())["n"]

async def per_student(group_ids, students):
    async with await connect() as c:
        rows = await (await c.execute("""
            SELECT s.idx, count(ri.group_id) AS n
            FROM unnest(%s::text[]) AS s (idx)
            LEFT JOIN registered_in ri ON ri.student_idx = s.idx AND ri.group_id = ANY(%s)
            GROUP BY s.idx""", (students, group_ids))).fetchall()
        return {r["idx"]: r["n"] for r in rows}

# C2: lock and check in one statement, as in the Cypher query.
LOCK_AND_CHECK = """
WITH locked AS (
  SELECT id, capacity FROM class_group WHERE id = %(group_id)s FOR UPDATE
)
INSERT INTO registered_in (student_idx, group_id)
SELECT %(student_idx)s, id FROM locked
WHERE (SELECT count(*) FROM registered_in WHERE group_id = %(group_id)s) < locked.capacity
RETURNING 'ok' AS status
"""

async def control(variant, group_id, students):
    async with await connect() as c:
        g = await (await c.execute(
            "SELECT capacity, group_type_id FROM class_group WHERE id = %s", (group_id,))).fetchone()
    async def one(idx):
        async with await connect() as c:
            params = {"student_idx": idx, "group_id": group_id, **g}
            row = await (await c.execute(REGISTER if variant == "c1" else LOCK_AND_CHECK, params)).fetchone()
            # The transaction stays open a moment, so that all requests surely overlap.
            await asyncio.sleep(0.1)
            await c.commit()
            return row["status"] if row else "full"
    statuses = await asyncio.gather(*(one(idx) for idx in students))
    return {"statuses": statuses, "count": await count(group_id)}

async def teardown(reg, turn, groups):
    async with await connect() as c:
        await c.execute("DELETE FROM registered_in WHERE group_id = ANY(%s)", (groups,))
        await c.execute("DELETE FROM assigned WHERE turn_id = %s", (turn,))
        await c.execute("DELETE FROM opens WHERE registration_id = %s", (reg,))
        await c.execute("DELETE FROM class_group WHERE id = ANY(%s)", (groups,))
        await c.execute("DELETE FROM registration_turn WHERE id = %s", (turn,))
        await c.execute("DELETE FROM registration WHERE id = %s", (reg,))
        await c.commit()

async def main():
    cmd, args = sys.argv[1], json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    out = await {"setup": setup, "count": count, "per_student": per_student,
                 "control": control, "teardown": teardown}[cmd](**args)
    print(json.dumps(out))

asyncio.run(main())
'''


def helper(cmd: str, **args):
    out = subprocess.run(
        ["docker", "compose", "exec", "-T", "app", "python", "-", cmd, json.dumps(args)],
        input=_HELPER, capture_output=True, text=True, cwd=ROOT,
    )
    if out.returncode:
        raise RuntimeError(f"helper {cmd}: {out.stderr.strip()[-800:]}")
    return json.loads(out.stdout)


def put(group_id: str, token: str) -> tuple[int, str]:
    req = urllib.request.Request(f"{API}/me/registered-groups/{group_id}", method="PUT",
                                 headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, context=_ctx) as resp:
            return resp.status, ""
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read() or b"{}").get("detail", "")


def concurrently(calls: list[tuple]) -> list[tuple[int, str]]:
    """Fires all requests at once (threads released together by a barrier)."""
    barrier = threading.Barrier(len(calls))

    def run(call):
        barrier.wait()
        return put(*call)

    with ThreadPoolExecutor(len(calls)) as pool:
        return list(pool.map(run, calls))


def scenario_a(data) -> dict:
    group = data["groups"]["small"]
    results = concurrently([(group, data["tokens"][s]) for s in data["students"][5:15]])
    return {"codes": Counter(code for code, _ in results), "details": Counter(d for _, d in results if d),
            "count": helper("count", group_id=group)}


def scenario_b(data) -> dict:
    groups = [data["groups"]["a"], data["groups"]["b"]]
    students = data["students"][:5]
    results = concurrently([(g, data["tokens"][s]) for s in students for g in groups])
    return {"codes": Counter(code for code, _ in results), "details": Counter(d for _, d in results if d),
            "per_student": helper("per_student", group_ids=groups, students=students)}


def to_markdown(a: dict, b: dict, c1: dict, c2: dict) -> str:
    fmt = lambda counter: ", ".join(f"{k}: {v}" for k, v in sorted(counter.items()))
    return "\n".join([
        "| Scenariusz | Żądania | Odpowiedzi | Stan bazy | Oczekiwano |",
        "| --- | ---: | --- | --- | --- |",
        f"| A: 10 studentów, grupa z 3 miejscami | 10 | {fmt(a['codes'])} | {a['count']} zapisanych | 3 zapisanych |",
        f"| B: 5 studentów × 2 grupy tego samego typu | 10 | {fmt(b['codes'])} | "
        f"{fmt(Counter(b['per_student'].values()))} (grup na studenta: liczba studentów) | każdy w 1 grupie |",
        f"| C1 (kontrola): jak A, bez blokad | 10 | statusy: {fmt(Counter(c1['statuses']))} | {c1['count']} zapisanych | – |",
        f"| C2 (kontrola): jak A, blokada i sprawdzenie w jednej instrukcji | 10 | "
        f"statusy: {fmt(Counter(c2['statuses']))} | {c2['count']} zapisanych | – |",
    ])


def check(a: dict, b: dict) -> list[str]:
    errors = []
    if a["count"] != 3 or a["codes"] != Counter({204: 3, 409: 7}):
        errors.append(f"A: {dict(a['codes'])}, zapisanych {a['count']}")
    if set(b["per_student"].values()) != {1} or b["codes"] != Counter({204: 5, 409: 5}):
        errors.append(f"B: {dict(b['codes'])}, {b['per_student']}")
    return errors


def run_all() -> tuple[dict, dict, dict, dict]:
    data = helper("setup")
    try:
        a = scenario_a(data)
        b = scenario_b(data)
        controls = data["students"][5:15]
        c1 = helper("control", variant="c1", group_id=data["groups"]["ctrl1"], students=controls)
        c2 = helper("control", variant="c2", group_id=data["groups"]["ctrl2"], students=controls)
    finally:
        helper("teardown", reg=data["reg"], turn=data["turn"], groups=list(data["groups"].values()))
    return a, b, c1, c2


def test_concurrent_registration_rel() -> None:
    a, b, _, _ = run_all()
    assert not check(a, b)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    a, b, c1, c2 = run_all()
    md = to_markdown(a, b, c1, c2)
    print(md)
    print("\nKomunikaty 409 (A):", dict(a["details"]))
    print("Komunikaty 409 (B):", dict(b["details"]))
    if args.out:
        args.out.write_text(md + "\n")
    errors = check(a, b)
    print("\nWYNIK:", "OK" if not errors else "BŁĄD - " + "; ".join(errors))
    raise SystemExit(1 if errors else 0)
