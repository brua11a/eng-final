"""Testy planisty: surowe plany zapytań PostgreSQL i Neo4j do rozdziału 7.8 (diagnostyka zapytań).

Powtarza wszystkie obserwacje pracy dotyczące planowania zapytań, na tych samych danych co pomiary
(skala z bench/generate.py, domyślnie 10 000 studentów), i zapisuje surowe plany do
bench/results/planner/:

  1. plan_cache.txt - dla każdego zapytania PostgreSQL każdego punktu końcowego:
       a) EXPLAIN ANALYZE z wartościami wpisanymi w treść (plan dla konkretnych parametrów),
       b) polecenie przygotowane po 10 wykonaniach (tak jak w API: psycopg przygotowuje zapytanie
          po 5 wykonaniach, PostgreSQL po kolejnych 5 może przejść na plan ogólny) - liczniki
          custom_plans / generic_plans z pg_prepared_statements i plan, którego używa API,
       c) plan ogólny wymuszony (plan_cache_mode = force_generic_plan) - jaki byłby plan bez
          znajomości parametrów,
     oraz mediany czasu wykonania (EXPLAIN ANALYZE, TIMING OFF) dla a) i b);
  2. opinions_old_new.txt - GET /opinions w pierwotnej wersji (jeden warunek `IS NULL OR` dla obu
     filtrów) i po rozdzieleniu zapytania, w obu bazach (PostgreSQL: jak w 1., Neo4j: PROFILE);
  3. import_neo4j.txt - plan instrukcji importu krawędzi studentów (edges.cypher) na pustej bazie
     w transakcji importu, bez wskazania indeksu i ze wskazaniem (USING INDEX); osobny kontener
     Neo4j z pustym wolumenem (część wykonywana na hoście, patrz import_test()).

Uruchomienie (na hoście, stos bench/run.py dla danej skali musi działać, np.):
    BENCH_DATA=$PWD/bench/data/10000 docker compose -p thesis-bench \\
        -f docker-compose.yml -f bench/docker-compose.bench.yml up -d --build
    python bench/planner.py [--scale 10000] [--runs 30]

Część 1-2 wykonuje się w kontenerze app (sterowniki, kod API, JWT_SECRET): skrypt przekazuje na
standardowe wejście interpretera kod bench/measure.py (nagrywanie zapytań, parametry żądań) bez
jego funkcji main oraz własny kod.
"""

import json
import os
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

IN_CONTAINER = os.environ.get("PLANNER_IN_CONTAINER") == "1"

# Pierwotne wersje zapytania GET /opinions (przed rozdzieleniem na warianty, 5.5.9).
# PostgreSQL: app/relation_backend/routers/catalogue.py::OPINIONS z commita 142320d.
OLD_OPINIONS_PG = """
SELECT
  o.id,
  o.grade::float8 AS grade,
  oc.content,
  (o.submit AT TIME ZONE 'Europe/Warsaw')::date AS submit,
  g.id AS group_id,
  su.code AS course_code,
  su.name AS course_name,
  gt.g_type,
  ac.year || ' ' || ac.season AS cycle,
  tp.idx AS teacher_idx,
  tp.name || ' ' || tp.surname AS teacher
FROM opinion o
LEFT JOIN opinion_content oc ON oc.opinion_id = o.id
JOIN class_group g ON g.id = o.group_id
JOIN person tp ON tp.idx = o.teacher_idx
JOIN group_type gt ON gt.id = g.group_type_id
JOIN subject su ON su.code = gt.subject_code
JOIN academic_cycle ac ON ac.id = gt.cycle_id
WHERE (%(teacher_idx)s::text IS NULL OR o.teacher_idx = %(teacher_idx)s)
  AND (%(group_id)s::text IS NULL OR o.group_id = %(group_id)s)
ORDER BY o.submit DESC
"""
# Neo4j: app/graph_backend/routers/catalogue.py::_OPINIONS z commita d3bab91.
OLD_OPINIONS_NEO4J = """
MATCH (o:Opinion)-[:ABOUT]->(g:Group), (o)-[:ABOUT_TEACHER]->(t:Teacher)
WHERE ($teacher_idx IS NULL OR t.idx = $teacher_idx)
  AND ($group_id IS NULL OR g.id = $group_id)
MATCH (g)-[:OF_TYPE]->(gt:GroupType)<-[:HAS_TYPE]-(si:SubjectInstance)-[:INSTANCE_OF]->(su:Subject)
MATCH (si)-[:OFFERED_IN]->(ac:AcademicCycle)
RETURN
  o.id AS id,
  o.grade AS grade,
  o.content AS content,
  date(o.submit) AS submit,
  g.id AS group_id,
  su.code AS course_code,
  su.name AS course_name,
  gt.g_type AS g_type,
  ac.year + " " + ac.season AS cycle,
  t.idx AS teacher_idx,
  t.name + " " + t.surname AS teacher
ORDER BY o.submit DESC
"""

