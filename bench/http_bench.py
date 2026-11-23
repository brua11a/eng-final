"""End-to-end latency of the compared endpoints, graph (/api) vs relational (/api/rel).

Measures what the client sees: TLS, FastAPI, validation, database and serialisation together.
Requests are sent sequentially over one keep-alive connection per backend.

    python bench/http_bench.py [runs]  > bench/results/http_bench.json
"""

import http.client
import json
import ssl
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from compare import ACCOUNTS, CTX, call, login  # noqa: E402

RUNS = int(sys.argv[1]) if len(sys.argv) > 1 else 200
WARMUP = 20


def measure(conn: http.client.HTTPSConnection, method: str, path: str, token: str | None, body: dict | None, runs: int) -> list[float]:
    data = json.dumps(body) if body is not None else None
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data:
        headers["Content-Type"] = "application/json"
    times = []
    for i in range(WARMUP + runs):
        t0 = time.perf_counter()
        conn.request(method, path, body=data, headers=headers)
        res = conn.getresponse()
        res.read()
        dt = (time.perf_counter() - t0) * 1000
        if res.status >= 500:
            raise RuntimeError(f"{method} {path}: {res.status}")
        if i >= WARMUP:
            times.append(dt)
    return times


def stats(times: list[float]) -> dict:
    return {"median_ms": statistics.median(times), "p95_ms": statistics.quantiles(times, n=20)[18]}


def main() -> None:
    st, te, ad = (login(w) for w in ("student", "teacher", "admin"))
    _, regs = call("GET", "/me/registrations", st)
    reg_id = regs["available_registrations"][0]["id"]
    _, courses = call("GET", f"/me/registrations/{reg_id}/subjects", st)
    subject_code = courses["courses"][0]["id"]
    _, groups = call("GET", "/me/groups", te)
    group_id = groups["groups"][0]["group_id"]
    _, students = call("GET", f"/groups/{group_id}/students", te)
    student_idx = students["students"][0]["idx"] if students["students"] else "279413"

    endpoints = [
        ("POST /login", "POST", "/login", None, {"email": ACCOUNTS["student"][0], "password": "student123"}),
        ("GET /opinions", "GET", "/opinions?teacher_idx=T008", st, None),
        ("GET /groups/{id}/students", "GET", f"/groups/{group_id}/students", te, None),
        ("GET /me/registrations/{id}/groups", "GET", f"/me/registrations/{reg_id}/groups?subject_code={subject_code}", st, None),
        ("GET /students/{idx}", "GET", f"/students/{student_idx}", ad, None),
        ("GET /subjects", "GET", "/subjects", st, None),
        ("PUT .../grade", "PUT", f"/groups/{group_id}/students/{student_idx}/grade", te, {"grade": 4.0}),
    ]
    out = []
    for name, method, path, token, body in endpoints:
        runs = 20 if name == "POST /login" else RUNS  # bcrypt: ~180 ms per request
        row = {"endpoint": name}
        for backend, prefix in (("neo4j", "/api"), ("postgres", "/api/rel")):
            conn = http.client.HTTPSConnection("localhost", 8000, context=CTX)
            row[backend] = stats(measure(conn, method, prefix + path, token, body, runs))
            conn.close()
        out.append(row)
        print(f"{name}: neo4j {row['neo4j']['median_ms']:.2f} ms, postgres {row['postgres']['median_ms']:.2f} ms", file=sys.stderr)
    json.dump({"runs": RUNS, "results": out}, sys.stdout, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
