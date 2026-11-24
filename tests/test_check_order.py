"""Kolejność sprawdzeń w punkcie końcowym (5.5.8, 7.2.2).

Uwierzytelnienie (401) i rola (403) są sprawdzane przed walidacją treści żądania (422), więc
komunikaty walidacji nie są ujawniane użytkownikom bez uprawnień. To samo niepoprawne żądanie
jest wysyłane bez tokenu, z tokenem bez wymaganej roli i z tokenem z wymaganą rolą.

Żądania nie zmieniają danych: treść jest zawsze niepoprawna.

Uruchomienie:
    python tests/test_check_order.py [--out wynik.md]
"""

import argparse
from pathlib import Path

from common import detail, finish, in_app, ok, request, table

_TOKENS = r'''
async def main(args):
    g = (await q("MATCH (st:Student)-[:REGISTERED_IN]->(g:Group) RETURN g.id AS g, st.idx AS st LIMIT 1"))[0]
    admin = (await q("MATCH (a:Admin) RETURN a.idx AS idx LIMIT 1"))[0]["idx"]
    return {**g, "student": token(g["st"], ["Student"]), "admin": token(admin, ["Admin"])}
'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    t = in_app(_TOKENS)
    requests = [
        ("ocena spoza skali", "PUT", f"/groups/{t['g']}/students/{t['st']}/grade", {"grade": 4.2}),
        ("wydział bez wymaganych pól", "POST", "/admin/faculties", {"name": "W99"}),
        ("grupa z dniem tygodnia 9", "POST", "/admin/groups",
         {"g_type": "L", "number": 1, "weekday": 9, "pnp": "ALL", "capacity": 10, "start_time": "08:00",
          "end_time": "09:00", "subject_code": "x", "cycle_id": "x", "room_id": "x"}),
    ]
    callers = [("bez tokenu", None, 401), ("student", t["student"], 403), ("administrator", t["admin"], 422)]
    rows, errors = [], []
    for name, method, path, body in requests:
        for caller, token, expected in callers:
            code, res = request(method, path, token, body)
            rows.append([name, f"`{method} {path.split('/')[1]}/…`", caller, expected,
                         f"{code} {detail(res)[:70]}".strip(), ok(code == expected)])
            if code != expected:
                errors.append(f"{name} ({caller}): {code} {detail(res)} (oczekiwano {expected})")
    finish(table(["Żądanie", "Punkt końcowy", "Wywołujący", "Oczekiwano", "Odpowiedź", "Zgodny"], rows),
           errors, args.out)


if __name__ == "__main__":
    main()
