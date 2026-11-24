"""Pomiar porównywanych punktów końcowych wewnątrz kontenera app (część wykonywana przez bench/run.py).

Skrypt jest przekazywany na standardowe wejście interpretera w kontenerze app (ma on sterowniki
obu baz, kod API i JWT_SECRET):
    docker compose exec -T app python - '{"runs": 50, ...}' < bench/measure.py

Dla każdego punktu końcowego i obu backendów:
 1. Nagrywa zapytania, które wykonuje punkt końcowy: jedno wywołanie aplikacji FastAPI w tym samym
    procesie z podmienionymi funkcjami run() (graph_backend/query.py, relation_backend/query.py).
    Dzięki temu w warstwach "surowych" wykonywane są dokładnie te same zapytania z tymi samymi
    parametrami co w API.
 2. Mierzy czasy w warstwach:
      engine  - czas wykonania po stronie silnika: suma czasów operatorów z PROFILE (Neo4j)
                lub "Execution Time" z EXPLAIN (ANALYZE, TIMING OFF) (PostgreSQL),
      driver  - te same zapytania wysłane sterownikiem tak jak robi to API (sesja Neo4j z transakcjami
                automatycznymi, połączenie z puli PostgreSQL z jedną transakcją na żądanie),
                razem z pobraniem wszystkich wierszy,
      asgi    - wywołanie aplikacji FastAPI w procesie (bez sieci i TLS): uwierzytelnianie,
                autoryzacja, walidacja, zapytania i serializacja odpowiedzi.
    Warstwy HTTP (bezpośrednio do API i przez nginx) mierzy bench/run.py z hosta.
 3. Zbiera diagnostykę zapytań: PROFILE (Neo4j) i EXPLAIN (ANALYZE, BUFFERS, MEMORY, SERIALIZE)
    (PostgreSQL) - liczba wierszy, db hits / bloki bufora, trafienia pamięci podręcznej,
    pamięć, czas planowania, oszacowania liczby wierszy, typy operatorów planu.

Zapytania zapisujące (wystawienie oceny) ustawiają ocenę równą bieżącej, więc dane się nie zmieniają.
Wynik: JSON na standardowe wyjście.
"""

import asyncio
import json
import os
import re
import sys
import time
from contextvars import ContextVar

import jwt
import psycopg
from psycopg.rows import dict_row

import app.graph_backend.query as gq
import app.relation_backend.query as rq
from app import app as fastapi_app
from app.graph_backend.database import driver
from app.relation_backend.database import pool

ARGS = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
RUNS = ARGS.get("runs", 50)
WARMUP = ARGS.get("warmup", 10)
# Wspólna rozgrzewka przed wszystkimi pomiarami: Neo4j działa w JVM, której kompilator JIT optymalizuje
# kod dopiero po setkach wykonań. Bez niej warstwy mierzone na początku (asgi, driver) wypadały
# wolniej niż mierzone później z hosta warstwy HTTPS, choć te zawierają więcej pracy.
GLOBAL_WARMUP = ARGS.get("global_warmup", 200)
LOGIN_RUNS = ARGS.get("login_runs", 10)
PASSWORD = "student123"

# ---------------------------------------------------------------- nagrywanie zapytań

_recording: ContextVar[list | None] = ContextVar("recording", default=None)
_g_run, _r_run = gq.run, rq.run


async def _g_rec(runner, query, **params):
    rec = _recording.get()
    if rec is not None:
        rec.append({"query": query, "params": params})
    return await _g_run(runner, query, **params)


async def _r_rec(conn, query, **params):
    rec = _recording.get()
    if rec is not None:
        rec.append({"query": query, "params": params})
    return await _r_run(conn, query, **params)


def _patch() -> None:
    gq.run, rq.run = _g_rec, _r_rec
    for name, mod in list(sys.modules.items()):
        if name.startswith("app.graph_backend") and getattr(mod, "run", None) is _g_run:
            mod.run = _g_rec
        if name.startswith("app.relation_backend") and getattr(mod, "run", None) is _r_run:
            mod.run = _r_rec


# ---------------------------------------------------------------- wywołanie ASGI w procesie

async def asgi(method: str, path: str, token: str | None, body: dict | None) -> tuple[int, bytes]:
    p, _, qs = path.partition("?")
    headers = [(b"host", b"localhost")]
    data = json.dumps(body).encode() if body is not None else b""
    if body is not None:
        headers.append((b"content-type", b"application/json"))
    if token:
        headers.append((b"authorization", f"Bearer {token}".encode()))
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": method,
             "scheme": "https", "path": p, "raw_path": p.encode(), "query_string": qs.encode(), "root_path": "",
             "headers": headers, "client": ("127.0.0.1", 1), "server": ("localhost", 8000)}
    sent = False

    async def receive():
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": data, "more_body": False}
        return {"type": "http.disconnect"}

    status, chunks = 0, []

    async def send(msg):
        nonlocal status
        if msg["type"] == "http.response.start":
            status = msg["status"]
        elif msg["type"] == "http.response.body":
            chunks.append(msg.get("body", b""))

    await fastapi_app(scope, receive, send)
    return status, b"".join(chunks)


