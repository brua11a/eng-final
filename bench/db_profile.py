"""Runs the compared queries directly in both databases and collects measurements.

Runs inside the app container, which has both drivers, the database addresses and credentials:

    docker compose exec -T app python - < bench/db_profile.py > bench/results/db_profile.json

For every query:
  * time       - median wall time of executing the query and fetching all rows, measured by
                 the driver (N runs after warm-up), in ms,
  * db_time    - time reported by the database itself: Neo4j result_available_after +
                 result_consumed_after, PostgreSQL "Execution Time" from EXPLAIN ANALYZE, in ms,
  * work       - Neo4j: total db hits from PROFILE; PostgreSQL: shared buffer hits + reads
                 from EXPLAIN (ANALYZE, BUFFERS) - different units, compared only within a database,
  * shape      - number of relationship patterns (Cypher) / JOIN clauses (SQL) and query length.
Writes are executed in a transaction that is rolled back.
"""

import asyncio
import json
import re
import statistics
import sys
import time

from app.graph_backend.database import driver
from app.relation_backend.database import pool
from app.graph_backend.routers import catalogue as g_cat, public as g_pub, student as g_stu, teacher as g_tea
from app.relation_backend.routers import catalogue as r_cat, public as r_pub, student as r_stu, teacher as r_tea

RUNS = int(sys.argv[1]) if len(sys.argv) > 1 else 50
WARMUP = 10

# Cypher queries defined inline in graph_backend endpoints are repeated here verbatim.
G_OPEN_GROUPS = """
MATCH (st:Student {idx: $student_idx})
MATCH (reg:Registration {id: $registration_id})-[:OPENS]->(g:Group)
MATCH (g)-[:OF_TYPE]->(gt:GroupType)<-[:HAS_TYPE]-(:SubjectInstance)-[:INSTANCE_OF]->(:Subject {code: $subject_code})
OPTIONAL MATCH (g)-[:IN_ROOM]->(r:Room)
OPTIONAL MATCH (t:Teacher)-[:TEACHES]->(g)
OPTIONAL MATCH (st)-[mine:REGISTERED_IN]->(g)
RETURN g.id AS id, gt.g_type AS g_type, g.number AS number, g.weekday AS weekday,
  g.start_time AS start, g.end_time AS end, g.capacity AS capacity,
  size([(g)<-[:REGISTERED_IN]-() | 1]) AS filled,
  r.building + " " + r.room_num AS room, t.name + " " + t.surname AS teacher,
  mine IS NOT NULL AS registered
ORDER BY gt.g_type, g.number
"""
G_TEACHES_GROUP = """
MATCH (t:Teacher {idx: $teacher_idx})-[:TEACHES]->(g:Group {id: $group_id})
RETURN g.id AS id
"""
G_STUDENTS_IN_GROUP = """
MATCH (g:Group {id: $group_id})
MATCH (st:Student)-[r:REGISTERED_IN]->(g)
RETURN st.idx AS idx, st.name AS name, st.surname AS surname, st.phone AS phone,
  st.photo AS photo, st.joined AS joined, r.grade AS grade
ORDER BY st.surname, st.name
"""
G_SET_GRADE = """
MATCH (st:Student {idx: $student_idx})-[r:REGISTERED_IN]->(g:Group {id: $group_id})
SET r.grade = $grade
RETURN g.id AS group_id, st.idx AS student_idx, r.grade AS grade
"""


QUERIES = [
    # name, complexity class, cypher, sql, write?
    ("login", "prosta", g_pub._LOGIN, r_pub.LOGIN, False),
    ("rebac: prowadzący uczy grupę", "prosta", G_TEACHES_GROUP, r_tea.TEACHES_GROUP, False),
    ("rebac: student w turze zapisów", "prosta", g_stu._CAN_USE_REGISTRATION, r_stu.CAN_USE_REGISTRATION, False),
    ("studenci w grupie", "średnia", G_STUDENTS_IN_GROUP, r_tea.STUDENTS_IN_GROUP, False),
    ("opinie o prowadzącym", "średnia", g_cat._OPINIONS, r_cat.OPINIONS, False),
    ("grupy w zapisach", "średnia", G_OPEN_GROUPS, r_stu.OPEN_GROUPS, False),
    ("oceny studenta (średnia)", "trudna", g_tea._STUDENT_GRADES, r_tea.STUDENT_GRADES, False),
    ("katalog przedmiotów", "trudna", g_cat._SUBJECTS, r_cat.SUBJECTS, False),
    ("wystawienie oceny", "zapis", G_SET_GRADE, r_tea.SET_GRADE, True),
]


def cypher_shape(q: str) -> dict:
    return {"hops": len(re.findall(r"-\[", q)), "chars": len(" ".join(q.split()))}