# ====================================================================== część w kontenerze app

if IN_CONTAINER:
    PRUNS = json.loads(sys.argv[1]).get("runs", 30) if len(sys.argv) > 1 else 30

    def pg_positional(query: str) -> tuple[str, list[str]]:
        """%(nazwa)s -> $n, tak jak psycopg przy przygotowaniu polecenia (ta sama nazwa = ten sam $n)."""
        names: list[str] = []

        def ph(m):
            if m.group(1) not in names:
                names.append(m.group(1))
            return f"${names.index(m.group(1)) + 1}"

        return re.sub(r"%\((\w+)\)s", ph, query).replace("%%", "%"), names

    def plan_numbers(text: str) -> dict:
        first = text.splitlines()[0]
        cost = re.search(r"cost=[\d.]+\.\.([\d.]+)", first)
        pt = re.search(r"Planning Time: ([\d.]+) ms", text)
        et = re.search(r"Execution Time: ([\d.]+) ms", text)
        return {"cost": float(cost.group(1)) if cost else None, "planning_ms": float(pt.group(1)) if pt else None,
                "execution_ms": float(et.group(1)) if et else None, "jit": "\nJIT:" in "\n" + text,
                "seq_scans": re.findall(r"Seq Scan on (\w+)", text),
                "index_scans": re.findall(r"Index (?:Only )?Scan using (\w+)", text)}

    async def explain_text(cur, sql: str, params=None) -> str:
        await cur.execute(sql, params)
        return "\n".join(r["QUERY PLAN"] for r in await cur.fetchall())

    async def pg_case(conn, label: str, query: str, params: dict, n: int) -> dict:
        """Plan dla konkretnych parametrów, plan po 10 wykonaniach polecenia przygotowanego i plan ogólny."""
        text, names = pg_positional(query)
        stmt = ("planner_" + re.sub(r"\W+", "_", label)[:40]).lower()  # nazwy w katalogu są małymi literami
        args = "(" + ", ".join(f"%({k})s" for k in names) + ")" if names else ""
        cur = psycopg.AsyncClientCursor(conn, row_factory=dict_row)  # parametry jako literały
        out: dict = {"label": label, "params": params, "query": query.strip()}
        async with conn.transaction(force_rollback=True):  # zapis oceny ustawia tę samą ocenę; i tak wycofany
            out["custom_text"] = await explain_text(cur, "EXPLAIN (ANALYZE, BUFFERS, SUMMARY) " + query, params)
            await cur.execute(f"PREPARE {stmt} AS {text}")
            counters = []
            for i in range(10):
                await cur.execute(f"EXECUTE {stmt}{args}", params)
                await cur.execute("SELECT generic_plans, custom_plans FROM pg_prepared_statements WHERE name = %s",
                                  (stmt,))
                counters.append(dict(await cur.fetchone()))
            out["counters"] = counters
            out["api_text"] = await explain_text(cur, f"EXPLAIN (ANALYZE, BUFFERS, SUMMARY) EXECUTE {stmt}{args}",
                                                 params)
            await cur.execute("SELECT generic_plans, custom_plans FROM pg_prepared_statements WHERE name = %s",
                              (stmt,))
            out["counters_after"] = dict(await cur.fetchone())
            # mediany czasu wykonania, bez pomiaru czasu poszczególnych węzłów planu
            cust, api = [], []
            for _ in range(n):
                cust.append(plan_numbers(await explain_text(
                    cur, "EXPLAIN (ANALYZE, TIMING OFF, SUMMARY) " + query, params))["execution_ms"])
                api.append(plan_numbers(await explain_text(
                    cur, f"EXPLAIN (ANALYZE, TIMING OFF, SUMMARY) EXECUTE {stmt}{args}", params))["execution_ms"])
            out["custom_exec_median_ms"] = statistics.median(cust)
            out["api_exec_median_ms"] = statistics.median(api)
            await cur.execute("SET LOCAL plan_cache_mode = force_generic_plan")
            out["generic_text"] = await explain_text(cur, f"EXPLAIN (ANALYZE, BUFFERS, SUMMARY) EXECUTE {stmt}{args}",
                                                     params)
            gen = []
            for _ in range(n):
                gen.append(plan_numbers(await explain_text(
                    cur, f"EXPLAIN (ANALYZE, TIMING OFF, SUMMARY) EXECUTE {stmt}{args}", params))["execution_ms"])
            out["generic_exec_median_ms"] = statistics.median(gen)
        await conn.execute(f"DEALLOCATE {stmt}")
        for k in ("custom", "api", "generic"):
            out[k] = plan_numbers(out[k + "_text"])
        return out

    def neo4j_plan_text(node: dict, depth: int = 0) -> list[str]:
        a = node.get("args", {})
        line = (f"{'  ' * depth}+{re.sub(r'@neo4j$', '', node['operatorType'])}"
                f"  | {a.get('Details', '')}"
                f"  | est. rows {a.get('EstimatedRows', 0):.0f} | rows {node.get('rows', 0)}"
                f" | db hits {node.get('dbHits', 0)}")
        lines = [line]
        for c in node.get("children", []) or []:
            lines += neo4j_plan_text(c, depth + 1)
        return lines

    async def neo4j_case(label: str, query: str, params: dict, n: int) -> dict:
        async def prof():
            async with driver.session() as s:
                res = await s.run("PROFILE " + query, params)
                rows = [r async for r in res]
                summary = await res.consume()
            return rows, summary.profile

        for _ in range(5):
            await prof()
        times = []
        for _ in range(n):
            _, p = await prof()
            times.append(sum(o.get("time", 0) for o in walk(p, "children")) / 1e6)
        rows, p = await prof()
        ops = list(walk(p, "children"))
        err = max((max(o.get("rows", 0), 1) / max(o["args"].get("EstimatedRows", 1), 1)
                   if o.get("rows", 0) >= o["args"].get("EstimatedRows", 0)
                   else max(o["args"].get("EstimatedRows", 1), 1) / max(o.get("rows", 0), 1)) for o in ops)
        return {"label": label, "params": params, "query": query.strip(), "rows": len(rows),
                "db_hits": sum(o.get("dbHits", 0) for o in ops), "estimate_error": err,
                "operators": [re.sub(r"@neo4j$", "", o["operatorType"]) for o in ops],
                "engine_median_ms": statistics.median(times), "plan_text": "\n".join(neo4j_plan_text(p))}

    async def planner_main() -> None:
        _patch()
        result = {"plan_cache": [], "opinions": {}}
        async with fastapi_app.router.lifespan_context(fastapi_app):
            p = await pick()
            eps = endpoints(p)
            conn = await psycopg.AsyncConnection.connect(pool.conninfo, **pool.kwargs, prepare_threshold=None)
            await conn.execute("ANALYZE")  # świeże statystyki, jak po autovacuum w trakcie pomiarów
            recorded = {}
            for ep in eps:
                for backend in ("postgres", "neo4j"):
                    rec = []
                    tok = _recording.set(rec)
                    status, body = await asgi(ep["method"], PREFIX[backend] + ep["path"], ep["token"], ep["body"])
                    _recording.reset(tok)
                    if status >= 400:
                        raise RuntimeError(f"{backend} {ep['name']}: {status} {body[:200]!r}")
                    recorded[(ep["name"], backend)] = rec
                for i, q in enumerate(recorded[(ep["name"], "postgres")]):
                    result["plan_cache"].append(
                        {"endpoint": ep["name"], "query_no": i,
                         **await pg_case(conn, f"{ep['name']} #{i}", q["query"], q["params"], PRUNS)})
                    print(f"{ep['name']} #{i}", file=sys.stderr)

            op_params = {"teacher_idx": p["opinion_teacher"], "group_id": None}
            few = (await cy("""
                MATCH (o:Opinion)-[:ABOUT_TEACHER]->(t:Teacher) WITH t, count(o) AS n
                RETURN t.idx AS teacher, n ORDER BY n, t.idx LIMIT 1"""))[0]
            new_pg = recorded[("GET /opinions", "postgres")][0]
            new_neo = recorded[("GET /opinions", "neo4j")][0]
            result["opinions"] = {
                "teacher": p["opinion_teacher"], "opinions": p["opinions"],
                "pg_old": await pg_case(conn, "opinions_old", OLD_OPINIONS_PG, op_params, PRUNS),
                "few_teacher": few["teacher"], "few_opinions": few["n"],
                "pg_old_few": await pg_case(conn, "opinions_old_few", OLD_OPINIONS_PG,
                                            {"teacher_idx": few["teacher"], "group_id": None}, PRUNS),
                "pg_new": await pg_case(conn, "opinions_new", new_pg["query"], new_pg["params"], PRUNS),
                "neo4j_old": await neo4j_case("opinions_old", OLD_OPINIONS_NEO4J, op_params, PRUNS),
                "neo4j_new": await neo4j_case("opinions_new", new_neo["query"], new_neo["params"], PRUNS),
            }
            await conn.close()
            await driver.close()
        json.dump(result, sys.stdout, ensure_ascii=False, default=str)

    asyncio.run(planner_main())