# ---------------------------------------------------------------- dane do żądań

def token(idx: str, roles: list[str]) -> str:
    now = time.time()
    return jwt.encode({"sub": f"{idx}@bench", "idx": idx, "roles": roles, "iat": now, "exp": int(now) + 7200},
                      os.environ["JWT_SECRET"], algorithm="HS256")


async def cy(query: str, **params) -> list[dict]:
    async with driver.session() as s:
        return [r.data() async for r in await s.run(query, **params)]


async def pick() -> dict:
    """Parametry żądań wybrane z danych bieżącej skali (zapytaniami do Neo4j)."""
    # Grupa o możliwie stałym rozmiarze we wszystkich skalach (laboratorium, do 16 osób), z ocenami:
    # zapytania punktowe zwracają wtedy tyle samo wierszy, a różnice wynikają z rozmiaru bazy.
    g = (await cy("""
        MATCH (t:Teacher)-[:TEACHES]->(g:Group)<-[r:REGISTERED_IN]-(st:Student)
        WITH t, g, count(st) AS n, collect(CASE WHEN r.grade IS NOT NULL THEN [st.idx, r.grade] END) AS graded
        WHERE size(graded) > 0
        RETURN t.idx AS teacher, g.id AS group_id, graded[0][0] AS student, graded[0][1] AS grade, n
        ORDER BY abs(n - 16), g.id LIMIT 1"""))[0]
    reg = (await cy("""
        MATCH (st:Student:User)-[:ASSIGNED]->(:RegistrationTurn)<-[:HAS_TURN]-(reg:Registration)-[:OPENS]->(gr:Group)
              -[:OF_TYPE]->(:GroupType)<-[:HAS_TYPE]-(:SubjectInstance)-[:INSTANCE_OF]->(su:Subject)
        RETURN st.idx AS student, st.email AS email, reg.id AS registration, su.code AS subject
        ORDER BY CASE st.idx WHEN '279413' THEN 0 ELSE 1 END, st.idx LIMIT 1"""))[0]
    op = (await cy("""
        MATCH (o:Opinion)-[:ABOUT_TEACHER]->(t:Teacher) RETURN t.idx AS teacher, count(o) AS n
        ORDER BY n DESC, t.idx LIMIT 1"""))[0]
    return {"teacher": g["teacher"], "group_id": g["group_id"], "graded_student": g["student"], "grade": g["grade"],
            "group_size": g["n"], "student": reg["student"], "email": reg["email"], "registration": reg["registration"],
            "subject": reg["subject"], "opinion_teacher": op["teacher"], "opinions": op["n"]}


def endpoints(p: dict) -> list[dict]:
    st, te = token(p["student"], ["Student"]), token(p["teacher"], ["Teacher"])
    return [
        {"name": "POST /login", "method": "POST", "path": "/login", "token": None,
         "body": {"email": p["email"], "password": PASSWORD}},
        {"name": "GET /subjects", "method": "GET", "path": "/subjects", "token": st, "body": None},
        {"name": "GET /opinions", "method": "GET", "path": f"/opinions?teacher_idx={p['opinion_teacher']}",
         "token": st, "body": None},
        {"name": "GET /me/registrations/{id}/groups", "method": "GET",
         "path": f"/me/registrations/{p['registration']}/groups?subject_code={p['subject']}", "token": st, "body": None},
        {"name": "GET /groups/{id}/students", "method": "GET", "path": f"/groups/{p['group_id']}/students",
         "token": te, "body": None},
        {"name": "GET /students/{idx}", "method": "GET", "path": f"/students/{p['graded_student']}",
         "token": te, "body": None},
        {"name": "PUT /groups/{id}/students/{idx}/grade", "method": "PUT",
         "path": f"/groups/{p['group_id']}/students/{p['graded_student']}/grade", "token": te,
         "body": {"grade": p["grade"]}},
    ]


PREFIX = {"neo4j": "/api", "postgres": "/api/rel"}

# ---------------------------------------------------------------- warstwy surowe


async def driver_graph(queries: list[dict]) -> None:
    async with driver.session() as s:  # jak get_session(): sesja na żądanie, transakcje automatyczne
        for q in queries:
            await _g_run(s, q["query"], **q["params"])


async def driver_rel(queries: list[dict]) -> None:
    async with pool.connection() as conn:  # jak get_conn(): jedna transakcja na żądanie
        for q in queries:
            await _r_run(conn, q["query"], **q["params"])