def sql_shape(q: str) -> dict:
    return {"joins": len(re.findall(r"\bJOIN\b", q)), "subqueries": q.count("SELECT") - 1, "chars": len(" ".join(q.split()))}


def db_hits(plan) -> int:
    return plan.get("dbHits", 0) + sum(db_hits(c) for c in plan.get("children", []))


async def sample_params() -> dict:
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute("""
            SELECT a.student_idx, a.registration_id, gt.subject_code
            FROM assigned a JOIN opens o ON o.registration_id = a.registration_id
            JOIN class_group g ON g.id = o.group_id JOIN group_type gt ON gt.id = g.group_type_id
            LIMIT 1""")
        p = dict(await cur.fetchone())
        await cur.execute("""
            SELECT te.teacher_idx, te.group_id, min(ri.student_idx) AS graded_idx
            FROM teaches te JOIN registered_in ri ON ri.group_id = te.group_id
            GROUP BY te.teacher_idx, te.group_id
            ORDER BY count(*) DESC LIMIT 1""")
        t = dict(await cur.fetchone())
        await cur.execute("SELECT email FROM app_user ORDER BY idx LIMIT 1")
        email = (await cur.fetchone())["email"]
        await cur.execute("SELECT id, year, season FROM academic_cycle")
        cycles = [r["id"] for r in await cur.fetchall()]
    return {
        "email": email, "student_idx": p["student_idx"], "registration_id": p["registration_id"],
        "subject_code": p["subject_code"], "teacher_idx": t["teacher_idx"], "group_id": t["group_id"],
        "name": None, "code": None, "cycle_ids": cycles,
        "grade": 4.0, "graded_idx": t["graded_idx"],
    }


def params_for(name: str, p: dict) -> dict:
    q = dict(p)
    if name == "oceny studenta (średnia)":
        q["student_idx"] = p["graded_idx"]
    if name == "wystawienie oceny":
        q["student_idx"] = p["graded_idx"]
    if name == "opinie o prowadzącym":
        q["group_id"] = None
    return q


async def neo4j_measure(cypher: str, params: dict, write: bool) -> dict:
    times = []
    async with driver.session() as session:
        for i in range(WARMUP + RUNS):
            tx = await session.begin_transaction()
            t0 = time.perf_counter()
            result = await tx.run(cypher, params)
            rows = [r async for r in result]
            dt = (time.perf_counter() - t0) * 1000
            await (tx.rollback() if write else tx.commit())
            if i >= WARMUP:
                times.append(dt)
        tx = await session.begin_transaction()
        result = await tx.run("PROFILE " + cypher, params)
        summary = await result.consume()
        await tx.rollback()
    return {
        "rows": len(rows),
        "time_ms": statistics.median(times),
        "time_p95_ms": statistics.quantiles(times, n=20)[18],
        "db_time_ms": summary.result_available_after + summary.result_consumed_after,
        "db_hits": db_hits(summary.profile),
    }


async def pg_measure(sql: str, params: dict, write: bool) -> dict:
    times = []
    async with pool.connection() as conn:
        for i in range(WARMUP + RUNS):
            async with conn.transaction(force_rollback=write):
                async with conn.cursor() as cur:
                    t0 = time.perf_counter()
                    await cur.execute(sql, params)
                    rows = await cur.fetchall()
                    dt = (time.perf_counter() - t0) * 1000
            if i >= WARMUP:
                times.append(dt)
        async with conn.transaction(force_rollback=True):
            async with conn.cursor() as cur:
                await cur.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql, params)
                plan = (await cur.fetchone())["QUERY PLAN"][0]
    root = plan["Plan"]
    return {
        "rows": len(rows),
        "time_ms": statistics.median(times),
        "time_p95_ms": statistics.quantiles(times, n=20)[18],
        "db_time_ms": plan["Execution Time"],
        "planning_ms": plan["Planning Time"],
        "buffers": root.get("Shared Hit Blocks", 0) + root.get("Shared Read Blocks", 0),
    }


async def main() -> None:
    await pool.open(wait=True)
    p = await sample_params()
    out = []
    for name, cls, cypher, sql, write in QUERIES:
        params = params_for(name, p)
        out.append({
            "query": name, "class": cls,
            "neo4j": {**await neo4j_measure(cypher, params, write), **cypher_shape(cypher)},
            "postgres": {**await pg_measure(sql, params, write), **sql_shape(sql)},
        })
        print(f"{name}: done", file=sys.stderr)
    await pool.close()
    await driver.close()
    json.dump({"runs": RUNS, "params": {k: v for k, v in p.items() if k != "cycle_ids"}, "results": out},
              sys.stdout, ensure_ascii=False, indent=1, default=str)


asyncio.run(main())
