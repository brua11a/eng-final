"""Odebranie roli a wcześniej wydany token (4.4.1, 5.5.6, 5.5.10, 7.2.4).

Student 279413 otrzymuje rolę Admin, loguje się (token z rolą Admin), po czym inny administrator
odbiera mu tę rolę. Stary token musi zostać odrzucony (401 "Token revoked") zarówno przy odczycie,
jak i przy operacji zmieniającej dane; po ponownym zalogowaniu token nie zawiera już roli Admin.

Operacja na cudzym koncie (dezaktywacja 281056) wykonywana jest tylko starym tokenem, który powinien
zostać odrzucony; gdyby jednak przeszła, konto jest na końcu ponownie aktywowane.

Uruchomienie:
    python tests/test_role_revocation.py [--out wynik.md]
"""

import argparse
from pathlib import Path

from common import detail, finish, in_app, ok, request, table

STUDENT = "279413"
LOGIN = {"email": "279413@student.pwr.edu.pl", "password": "student123"}
VICTIM = "281056"

_FIXTURE = r'''
async def main(args):
    if args["cmd"] == "teardown":
        await q("MATCH (p:Person {idx: $idx}) REMOVE p:Admin", idx=args["idx"])
        await q("MATCH (u:User {idx: $v}) REMOVE u:Inactive, u.deactivated_at", v=args["victim"])
        return {}
    state = (await q("MATCH (p:Person {idx: $idx}) RETURN p:Admin AS admin", idx=args["idx"]))[0]
    admin = (await q("MATCH (a:Admin) WHERE a.idx <> $idx RETURN a.idx AS idx LIMIT 1", idx=args["idx"]))[0]["idx"]
    return {"was_admin": state["admin"], "admin": token(admin, ["Admin"])}
'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    f = in_app(_FIXTURE, cmd="setup", idx=STUDENT, victim=VICTIM)
    if f["was_admin"]:
        raise SystemExit(f"{STUDENT} ma już rolę Admin - test zakłada stan z danych początkowych.")
    adm = f["admin"]
    rows, errors = [], []

    def step(name, result, expected_code, expected_detail=None):
        code, body = result
        msg = detail(body)
        good = code == expected_code and (expected_detail is None or msg == expected_detail)
        rows.append([name, f"{expected_code} {expected_detail or ''}".strip(), f"{code} {msg}".strip(), ok(good)])
        if not good:
            errors.append(f"{name}: {code} {msg} (oczekiwano {expected_code} {expected_detail or ''})")
        return body

    try:
        step("nadanie roli: `PUT /admin/users/279413/roles/Admin`",
             request("PUT", f"/admin/users/{STUDENT}/roles/Admin", adm, {}), 200)
        res = step("logowanie studenta", request("POST", "/login", body=LOGIN), 200)
        old = res["token"]
        roles_before = res["roles"]
        step("`GET /admin/people/next-idx` przed odebraniem roli", request("GET", "/admin/people/next-idx", old), 200)
        step("odebranie roli: `DELETE /admin/users/279413/roles/Admin`",
             request("DELETE", f"/admin/users/{STUDENT}/roles/Admin", adm), 200)
        step("`GET /admin/people/next-idx` po odebraniu roli, stary token",
             request("GET", "/admin/people/next-idx", old), 401, "Token revoked")
        step(f'`PATCH /admin/users/{VICTIM}` z `{{"active": false}}`, stary token',
             request("PATCH", f"/admin/users/{VICTIM}", old, {"active": False}), 401, "Token revoked")
        res = step("ponowne logowanie", request("POST", "/login", body=LOGIN), 200)
        roles_after = res["roles"]
        step("`GET /admin/people/next-idx`, nowy token", request("GET", "/admin/people/next-idx", res["token"]), 403)
        if "Admin" not in roles_before or "Admin" in roles_after:
            errors.append(f"role w tokenach: przed {roles_before}, po {roles_after}")
    finally:
        in_app(_FIXTURE, cmd="teardown", idx=STUDENT, victim=VICTIM)
    md = "\n\n".join([
        table(["Krok", "Oczekiwano", "Odpowiedź", "Zgodny"], rows),
        f"Role w tokenie: przed odebraniem {roles_before}, po ponownym logowaniu {roles_after}.",
    ])
    finish(md, errors, args.out)


if __name__ == "__main__":
    main()