def walk(node: dict, children: str):
    yield node
    for c in node.get(children, []) or []:
        yield from walk(c, children)


async def profile_graph(q: dict) -> dict:
    async with driver.session() as s:
        res = await s.run("PROFILE " + q["query"], q["params"])
        rows = len([r async for r in res])
        summary = await res.consume()
    ops = list(walk(summary.profile, "children"))
    est_err = max((max(o["rows"], 1) / max(o["args"].get("EstimatedRows", 1), 1)
                   if o["rows"] >= o["args"].get("EstimatedRows", 0)
                   else max(o["args"].get("EstimatedRows", 1), 1) / max(o["rows"], 1)) for o in ops)
    return {
        "engine_ms": sum(o.get("time", 0) for o in ops) / 1e6,
        "rows": rows,
        "work": sum(o.get("dbHits", 0) for o in ops),                 # db hits
        "cache_hits": sum(o.get("pageCacheHits", 0) for o in ops),
        "cache_misses": sum(o.get("pageCacheMisses", 0) for o in ops),
        "memory_bytes": summary.profile["args"].get("GlobalMemory", 0),
        "estimate_error": est_err,
        "available_after_ms": summary.result_available_after,
        "consumed_after_ms": summary.result_consumed_after,
        "operators": [re.sub(r"@neo4j$", "", o["operatorType"]) for o in ops],
    }



# Zapytania API trafiają do PostgreSQL jako polecenia przygotowane: psycopg przygotowuje zapytanie
# po 5 wykonaniach na danym połączeniu, a PostgreSQL po kolejnych 5 może przejść na plan ogólny
# (plan_cache_mode = auto). Plan ogólny bywa inny niż plan dla konkretnych parametrów - dla katalogu
# przedmiotów przy 10 000 studentów plan dla parametrów przekracza próg kompilacji JIT
# (jit_above_cost), a plan ogólny nie. Dlatego EXPLAIN ANALYZE dotyczy polecenia przygotowanego
# (PREPARE ... / EXPLAIN EXECUTE) na osobnym połączeniu: rozgrzewka w main() wykonuje je kilka razy,
# więc mierzony jest plan, którego używa API. Połączenie nie pochodzi z puli i ma wyłączone
# automatyczne przygotowywanie psycopg: psycopg przy wycofaniu transakcji, w której przygotowywał
# własne polecenia, wysyła DEALLOCATE ALL, co usunęłoby też polecenia przygotowane tutaj.
_eng_conn = None
_prepared: dict[str, tuple[str, list[str]]] = {}


async def _explain_rel(q: dict, options: str) -> dict:
    global _eng_conn
    if _eng_conn is None:
        _eng_conn = await psycopg.AsyncConnection.connect(pool.conninfo, **pool.kwargs, prepare_threshold=None)
    if q["query"] not in _prepared:
        names: list[str] = []

        def placeholder(m):
            if m.group(1) not in names:
                names.append(m.group(1))
            return f"${names.index(m.group(1)) + 1}"

        text = re.sub(r"%\((\w+)\)s", placeholder, q["query"]).replace("%%", "%")
        stmt = f"bench_{len(_prepared)}"
        async with _eng_conn.transaction():
            await _eng_conn.execute(f"PREPARE {stmt} AS {text}", prepare=False)
        _prepared[q["query"]] = (stmt, names)
    stmt, names = _prepared[q["query"]]
    args = ", ".join(f"%({n})s" for n in names)
    async with _eng_conn.transaction(force_rollback=True):
        cur = psycopg.AsyncClientCursor(_eng_conn, row_factory=dict_row)  # parametry EXECUTE jako literały
        await cur.execute(f"EXPLAIN ({options}, FORMAT JSON) EXECUTE {stmt}" + (f"({args})" if names else ""),
                          q["params"])
        return (await cur.fetchone())["QUERY PLAN"][0]


async def engine_rel(q: dict) -> dict:
    """Czas wykonania bez pomiaru czasu poszczególnych węzłów planu (TIMING OFF), który przy dużych
    wynikach zawyża czas o kilkadziesiąt procent."""
    plan = await _explain_rel(q, "ANALYZE, TIMING OFF")
    return {"engine_ms": plan["Execution Time"], "jit": "JIT" in plan}


