"""Odporność weryfikacji tokenów JWT na modyfikacje (4.4.1, 5.5.6).

Każdy token jest wysyłany do punktu końcowego administratora GET /api/admin/people/next-idx.
Tylko poprawny token administratora może dać 200; każdy zmodyfikowany, wygasły lub niepełny token
musi zostać odrzucony kodem 401, zanim zostanie sprawdzona rola.

Tokeny poprawnie podpisane (z kluczem API) są tworzone w kontenerze app; modyfikacje bez znajomości
klucza (zmiana treści, algorytm "none") wykonuje skrypt na hoście, tak jak atakujący.

Uruchomienie:
    python tests/test_jwt.py [--out wynik.md]
"""

import argparse
import base64
import json
from pathlib import Path

from common import detail, finish, in_app, ok, request, table

PATH = "/admin/people/next-idx"

_TOKENS = r'''
async def main(args):
    admin = (await q("MATCH (a:Admin) RETURN a.idx AS idx LIMIT 1"))[0]["idx"]
    student = (await q("MATCH (s:Student) WHERE NOT s:Admin RETURN s.idx AS idx LIMIT 1"))[0]["idx"]
    now = time.time()
    return {
        "admin": token(admin, ["Admin"]),
        "student": token(student, ["Student"]),
        "expired": token(admin, ["Admin"], exp=int(now) - 60),
        "no_exp": token(admin, ["Admin"], exp=None),
        "no_iat": token(admin, ["Admin"], iat=None),
        "no_sub": token(admin, ["Admin"], sub=None),
        "before_start": token(admin, ["Admin"], iat=now - 365 * 24 * 3600),
        "unknown_role": token(admin, ["Superuser"]),
        "no_roles": token(admin, []),
        "roles_string": token(admin, "Admin"),
        "hs512": jwt.encode({"sub": "a@test", "idx": admin, "roles": ["Admin"], "iat": now, "exp": int(now) + 600},
                            SECRET, algorithm="HS512"),
        "other_key": jwt.encode({"sub": "a@test", "idx": admin, "roles": ["Admin"], "iat": now, "exp": int(now) + 600},
                                "not-the-api-secret-but-long-enough-0123456789", algorithm="HS256"),
    }
'''


def b64(data: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(data, separators=(",", ":")).encode()).rstrip(b"=").decode()


def unb64(part: str) -> dict:
    return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    t = in_app(_TOKENS)
    header, payload, signature = t["student"].split(".")
    claims = unb64(payload)
    escalated = b64({**claims, "roles": ["Admin"]})

    cases = [
        # (opis, nagłówek Authorization, oczekiwany kod, oczekiwany komunikat)
        ("kontrola: poprawny token administratora", f"Bearer {t['admin']}", 200, None),
        ("kontrola: poprawny token studenta", f"Bearer {t['student']}", 403, "Forbidden"),
        ("token studenta z dopisaną rolą Admin, stary podpis", f"Bearer {header}.{escalated}.{signature}", 401, "Invalid token"),
        ("rola Admin, algorytm none, bez podpisu",
         f"Bearer {b64({'alg': 'none', 'typ': 'JWT'})}.{escalated}.", 401, "Invalid token"),
        ("rola Admin, podpis innym kluczem", f"Bearer {t['other_key']}", 401, "Invalid token"),
        ("podpis kluczem API, algorytm HS512", f"Bearer {t['hs512']}", 401, "Invalid token"),
        ("token wygasły (exp w przeszłości)", f"Bearer {t['expired']}", 401, "Invalid token"),
        ("token bez exp (bezterminowy)", f"Bearer {t['no_exp']}", 401, "Invalid token"),
        ("token bez iat", f"Bearer {t['no_iat']}", 401, "Invalid token"),
        ("token bez sub", f"Bearer {t['no_sub']}", 401, "Invalid token"),
        ("token wydany przed uruchomieniem API", f"Bearer {t['before_start']}", 401, "Token revoked"),
        ("nieznana rola", f"Bearer {t['unknown_role']}", 401, "Invalid token"),
        ("pusta lista ról", f"Bearer {t['no_roles']}", 401, "Invalid token"),
        ("role jako tekst zamiast listy", f"Bearer {t['roles_string']}", 401, "Invalid token"),
        ("uszkodzony token", "Bearer abc.def.ghi", 401, "Invalid token"),
        ("schemat inny niż Bearer", f"Token {t['admin']}", 401, "Not authenticated"),
        ("brak nagłówka", None, 401, "Not authenticated"),
    ]
    rows, errors = [], []
    for name, auth, code_expected, msg_expected in cases:
        code, body = request("GET", PATH, headers={"Authorization": auth} if auth else None)
        msg = detail(body)
        good = code == code_expected and (msg_expected is None or msg == msg_expected)
        rows.append([name, f"{code_expected} {msg_expected or ''}".strip(), f"{code} {msg}".strip(), ok(good)])
        if not good:
            errors.append(f"{name}: {code} {msg} (oczekiwano {code_expected} {msg_expected or ''})")
    md = "\n\n".join([
        f"Punkt końcowy: `GET /api{PATH}` (rola Admin).",
        table(["Token", "Oczekiwano", "Odpowiedź", "Zgodny"], rows),
    ])
    finish(md, errors, args.out)


if __name__ == "__main__":
    main()
