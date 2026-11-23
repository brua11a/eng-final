"""Checks that the relational backend returns the same responses as the graph one.

Every compared endpoint is called on /api/... (Neo4j) and on /api/rel/... (PostgreSQL)
with the same token; the JSON bodies and status codes must be equal.

    python bench/compare.py
"""

import json
import re
import ssl
from datetime import datetime, timezone
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://localhost:8000/api"
CTX = ssl.create_default_context(cafile=str(ROOT / "certificates" / "ca.pem"))

ACCOUNTS = {
    "student": ("279413@student.pwr.edu.pl", "student123"),
    "teacher": ("tomasz.szandala@pwr.edu.pl", "teacher123"),
    "admin": ("admin@pwr.edu.pl", "admin"),
}


def call(method: str, path: str, token: str | None = None, body: dict | None = None) -> tuple[int, object]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Accept", "application/json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, context=CTX) as res:
            raw = res.read()
            return res.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, json.loads(raw) if raw else None


def login(who: str) -> str:
    email, password = ACCOUNTS[who]
    status, body = call("POST", "/login", body={"email": email, "password": password})
    assert status == 200, (who, status, body)
    return body["token"]


ISO_DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})$")


def normalise(body: object) -> object:
    # Tokens differ (different "exp"), everything else must be identical.
    # Neo4j keeps the original UTC offset of a ZONED DATETIME, PostgreSQL returns a timestamptz
    # in UTC: the same instant written differently, so date-times are compared as instants.
    if isinstance(body, str) and ISO_DATETIME.match(body):
        return datetime.fromisoformat(body).astimezone(timezone.utc).isoformat()
    if isinstance(body, dict):
        return {k: normalise(v) for k, v in body.items() if k != "token"}
    if isinstance(body, list):
        return [normalise(v) for v in body]
    return body


def compare(name: str, method: str, path: str, token: str | None, body: dict | None = None) -> bool:
    g = call(method, path, token, body)
    r = call(method, "/rel" + path, token, body)
    same = (g[0], normalise(g[1])) == (r[0], normalise(r[1]))
    print(f"{'OK  ' if same else 'DIFF'} {name:<40} graph={g[0]} rel={r[0]}")
    if not same:
        print("  graph:", json.dumps(g[1], ensure_ascii=False)[:600])
        print("  rel:  ", json.dumps(r[1], ensure_ascii=False)[:600])
    return same


def main() -> int:
    tokens = {who: login(who) for who in ACCOUNTS}
    st, te, ad = tokens["student"], tokens["teacher"], tokens["admin"]

    _, regs = call("GET", "/me/registrations", st)
    reg_id = regs["available_registrations"][0]["id"]
    _, courses = call("GET", f"/me/registrations/{reg_id}/subjects", st)
    subject_code = courses["courses"][0]["id"]
    _, groups = call("GET", "/me/groups", te)
    group_id = next(g["group_id"] for g in groups["groups"] if call("GET", f"/groups/{g['group_id']}/students", te)[1]["students"])
    _, students = call("GET", f"/groups/{group_id}/students", te)
    student_idx = students["students"][0]["idx"]

    results = [
        compare("POST /login (student)", "POST", "/login", None, {"email": ACCOUNTS["student"][0], "password": "student123"}),
        compare("POST /login (wrong password)", "POST", "/login", None, {"email": ACCOUNTS["student"][0], "password": "x"}),
        compare("GET /subjects", "GET", "/subjects", st),
        compare("GET /subjects?name=sieci", "GET", "/subjects?name=sieci", st),
        compare("GET /opinions?teacher_idx", "GET", "/opinions?teacher_idx=T008", st),
        compare("GET /me/registrations/{id}/groups", "GET", f"/me/registrations/{reg_id}/groups?subject_code={subject_code}", st),
        compare("GET /students/{idx} (teacher)", "GET", f"/students/{student_idx}", te),
        compare("GET /students/{idx} (admin)", "GET", "/students/279413", ad),
        compare("GET /groups/{id}/students", "GET", f"/groups/{group_id}/students", te),
        compare("GET /groups/{id}/students (forbidden)", "GET", f"/groups/{group_id}/students", st),
        # Writes go to different databases, so the same request may be compared on both.
        compare("PUT .../grade", "PUT", f"/groups/{group_id}/students/{student_idx}/grade", te, {"grade": 4.5}),
        compare("PUT .../grade (outside scale)", "PUT", f"/groups/{group_id}/students/{student_idx}/grade", te, {"grade": 4.2}),
        compare("PUT /me/registered-groups (no turn)", "PUT", f"/me/registered-groups/{group_id}", st),
    ]
    print(f"{sum(results)}/{len(results)} identical")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