async def profile_rel(q: dict) -> dict:
    plan = await _explain_rel(q, "ANALYZE, BUFFERS, MEMORY, SERIALIZE")
    nodes = list(walk(plan["Plan"], "Plans"))
    root = plan["Plan"]
    est_err = max((max(n["Actual Rows"], 1) / max(n["Plan Rows"], 1) if n["Actual Rows"] >= n["Plan Rows"]
                   else max(n["Plan Rows"], 1) / max(n["Actual Rows"], 1)) for n in nodes)
    mem_kb = sum(n.get("Sort Space Used", 0) if n.get("Sort Space Type") == "Memory" else 0 for n in nodes) \
        + sum(n.get("Peak Memory Usage", 0) for n in nodes)
    hits = root.get("Shared Hit Blocks", 0) + plan["Planning"].get("Shared Hit Blocks", 0)
    reads = root.get("Shared Read Blocks", 0) + plan["Planning"].get("Shared Read Blocks", 0)
    return {
        "engine_ms": plan["Execution Time"],
        "planning_ms": plan["Planning Time"],
        "rows": int(root["Actual Rows"]) if not root.get("Actual Loops", 1) > 1 else int(root["Actual Rows"]),
        "work": root.get("Shared Hit Blocks", 0) + root.get("Shared Read Blocks", 0),   # bloki 8 kB (wykonanie)
        "cache_hits": hits,
        "cache_misses": reads,
        "memory_bytes": mem_kb * 1024 + plan["Planning"].get("Memory Used", 0) * 1024,
        "estimate_error": est_err,
        "jit": "JIT" in plan,
        "serialized_bytes": plan.get("Serialization", {}).get("Output Volume", 0) * 1024,
        "operators": [n["Node Type"] + (f" ({n['Join Type']})" if n.get("Join Type") and n["Node Type"] in
                                        ("Hash Join", "Nested Loop", "Merge Join") else "") for n in nodes],
    }


def shape(query: str, backend: str) -> dict:
    text = " ".join(query.split())
    if backend == "neo4j":
        return {"chars": len(text), "relationship_patterns": len(re.findall(r"-\[", text)),
                "match_clauses": len(re.findall(r"\b(OPTIONAL MATCH|MATCH)\b", text))}
    return {"chars": len(text), "joins": len(re.findall(r"\bJOIN\b", text, re.I)),
            "selects": len(re.findall(r"\bSELECT\b", text, re.I))}


async def timed(fn, n: int) -> list[float]:
    out = []
    for i in range(WARMUP + n):
        t0 = time.perf_counter()
        await fn()
        dt = (time.perf_counter() - t0) * 1000
        if i >= WARMUP:
            out.append(dt)
    return out


async def main() -> None:
    _patch()
    async with fastapi_app.router.lifespan_context(fastapi_app):
        p = await pick()
        eps = endpoints(p)
        for ep in eps:
            for backend in ("neo4j", "postgres"):
                for _ in range(5 if ep["name"] == "POST /login" else GLOBAL_WARMUP):
                    await asgi(ep["method"], PREFIX[backend] + ep["path"], ep["token"], ep["body"])
        print(f"rozgrzewka: {GLOBAL_WARMUP} wywołań na punkt końcowy", file=sys.stderr)
        samples, queries = [], []
        for ep in eps:
            n = LOGIN_RUNS if ep["name"] == "POST /login" else RUNS
            for backend in ("neo4j", "postgres"):
                path = PREFIX[backend] + ep["path"]
                rec = []
                tok = _recording.set(rec)
                status, body = await asgi(ep["method"], path, ep["token"], ep["body"])
                _recording.reset(tok)
                if status >= 400:
                    raise RuntimeError(f"{backend} {ep['name']}: {status} {body[:300]!r}")
                size = len(body)

                async def call():
                    s, _ = await asgi(ep["method"], path, ep["token"], ep["body"])
                    assert s < 400, s

                samples.append({"endpoint": ep["name"], "backend": backend, "layer": "asgi", "ms": await timed(call, n)})
                drv = driver_graph if backend == "neo4j" else driver_rel
                samples.append({"endpoint": ep["name"], "backend": backend, "layer": "driver",
                                "ms": await timed(lambda: drv(rec), n)})
                prof = profile_graph if backend == "neo4j" else profile_rel
                eng = profile_graph if backend == "neo4j" else engine_rel
                for _ in range(min(WARMUP, 5)):
                    for q in rec:
                        await eng(q)
                engine = []
                for _ in range(n):
                    engine.append(sum([(await eng(q))["engine_ms"] for q in rec]))
                diag = [await prof(q) for q in rec]
                samples.append({"endpoint": ep["name"], "backend": backend, "layer": "engine", "ms": engine})
                for i, (q, d) in enumerate(zip(rec, diag)):
                    queries.append({"endpoint": ep["name"], "backend": backend, "query_no": i, "query": q["query"],
                                    "response_bytes": size, **shape(q["query"], backend), **d})
                print(f"{ep['name']} {backend}: {len(rec)} zapytań", file=sys.stderr)
    if _eng_conn is not None:
        await _eng_conn.close()
    await driver.close()
    json.dump({"params": p, "endpoints": [{k: e[k] for k in ("name", "method", "path", "token", "body")} for e in eps],
               "samples": samples, "queries": queries}, sys.stdout, ensure_ascii=False, default=str)


asyncio.run(main())
