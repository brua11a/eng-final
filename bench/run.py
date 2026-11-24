"""Porównanie wydajności backendów grafowego i relacyjnego w kilku skalach danych.

Dla każdej skali skrypt:
  1. uruchamia osobny projekt Docker Compose ("thesis-bench") na pustych wolumenach, z danymi
     początkowymi (skala "seed") albo wygenerowanymi przez bench/generate.py,
  2. mierzy czas uruchomienia (import danych do obu baz),
  3. uruchamia w kontenerze app bench/measure.py: warstwy engine, driver i asgi oraz diagnostykę zapytań,
  4. mierzy z hosta warstwy HTTP: bezpośrednio do API (https) i przez nginx (nginx),
  5. odczytuje rozmiar obu baz na dysku,
  6. usuwa projekt razem z wolumenami.
Główne środowisko jest na czas pomiarów zatrzymywane (te same porty) i na końcu uruchamiane ponownie.

Wyniki (format długi, gotowy do pandas/matplotlib) - bench/results/:
  samples.csv    - scale, students, endpoint, backend, layer, run, ms         (wszystkie pomiary)
  queries.csv    - scale, students, endpoint, backend, query_no, metryki zapytania z PROFILE/EXPLAIN
  operators.csv  - scale, students, endpoint, backend, query_no, operator, count
  storage.csv    - scale, students, backend, metric, value
  params_<skala>.json - parametry żądań i treść zapytań
Ponowne uruchomienie dla danej skali zastępuje jej wiersze, pozostałe skale zostają.

Uruchomienie:
    python bench/generate.py 1000 3000 10000
    python bench/run.py seed 1000 3000 10000 [--runs 50]
    python bench/plots.py
"""

import argparse
import csv
import http.client
import json
import os
import ssl
import statistics
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "bench" / "results"
PROJECT = "thesis-bench"
CTX = ssl.create_default_context(cafile=str(ROOT / "certificates" / "ca.pem"))
PREFIX = {"neo4j": "/api", "postgres": "/api/rel"}
HTTP_LAYERS = {"https": 8000, "nginx": 5173}


def sh(*cmd, env=None, check=True, input=None, timeout=3600) -> str:
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env, input=input, timeout=timeout)
    if check and out.returncode:
        raise RuntimeError(f"{' '.join(cmd)}\n{out.stderr[-2000:]}")
    return out.stdout


def compose_cmd(scale: str) -> tuple[list[str], dict]:
    env = dict(os.environ)
    files = ["-f", "docker-compose.yml"]
    if scale != "seed":
        env["BENCH_DATA"] = str(ROOT / "bench" / "data" / scale)
        files += ["-f", "bench/docker-compose.bench.yml"]
    return ["docker", "compose", "-p", PROJECT, *files], env


def wait_ready(limit: int = 1800) -> float:
    start = time.time()
    while time.time() - start < limit:
        try:
            conn = http.client.HTTPSConnection("localhost", 5173, context=CTX, timeout=5)
            conn.request("GET", "/api/openapi.json")
            if conn.getresponse().status == 200:
                return time.time() - start
        except OSError:
            pass
        time.sleep(2)
    raise TimeoutError("API nie wystartowało")


def http_layer(port: int, ep: dict, backend: str, runs: int, warmup: int) -> list[float]:
    conn = http.client.HTTPSConnection("localhost", port, context=CTX)
    headers = {"Accept": "application/json"}
    if ep["token"]:
        headers["Authorization"] = f"Bearer {ep['token']}"
    body = json.dumps(ep["body"]) if ep["body"] is not None else None
    if body:
        headers["Content-Type"] = "application/json"
    times = []
    for i in range(warmup + runs):
        t0 = time.perf_counter()
        conn.request(ep["method"], PREFIX[backend] + ep["path"], body=body, headers=headers)
        res = conn.getresponse()
        res.read()
        dt = (time.perf_counter() - t0) * 1000
        if res.status >= 400:
            raise RuntimeError(f"{backend} {ep['name']} :{port} -> {res.status}")
        if i >= warmup:
            times.append(dt)
    conn.close()
    return times


def dotenv() -> dict:
    pairs = (line.split("=", 1) for line in (ROOT / ".env").read_text().splitlines() if "=" in line and not line.startswith("#"))
    return {k.strip(): v.strip() for k, v in pairs}


