"""Macierz uprawnień (3.4): RBAC dla wszystkich punktów końcowych i wybrane reguły ReBAC.

Część A (RBAC). Lista punktów końcowych backendu grafowego pochodzi z dokumentacji OpenAPI
(`/api/openapi.json`), więc nowy punkt końcowy bez przypisanych ról w tym skrypcie kończy test
błędem. Każdy jest wywoływany:
  - bez tokenu                      -> oczekiwane 401,
  - jako student, prowadzący, administrator oraz osoba z rolami Student i Teacher jednocześnie
                                     -> rola niedozwolona: 403 "Forbidden",
                                        rola dozwolona: inna odpowiedź niż 401 i 403 "Forbidden".
Żądania osób z rolą dozwoloną nie zmieniają danych: treść żądania jest niepoprawna (422 - walidacja
następuje po sprawdzeniu roli, 7.2.2), a identyfikatory w ścieżce wskazują nieistniejące zasoby (404)
albo zasoby, do których osoba ma dostęp (200).

Część B (ReBAC). Żądania z poprawną treścią, w których rola jest dozwolona, a o wyniku decyduje
powiązanie użytkownika z zasobem w grafie (4.4.2).

Tokeny są podpisywane kluczem API w kontenerze app dla osób z danych początkowych. Na czas testu
student 279413 otrzymuje dodatkowo etykietę Teacher i krawędź TEACHES (osoba z dwiema rolami);
zmiany są cofane po teście.

Uruchomienie:
    python tests/test_permissions.py [--out wynik.md]
"""

import argparse
from pathlib import Path

from common import API, detail, finish, in_app, ok, request, table

S, T, A, ST = "student", "prowadzący", "administrator", "student i prowadzący"
CALLERS = [S, T, A, ST]
ROLES = {S: {"Student"}, T: {"Teacher"}, A: {"Admin"}, ST: {"Student", "Teacher"}}

STUDENT_IDX = "279413"

_FIXTURE = r'''
async def main(args):
    if args["cmd"] == "teardown":
        await q("""MATCH (p:Person {idx: $idx}) OPTIONAL MATCH (p)-[r:TEACHES]->(:Group {id: $g})
                   DELETE r REMOVE p:Teacher, p.degree, p.working_since""", idx=args["student"], g=args["g_own"])
        return {}
    st = args["student"]
    # Prowadzący z grupą, w której są zapisani studenci (inni niż st), i grupa, której nie prowadzi.
    own = (await q("""
        MATCH (t:Teacher)-[:TEACHES]->(g:Group)<-[:REGISTERED_IN]-(x:Student)
        WHERE NOT t:Student AND x.idx <> $st
        RETURN t.idx AS teacher, g.id AS g_own, x.idx AS taught ORDER BY t.idx, g.id LIMIT 1""", st=st))[0]
    foreign = (await q("""
        MATCH (g:Group)<-[:REGISTERED_IN]-(x:Student)
        WHERE NOT EXISTS { (:Teacher {idx: $t})-[:TEACHES]->(g) }
        RETURN g.id AS g_foreign, x.idx AS in_foreign LIMIT 1""", t=own["teacher"]))[0]
    untaught = (await q("""
        MATCH (x:Student) WHERE x.idx <> $st
          AND NOT EXISTS { (:Teacher {idx: $t})-[:TEACHES]->(:Group)<-[:REGISTERED_IN]-(x) }
        RETURN x.idx AS untaught LIMIT 1""", t=own["teacher"], st=st))[0]
    regs = (await q("""
        MATCH (reg:Registration)
        RETURN reg.id AS id, EXISTS { (:Student {idx: $st})-[:ASSIGNED]->(:RegistrationTurn)<-[:HAS_TURN]-(reg) } AS mine""",
        st=st))
    cycles = (await q("""
        MATCH (ac:AcademicCycle)
        RETURN ac.id AS id, EXISTS { (:Student {idx: $st})-[:ENROLLED]->(:CurriculumTerm)-[:TAUGHT_IN]->(ac) } AS mine""",
        st=st))
    not_registered = (await q("""
        MATCH (t:Teacher)-[:TEACHES]->(g:Group) WHERE NOT EXISTS { (:Student {idx: $st})-[:REGISTERED_IN]->(g) }
        RETURN g.id AS g, t.idx AS t LIMIT 1""", st=st))[0]
    subject = (await q("""
        MATCH (su:Subject)<-[:INSTANCE_OF]-(si)-[:OFFERED_IN]->(ac:AcademicCycle), (si)-[:HAS_TYPE]->()<-[:OF_TYPE]-(:Group)
        RETURN su.code AS code, ac.id AS cycle LIMIT 1"""))[0]
    admin = (await q("MATCH (a:Admin) RETURN a.idx AS idx ORDER BY a.idx LIMIT 1"))[0]["idx"]
    # Osoba z dwiema rolami: student st dostaje na czas testu etykietę Teacher i grupę g_own.
    await q("""MATCH (p:Person {idx: $st}), (g:Group {id: $g})
               SET p:Teacher, p.degree = 'mgr', p.working_since = date() MERGE (p)-[:TEACHES]->(g)""",
            st=st, g=own["g_own"])
    return {
        **own, **foreign, **untaught, "admin": admin,
        "reg_mine": next(r["id"] for r in regs if r["mine"]),
        "reg_other": next(r["id"] for r in regs if not r["mine"]),
        "cycle_mine": next(c["id"] for c in cycles if c["mine"]),
        "cycle_other": next(c["id"] for c in cycles if not c["mine"]),
        "g_not_registered": not_registered["g"], "t_not_registered": not_registered["t"],
        "subject": subject["code"], "subject_cycle": subject["cycle"],
        "tokens": {
            "student": token(st, ["Student"]),
            "prowadzący": token(own["teacher"], ["Teacher"]),
            "administrator": token(admin, ["Admin"]),
            "student i prowadzący": token(st, ["Teacher", "Student"]),
        },
    }
'''


