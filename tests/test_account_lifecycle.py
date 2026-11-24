"""Cykl życia konta użytkownika (3.1, 3.2, 5.5.9, 7.2.3).

Na przykładzie studenta 285904, który w danych początkowych nie ma konta: utworzenie konta,
logowanie, dezaktywacja, odrzucenie wcześniej wydanego tokenu, aktywacja, usunięcie konta oraz
sprawdzenie, że dane osoby pozostają w bazie. Na końcu administrator próbuje usunąć własne konto.

Operacje administratora wykonywane są tokenem podpisanym w kontenerze app dla administratora
z danych początkowych. Po teście konto studenta jest usunięte (stan jak w danych początkowych).

Uruchomienie:
    python tests/test_account_lifecycle.py [--out wynik.md]
"""

import argparse
from pathlib import Path

from common import detail, finish, in_app, ok, request, table

STUDENT = "285904"
EMAIL = "285904@student.pwr.edu.pl"
PASSWORD = "test-haslo-285904"

_FIXTURE = r'''
async def main(args):
    if args["cmd"] == "teardown":
        await q("MATCH (u:User {idx: $idx}) REMOVE u:User:Inactive, u.email, u.passwd_hash, u.deactivated_at", idx=args["idx"])
        return {}
    state = (await q("MATCH (p:Person {idx: $idx}) RETURN p:User AS user", idx=args["idx"]))[0]
    admin = (await q("MATCH (a:Admin:User) RETURN a.idx AS idx ORDER BY a.idx LIMIT 1"))[0]["idx"]
    return {"has_account": state["user"], "admin_idx": admin, "admin": token(admin, ["Admin"])}
'''


def login() -> tuple[int, object]:
    return request("POST", "/login", body={"email": EMAIL, "password": PASSWORD})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    f = in_app(_FIXTURE, cmd="setup", idx=STUDENT)
    if f["has_account"]:
        raise SystemExit(f"Student {STUDENT} ma już konto - test zakłada stan z danych początkowych.")
    adm = f["admin"]
    rows, errors = [], []

    def step(name, result, expected_code, expected_detail=None):
        code, body = result
        msg = detail(body)
        good = code == expected_code and (expected_detail is None or msg == expected_detail)
        shown = "token" if isinstance(body, dict) and "token" in body else msg
        rows.append([name, f"{expected_code} {expected_detail or ''}".strip(), f"{code} {shown}".strip(), ok(good)])
        if not good:
            errors.append(f"{name}: {code} {msg} (oczekiwano {expected_code} {expected_detail or ''})")
        return body

    try:
        step("`POST /admin/users` - utworzenie konta", request(
            "POST", "/admin/users", adm, {"email": EMAIL, "passwd": PASSWORD, "idx": STUDENT}), 201)
        old = step("`POST /login`", login(), 200)
        old_token = old.get("token") if isinstance(old, dict) else None
        step("token studenta: `GET /me/enrolments`", request("GET", "/me/enrolments", old_token), 200)
        step('`PATCH /admin/users/285904` z `{"active": false}`',
             request("PATCH", f"/admin/users/{STUDENT}", adm, {"active": False}), 200)
        step("`POST /login`", login(), 403, "Account inactive")
        step("żądanie z tokenem wydanym przed dezaktywacją", request("GET", "/me/enrolments", old_token), 401, "Token revoked")
        step('`PATCH /admin/users/285904` z `{"active": true}`',
             request("PATCH", f"/admin/users/{STUDENT}", adm, {"active": True}), 200)
        step("`POST /login`", login(), 200)
        step("`DELETE /admin/users/285904`", request("DELETE", f"/admin/users/{STUDENT}", adm), 204)
        step("`POST /login`", login(), 401, "Invalid email or password")
        person = step("`GET /students/285904` (administrator) - dane osoby", request("GET", f"/students/{STUDENT}", adm), 200)
        if isinstance(person, dict) and person.get("idx") != STUDENT:
            errors.append("dane osoby nie zostały zwrócone")
        step(f"`DELETE /admin/users/{f['admin_idx']}` (własne konto administratora)",
             request("DELETE", f"/admin/users/{f['admin_idx']}", adm), 409, "Cannot remove your own account")
    finally:
        in_app(_FIXTURE, cmd="teardown", idx=STUDENT)
    finish(table(["Krok", "Oczekiwano", "Odpowiedź", "Zgodny"], rows), errors, args.out)


if __name__ == "__main__":
    main()