def checkpoint(cmd: list[str], env: dict) -> None:
    """Punkt kontrolny w obu bazach (konta administratorów baz).

    Po imporcie dane są w dzienniku transakcji. Wykonany przed pomiarami punkt kontrolny zapisuje je
    do plików magazynu od razu, zamiast w tle w trakcie pomiarów: bez tego przy 10 000 studentów
    zapisy na dysk spowalniały zatwierdzanie transakcji (fsync) w obu bazach w pierwszych mierzonych
    warstwach. Przed odczytem rozmiaru baz zapewnia, że rozmiar plików odpowiada danym."""
    e = dotenv()
    sh(*cmd, "exec", "-T", "-e", f"ADMIN_USER={e['NEO4J_USER']}", "-e", f"ADMIN_PASSWORD={e['NEO4J_PASSWORD']}",
       "app", "python", "-c",
       "import os\nfrom neo4j import GraphDatabase\n"
       "with GraphDatabase.driver(os.environ['NEO4J_URI'], auth=(os.environ['ADMIN_USER'], os.environ['ADMIN_PASSWORD'])) as d:\n"
       "    d.execute_query('CALL db.checkpoint()')", env=env)
    sh(*cmd, "exec", "-T", "-u", "postgres", "postgres", "psql", "-d", "usos", "-c", "CHECKPOINT", env=env)


def storage(cmd: list[str], env: dict) -> dict:
    checkpoint(cmd, env)
    neo = sh(*cmd, "exec", "-T", "neo4j", "du", "-sb", "/data/databases/neo4j", "/data/transactions/neo4j", env=env)
    sizes = [int(line.split()[0]) for line in neo.splitlines()]
    pg = sh(*cmd, "exec", "-T", "-u", "postgres", "postgres", "psql", "-d", "usos", "-tAc",
            "SELECT pg_database_size('usos'), (SELECT sum(pg_indexes_size(c.oid)) FROM pg_class c "
            "JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relkind = 'r')", env=env)
    db, idx = (int(x) for x in pg.strip().split("|"))
    counts = sh(*cmd, "exec", "-T", "app", "python", "-c",
                "import asyncio\nfrom app.graph_backend.database import driver\n"
                "async def m():\n"
                "    async with driver.session() as s:\n"
                "        n = (await (await s.run('MATCH (n) RETURN count(n) AS n')).single())['n']\n"
                "        r = (await (await s.run('MATCH ()-[r]->() RETURN count(r) AS n')).single())['n']\n"
                "    await driver.close(); print(n, r)\n"
                "asyncio.run(m())", env=env).split()
    return {"neo4j": {"store_bytes": sizes[0], "tx_log_bytes": sizes[1], "nodes": int(counts[0]),
                      "relationships": int(counts[1])},
            "postgres": {"database_bytes": db, "index_bytes": idx}}


def replace_rows(name: str, scale: str, rows: list[dict]) -> None:
    path = OUT / name
    old = []
    if path.exists():
        with open(path, newline="") as f:
            old = [r for r in csv.DictReader(f) if r["scale"] != scale]
    allrows = old + rows
    fields = list(dict.fromkeys(k for r in allrows for k in r))
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(allrows)