def allowed_roles(method: str, path: str) -> set[str]:
    """Role dopuszczone do punktu końcowego według macierzy uprawnień (tabele 3.1-3.3)."""
    p = path.removeprefix("/api")
    if p.startswith("/admin/"):
        return {"Admin"}                                   # tabela 3.3
    if p == "/me/groups":
        return {"Teacher"}                                 # lista własnych grup prowadzącego
    if p in ("/students/{student_idx}", "/groups/{group_id}/students",
             "/groups/{group_id}/students/{student_idx}/grade"):
        return {"Teacher", "Admin"}                        # tabela 3.2, funkcje prowadzącego
    if p.startswith("/me/") or (method == "POST" and p == "/opinions"):
        return {"Student"}                                 # tabela 3.2, funkcje studenta
    return {"Student", "Teacher", "Admin"}                 # tabela 3.1, katalog


def fill(path: str, caller: str, f: dict) -> str:
    """Identyfikatory w ścieżce: zasoby dostępne dla osoby albo nieistniejące (bez zmian w danych)."""
    p = path.removeprefix("/api")
    values = {
        "code": f["subject"], "subject_code": f["subject"], "group_id": f["g_own"],
        "idx": f["teacher"], "student_idx": f["taught"], "registration_id": f["reg_mine"],
        "cycle_id": f["cycle_mine"], "role": "Admin",
    }
    if p.startswith("/admin/"):
        values.update(idx="test-nonexistent", code="test-nonexistent")
    if p.startswith("/me/registered-groups"):
        values["group_id"] = f["g_not_registered"]
    for name, value in values.items():
        p = p.replace("{" + name + "}", value)
    if p.startswith("/subjects/") and p.endswith("/groups"):
        p += f"?cycle_id={f['subject_cycle']}"
    if p.endswith("/groups") and p.startswith("/me/registrations/"):
        p += f"?subject_code={f['subject']}"
    if p == "/opinions":
        p += f"?teacher_idx={f['teacher']}"
    return p


def body_for(method: str, path: str):
    if method in ("POST", "PUT", "PATCH") and path.endswith("/grade"):
        return {"grade": 4.2}  # spoza skali: 422 bez zapisu
    return {} if method in ("POST", "PUT", "PATCH") else None


def passed_rbac(code: int, body) -> bool:
    return code != 401 and not (code == 403 and detail(body) == "Forbidden")


def part_a(f: dict) -> tuple[list[list], list[str]]:
    status, spec = request("GET", "/openapi.json")
    assert status == 200, "brak /api/openapi.json"
    rows, errors = [], []
    for path, ops in spec["paths"].items():
        if path.startswith("/api/rel"):
            continue  # backend relacyjny: rozdział 6
        for method in ops:
            method = method.upper()
            allowed = allowed_roles(method, path)
            body = None if path == "/api/login" else body_for(method, path)
            cells = []
            code, res = request(method, fill(path, S, f), None, body if path != "/api/login" else {})
            expected_none = 422 if path == "/api/login" else 401
            cells.append(f"{code}{'' if code == expected_none else ' ✗'}")
            if code != expected_none:
                errors.append(f"{method} {path} bez tokenu: {code}")
            if path == "/api/login":
                rows.append([f"`{method} {path.removeprefix('/api')}`", "wszyscy", cells[0], "–", "–", "–", "–"])
                continue
            for caller in CALLERS:
                code, res = request(method, fill(path, caller, f), f["tokens"][caller], body)
                should = bool(ROLES[caller] & allowed)
                good = passed_rbac(code, res) if should else (code == 403 and detail(res) == "Forbidden")
                cells.append(f"{code}{'' if good else ' ✗'}")
                if not good:
                    errors.append(f"{method} {path} jako {caller}: {code} {detail(res)} (oczekiwano "
                                  f"{'dostępu' if should else '403'})")
            rows.append([f"`{method} {path.removeprefix('/api')}`", ", ".join(sorted(allowed)), *cells])
    return rows, errors