# ====================================================================== część na hoście

else:
    import argparse

    ROOT = Path(__file__).resolve().parent.parent
    OUT = ROOT / "bench" / "results" / "planner"

    def sh(*cmd, env=None, input=None, check=True) -> str:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env, input=input)
        if check and r.returncode:
            raise RuntimeError(f"{' '.join(cmd)}\n{r.stderr[-3000:]}")
        return r.stdout

    def compose(project: str, scale: str) -> tuple[list[str], dict]:
        env = dict(os.environ, BENCH_DATA=str(ROOT / "bench" / "data" / scale))
        return ["docker", "compose", "-p", project, "-f", "docker-compose.yml", "-f",
                "bench/docker-compose.bench.yml"], env

    def fmt(v, nd=3) -> str:
        return "–" if v is None else f"{v:.{nd}f}"

    def write_plan_cache(res: dict, scale: str) -> None:
        lines = [f"# Plany PostgreSQL zapytań API - {scale} studentów",
                 "# custom  = EXPLAIN ANALYZE z wartościami w treści (plan dla konkretnych parametrów)",
                 "# API     = polecenie przygotowane po 10 wykonaniach (plan_cache_mode = auto), jak w API",
                 "# generic = plan ogólny wymuszony (plan_cache_mode = force_generic_plan)",
                 "# liczniki: (custom_plans, generic_plans) z pg_prepared_statements po kolejnych wykonaniach", ""]
        for c in res["plan_cache"]:
            lines += [_case_text(c)]
        (OUT / "plan_cache.txt").write_text("\n".join(lines))

    def _case_text(c: dict) -> str:
        seq = " ".join(f"{x['custom_plans']}/{x['generic_plans']}" for x in c["counters"])
        lines = ["=" * 100, f"## {c['label']}", f"parametry: {json.dumps(c['params'], ensure_ascii=False)}",
                 "zapytanie:", c["query"], "",
                 f"liczniki custom/generic po wykonaniach 1..10: {seq}; po EXPLAIN EXECUTE: "
                 f"{c['counters_after']['custom_plans']}/{c['counters_after']['generic_plans']}",
                 f"koszt planu: custom {fmt(c['custom']['cost'], 2)}, API {fmt(c['api']['cost'], 2)}, "
                 f"generic {fmt(c['generic']['cost'], 2)}",
                 f"czas planowania [ms]: custom {fmt(c['custom']['planning_ms'])}, API {fmt(c['api']['planning_ms'])}",
                 f"mediana czasu wykonania [ms] (TIMING OFF): custom {fmt(c['custom_exec_median_ms'])}, "
                 f"API {fmt(c['api_exec_median_ms'])}, generic {fmt(c['generic_exec_median_ms'])}",
                 f"JIT: custom {c['custom']['jit']}, API {c['api']['jit']}, generic {c['generic']['jit']}", ""]
        for k, title in (("custom", "plan dla konkretnych parametrów"), ("api", "plan używany przez API"),
                         ("generic", "plan ogólny (wymuszony)")):
            lines += [f"--- {title}", c[k + "_text"], ""]
        return "\n".join(lines)

    def write_opinions(o: dict, scale: str) -> None:
        lines = [f"# GET /opinions: wersja pierwotna (IS NULL OR) i po rozdzieleniu - {scale} studentów",
                 f"# prowadzący {o['teacher']} ({o['opinions']} opinii), group_id = NULL (jak w pomiarach)", "",
                 "#" * 100, "# PostgreSQL", "#" * 100, _case_text(o["pg_old"]), _case_text(o["pg_new"]),
                 f"# wersja pierwotna dla prowadzącego z najmniejszą liczbą opinii: {o['few_teacher']} "
                 f"({o['few_opinions']} opinii)", _case_text(o["pg_old_few"]),
                 "#" * 100, "# Neo4j (PROFILE, plan z pamięci podręcznej)", "#" * 100]
        for k in ("neo4j_old", "neo4j_new"):
            c = o[k]
            lines += ["=" * 100, f"## {c['label']}", f"parametry: {json.dumps(c['params'], ensure_ascii=False)}",
                      "zapytanie:", c["query"], "",
                      f"wiersze {c['rows']}, db hits {c['db_hits']}, maks. błąd oszacowania {c['estimate_error']:.1f}, "
                      f"mediana czasu silnika {c['engine_median_ms']:.3f} ms", "", c["plan_text"], ""]
        (OUT / "opinions_old_new.txt").write_text("\n".join(lines))

    # ------------------------------------------------------------------ test importu (pusta baza)

    def import_test(scale: str) -> None:
        """Plan instrukcji importu krawędzi studentów w warunkach init_db.py: węzły i krawędzie są
        importowane w jednej transakcji, więc w chwili planowania krawędzi statystyki bazy (liczniki
        etykiet, selektywność indeksów) pochodzą z pustej bazy - zaimportowane węzły nie są jeszcze
        zatwierdzone. Osobny projekt Compose z pustym wolumenem; potrzebny wolny port 7687."""
        project = "thesis-planner-import"
        cmd, env = compose(project, scale)
        sh(*cmd, "down", "-v", env=env, check=False)
        sh(*cmd, "up", "-d", "neo4j", env=env)
        dot = {k: v for k, v in (l.split("=", 1) for l in (ROOT / ".env").read_text().splitlines()
                                 if "=" in l and not l.startswith("#"))}
        shell = [*cmd, "exec", "-T", "neo4j", "cypher-shell", "-a", "bolt+ssc://localhost:7687",
                 "-u", dot["NEO4J_USER"], "-p", dot["NEO4J_PASSWORD"], "--format", "verbose"]
        for _ in range(120):
            if subprocess.run([*shell, "RETURN 1;"], cwd=ROOT, env=env, capture_output=True).returncode == 0:
                break
            time.sleep(2)
        try:
            schema = (ROOT / "queries" / "schema.cypher").read_text()
            sh(*shell, env=env, input=schema.rstrip().rstrip(";") + ";\n")
            nodes = (ROOT / "queries" / "nodes.cypher").read_text()
            edges = (ROOT / "queries" / "edges.cypher").read_text()
            stmts = [s.strip() for s in re.split(r";\s*$", edges, flags=re.M) if s.strip()]
            hinted = next(s for s in stmts if "student_registered.csv" in s)
            # pierwotna postać (przed commitem dfedccb): sama etykieta Student, bez Person i bez wskazania
            original = hinted.replace("(st:Person:Student {idx: row.student_idx}) USING INDEX st:Person(idx)",
                                      "(st:Student {idx: row.student_idx})")
            labelled = hinted.replace(" USING INDEX st:Person(idx)", "")
            variants = [("A", "pierwotna: MATCH (st:Student {idx: ...})", original),
                        ("B", "z etykietą Person, bez USING INDEX", labelled),
                        ("C", "obecna (queries/edges.cypher): z USING INDEX st:Person(idx)", hinted)]
            sections = []
            for key, title, q in variants:
                out = sh(*shell, env=env, input=":begin\n" + nodes + "\nMATCH (n) RETURN count(n) AS `węzły w "
                         "transakcji`;\nEXPLAIN " + q + ";\n:rollback\n")
                sections += ["=" * 100, f"# {key}) w transakcji importu - {title}", q.split("\n")[1], "", out]
            # dla porównania: te same węzły zatwierdzone, statystyki z wypełnionej bazy
            sh(*shell, env=env, input=nodes)
            after = sh(*shell, env=env, input="CALL db.resampleOutdatedIndexes();\nEXPLAIN " + original + ";\n")
            sections += ["=" * 100, "# D) po zatwierdzeniu węzłów (statystyki wypełnionej bazy) - pierwotna postać",
                         original.split("\n")[1], "", after]
            # ten sam wzorzec (:Student {idx}) w zapytaniu tylko do odczytu i w zapytaniach modyfikujących
            for key, q in (("E", "MATCH (st:Student {idx: $i}) RETURN st.name"),
                           ("F", "MATCH (st:Student {idx: $i}) SET st.x = 1"),
                           ("G", "MATCH (st:Student {idx: $i}) MATCH (g:Group {id: $g}) MERGE (st)-[:REGISTERED_IN]->(g)"),
                           ("H", "MATCH (st:Person:Student {idx: $i}) SET st.x = 1")):
                sections += ["=" * 100, f"# {key}) wypełniona baza: {q}", "",
                             sh(*shell, env=env, input=f"EXPLAIN {q};\n")]
        finally:
            sh(*cmd, "down", "-v", env=env, check=False)
        text = [f"# Import Neo4j: plan instrukcji krawędzi REGISTERED_IN - {scale} studentów",
                "# init_db.py importuje węzły i krawędzie w jednej transakcji: przy planowaniu krawędzi węzły",
                "# nie są jeszcze zatwierdzone, więc planista widzi statystyki pustej bazy (Estimated Rows = 0).",
                "# Plany A-C w transakcji importu (węzły zaimportowane, niezatwierdzone), plan D po zatwierdzeniu.",
                "", "pełna instrukcja (wariant C):", hinted, "", *sections]
        (OUT / "import_neo4j.txt").write_text("\n".join(text))

    def main() -> None:
        ap = argparse.ArgumentParser()
        ap.add_argument("--scale", default="10000")
        ap.add_argument("--runs", type=int, default=30)
        ap.add_argument("--skip-import", action="store_true")
        ap.add_argument("--only-import", action="store_true")
        a = ap.parse_args()
        OUT.mkdir(parents=True, exist_ok=True)
        if not a.only_import:
            cmd, env = compose("thesis-bench", a.scale)
            measure = (ROOT / "bench" / "measure.py").read_text().replace("asyncio.run(main())", "")
            src = measure + "\n\n" + (ROOT / "bench" / "planner.py").read_text()
            raw = sh(*cmd, "exec", "-T", "-e", "PLANNER_IN_CONTAINER=1", "app", "python", "-",
                     json.dumps({"runs": a.runs}), env=env, input=src)
            res = json.loads(raw)
            (OUT / f"planner_{a.scale}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
            write_plan_cache(res, a.scale)
            write_opinions(res["opinions"], a.scale)
            print("zapisano", OUT)
        if not a.skip_import:
            import_test(a.scale)
            print("zapisano", OUT / "import_neo4j.txt")

    if __name__ == "__main__":
        main()