def bench_scale(scale: str, runs: int, warmup: int) -> None:
    cmd, env = compose_cmd(scale)
    sh(*cmd, "down", "-v", "--remove-orphans", env=env, check=False)
    t0 = time.time()
    sh(*cmd, "up", "-d", "--build", env=env)
    wait_ready()
    ready = time.time() - t0  # `up` czeka na init i test stanu baz, więc liczone od początku
    init = json.loads(sh("docker", "inspect", sh(*cmd, "ps", "-a", "-q", "init", env=env).strip()))[0]["State"]
    print(f"[{scale}] gotowe po {ready:.0f} s", file=sys.stderr)
    try:
        checkpoint(cmd, env)
        time.sleep(5)
        raw = sh(*cmd, "exec", "-T", "app", "python", "-",
                 json.dumps({"runs": runs, "warmup": warmup, "login_runs": max(5, runs // 5), "global_warmup": 200}),
                 env=env, input=(ROOT / "bench" / "measure.py").read_text())
        m = json.loads(raw)
        for ep in m["endpoints"]:
            n = max(5, runs // 5) if ep["name"] == "POST /login" else runs
            for backend in PREFIX:
                for layer, port in HTTP_LAYERS.items():
                    m["samples"].append({"endpoint": ep["name"], "backend": backend, "layer": layer,
                                         "ms": http_layer(port, ep, backend, n, warmup)})
            print(f"[{scale}] HTTP {ep['name']}", file=sys.stderr)
        st = storage(cmd, env)
        pg_import = pg_import_seconds(cmd, env)
    finally:
        sh(*cmd, "down", "-v", "--remove-orphans", env=env, check=False)

    students = sum(1 for _ in open((ROOT / "import" if scale == "seed" else ROOT / "bench" / "data" / scale / "import")
                                   / "nodes" / "students.csv")) - 1
    base = {"scale": scale, "students": students}
    replace_rows("samples.csv", scale, [
        {**base, "endpoint": s["endpoint"], "backend": s["backend"], "layer": s["layer"], "run": i, "ms": round(v, 4)}
        for s in m["samples"] for i, v in enumerate(s["ms"])])
    metric_keys = ["rows", "engine_ms", "planning_ms", "work", "cache_hits", "cache_misses", "memory_bytes",
                   "estimate_error", "jit", "available_after_ms", "consumed_after_ms", "serialized_bytes", "response_bytes",
                   "chars", "relationship_patterns", "match_clauses", "joins", "selects"]
    replace_rows("queries.csv", scale, [
        {**base, "endpoint": q["endpoint"], "backend": q["backend"], "query_no": q["query_no"],
         **{k: q.get(k, "") for k in metric_keys}} for q in m["queries"]])
    replace_rows("operators.csv", scale, [
        {**base, "endpoint": q["endpoint"], "backend": q["backend"], "query_no": q["query_no"], "operator": op, "count": c}
        for q in m["queries"] for op, c in Counter(q["operators"]).items()])
    storage_rows = [{**base, "backend": b, "metric": k, "value": v} for b, d in st.items() for k, v in d.items()]
    storage_rows.append({**base, "backend": "both", "metric": "startup_s", "value": round(ready, 1)})
    storage_rows.append({**base, "backend": "neo4j", "metric": "import_s", "value": round(
        _seconds(init["FinishedAt"]) - _seconds(init["StartedAt"]), 1)})
    storage_rows.append({**base, "backend": "postgres", "metric": "import_s", "value": pg_import})
    replace_rows("storage.csv", scale, storage_rows)
    (OUT / f"params_{scale}.json").write_text(json.dumps(
        {"params": m["params"], "runs": runs, "warmup": warmup,
         "queries": [{k: q[k] for k in ("endpoint", "backend", "query_no", "query")} for q in m["queries"]]},
        ensure_ascii=False, indent=1))
    print(f"[{scale}] zapisano ({time.time() - t0:.0f} s)", file=sys.stderr)


def pg_import_seconds(cmd: list[str], env: dict) -> float:
    """Czas skryptów inicjalizacyjnych obrazu PostgreSQL: od uruchomienia tymczasowego serwera
    do komunikatu o zakończeniu inicjalizacji (znaczniki czasu z dziennika kontenera)."""
    log = sh(*cmd, "logs", "-t", "postgres", env=env).splitlines()
    start = next(line for line in log if "running /docker-entrypoint-initdb.d/01_schema.sql" in line)
    end = next(line for line in log if "PostgreSQL init process complete" in line)
    stamp = lambda line: _seconds(line.split("|", 1)[1].strip().split()[0])
    return round(stamp(end) - stamp(start), 1)


def _seconds(ts: str) -> float:
    from datetime import datetime
    return datetime.fromisoformat(ts[:26].rstrip("Z") + "+00:00").timestamp()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("scales", nargs="+", help='"seed" lub liczba studentów (dane z bench/generate.py)')
    parser.add_argument("--runs", type=int, default=50)
    parser.add_argument("--warmup", type=int, default=10)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    for scale in args.scales:
        if scale != "seed" and not (ROOT / "bench" / "data" / scale).exists():
            raise SystemExit(f"brak danych bench/data/{scale} - uruchom: python bench/generate.py {scale}")
    running = sh("docker", "compose", "ps", "--services", "--status", "running").split()
    if running:
        sh("docker", "compose", "stop")
    try:
        for scale in args.scales:
            bench_scale(scale, args.runs, args.warmup)
    finally:
        if running:
            sh("docker", "compose", "up", "-d")


if __name__ == "__main__":
    main()