def part_b(f: dict) -> tuple[list[list], list[str]]:
    tok = f["tokens"]
    cases = [
        # (opis, osoba, metoda, ścieżka, treść, oczekiwany kod)
        ("prowadzący: studenci własnej grupy", T, "GET", f"/groups/{f['g_own']}/students", None, 200),
        ("prowadzący: studenci cudzej grupy", T, "GET", f"/groups/{f['g_foreign']}/students", None, 403),
        ("prowadzący: ocena w cudzej grupie", T, "PUT",
         f"/groups/{f['g_foreign']}/students/{f['in_foreign']}/grade", {"grade": 4.0}, 403),
        ("prowadzący: szczegóły swojego studenta", T, "GET", f"/students/{f['taught']}", None, 200),
        ("prowadzący: szczegóły studenta, którego nie uczy", T, "GET", f"/students/{f['untaught']}", None, 403),
        ("administrator: studenci dowolnej grupy", A, "GET", f"/groups/{f['g_foreign']}/students", None, 200),
        ("administrator: szczegóły dowolnego studenta", A, "GET", f"/students/{f['untaught']}", None, 200),
        ("student: szczegóły innego studenta", S, "GET", f"/students/{f['taught']}", None, 403),
        ("student: przedmioty we własnych zapisach", S, "GET", f"/me/registrations/{f['reg_mine']}/subjects", None, 200),
        ("student: przedmioty w cudzych zapisach", S, "GET", f"/me/registrations/{f['reg_other']}/subjects", None, 403),
        ("student: własny semestr", S, "GET", f"/me/academic-cycles/{f['cycle_mine']}", None, 200),
        ("student: cykl, w którym nie studiował", S, "GET", f"/me/academic-cycles/{f['cycle_other']}", None, 403),
        ("student: opinia o grupie, do której nie należy", S, "POST", "/opinions",
         {"group_id": f["g_not_registered"], "teacher_idx": f["t_not_registered"], "grade": 4.0}, 403),
        ("student i prowadzący: studenci własnej grupy", ST, "GET", f"/groups/{f['g_own']}/students", None, 200),
        ("student i prowadzący: własne zapisy", ST, "GET", f"/me/registrations/{f['reg_mine']}/subjects", None, 200),
        ("student i prowadzący: studenci cudzej grupy", ST, "GET", f"/groups/{f['g_foreign']}/students", None, 403),
    ]
    # W tabeli identyfikatory zastąpione nazwami z fixture, np. /groups/{g_foreign}/students.
    names = {v: k for k, v in f.items() if isinstance(v, str)}
    shown = lambda p: "/".join("{" + names[s] + "}" if s in names else s for s in p.split("/"))
    rows, errors = [], []
    for name, caller, method, path, body, expected in cases:
        code, res = request(method, path, tok[caller], body)
        rows.append([name, f"`{method} {shown(path)}`", expected, code, ok(code == expected)])
        if code != expected:
            errors.append(f"ReBAC {name}: {code} {detail(res)} (oczekiwano {expected})")
    return rows, errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    f = in_app(_FIXTURE, cmd="setup", student=STUDENT_IDX)
    try:
        rows_a, err_a = part_a(f)
        rows_b, err_b = part_b(f)
    finally:
        in_app(_FIXTURE, cmd="teardown", student=STUDENT_IDX, g_own=f["g_own"])
    md = "\n\n".join([
        f"API: {API}. ✗ oznacza wynik niezgodny z macierzą uprawnień.",
        "## A. Role (RBAC)",
        table(["Punkt końcowy", "Dozwolone role", "Bez tokenu", *CALLERS], rows_a),
        f"Punktów końcowych: {len(rows_a)}, żądań: {len(rows_a) * 5 - 4}.",
        "## B. Relacje (ReBAC)",
        table(["Przypadek", "Żądanie", "Oczekiwano", "Kod", "Zgodny"], rows_b),
    ])
    finish(md, err_a + err_b, args.out)


if __name__ == "__main__":
    main()
