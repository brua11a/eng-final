"""Testy uwierzytelniania.

1. Czas odpowiedzi POST /api/login dla istniejącego i nieistniejącego konta:
   po czasie odpowiedzi nie powinno dać się odróżnić, czy konto o danym
   adresie istnieje (enumeracja kont przez kanał czasowy).
2. POST /api/admin/users z hasłem dłuższym niż 72 bajty (limit bcrypt):
   oczekiwane 422, nie 500. Używa nieistniejącego idx, więc nie zmienia danych.

Wymaga uruchomionego stacka (`docker compose up`).

Uruchomienie:
    python tests/test_login_timing.py [--n 30] [--out wynik.md]
lub przez pytest:
    pytest tests/test_login_timing.py
"""

import argparse
import json
import ssl
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://localhost:8000/api"
URL = f"{API}/login"
CA = ROOT / "certificates" / "ca.pem"

ADMIN_EMAIL = "admin@pwr.edu.pl"
ADMIN_PASSWORD = "admin"
EXISTING_EMAIL = "279413@student.pwr.edu.pl"
EXISTING_PASSWORD = "student123"
MISSING_EMAIL = "nie-istnieje@pwr.edu.pl"
WRONG_PASSWORD = "zle-haslo"

# Maksymalna dopuszczalna różnica median czasów odpowiedzi [ms].
MAX_DIFF_MS = 30.0

_ctx = ssl.create_default_context(cafile=str(CA))


def post(url: str, payload: dict, token: str | None = None) -> tuple[int, str, float]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, context=_ctx) as resp:
            status, text = resp.status, resp.read().decode()
    except urllib.error.HTTPError as err:
        status, text = err.code, err.read().decode()
    return status, text, (time.perf_counter() - start) * 1000


def login(email: str, password: str) -> tuple[int, str, float]:
    return post(URL, {"email": email, "password": password})


def long_password_status() -> tuple[int, str]:
    _, text, _ = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    token = json.loads(text)["token"]
    status, text, _ = post(
        f"{API}/admin/users",
        {"email": "dlugie-haslo@pwr.edu.pl", "passwd": "a" * 73, "idx": "TEST-NIE-ISTNIEJE"},
        token,
    )
    return status, text


CASES = {
    "istniejące konto, poprawne hasło": (EXISTING_EMAIL, EXISTING_PASSWORD),
    "istniejące konto, błędne hasło": (EXISTING_EMAIL, WRONG_PASSWORD),
    "nieistniejące konto": (MISSING_EMAIL, WRONG_PASSWORD),
}


def measure(n: int) -> dict[str, dict]:
    for email, password in CASES.values():  # rozgrzanie połączeń i pul
        login(email, password)
    results = {}
    for name, (email, password) in CASES.items():
        times, status, detail = [], None, None
        for _ in range(n):
            status, text, ms = login(email, password)
            times.append(ms)
            detail = json.loads(text).get("detail", "(token)")
        results[name] = {
            "status": status,
            "detail": detail,
            "median": statistics.median(times),
            "min": min(times),
            "max": max(times),
        }
    return results


def to_markdown(results: dict[str, dict], n: int) -> str:
    lines = [
        f"Liczba prób na przypadek: {n}",
        "",
        "| Przypadek | Kod | Odpowiedź | Mediana [ms] | Min [ms] | Max [ms] |",
        "| --- | :---: | --- | ---: | ---: | ---: |",
    ]
    for name, r in results.items():
        lines.append(
            f"| {name} | {r['status']} | `{r['detail']}` | {r['median']:.1f} | {r['min']:.1f} | {r['max']:.1f} |"
        )
    diff = abs(results["istniejące konto, błędne hasło"]["median"] - results["nieistniejące konto"]["median"])
    lines += ["", f"Różnica median (błędne hasło vs nieistniejące konto): {diff:.1f} ms (próg: {MAX_DIFF_MS:.0f} ms)"]
    return "\n".join(lines)


def check(results: dict[str, dict]) -> None:
    wrong = results["istniejące konto, błędne hasło"]
    missing = results["nieistniejące konto"]
    assert results["istniejące konto, poprawne hasło"]["status"] == 200
    # Ta sama odpowiedź dla obu przypadków...
    assert (wrong["status"], wrong["detail"]) == (missing["status"], missing["detail"]) == (401, "Invalid email or password")
    # ...i porównywalny czas odpowiedzi.
    diff = abs(wrong["median"] - missing["median"])
    assert diff < MAX_DIFF_MS, f"różnica median {diff:.1f} ms zdradza istnienie konta"


def test_login_timing() -> None:
    check(measure(20))


def test_long_password_rejected() -> None:
    status, text = long_password_status()
    assert status == 422, f"oczekiwano 422, otrzymano {status}: {text}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=30)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    res = measure(args.n)
    lp_status, lp_text = long_password_status()
    md = to_markdown(res, args.n) + (
        f"\n\nPOST /api/admin/users z hasłem 73-bajtowym: {lp_status} `{lp_text[:200]}`"
    )
    print(md)
    if args.out:
        args.out.write_text(md + "\n")
    failed = False
    try:
        check(res)
        print("\nCzas odpowiedzi: OK")
    except AssertionError as e:
        print(f"\nCzas odpowiedzi: BŁĄD - {e}")
        failed = True
    if lp_status == 422:
        print("Długie hasło: OK")
    else:
        print(f"Długie hasło: BŁĄD - oczekiwano 422, otrzymano {lp_status}")
        failed = True
    raise SystemExit(1 if failed else 0)
