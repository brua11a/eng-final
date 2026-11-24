"""Wspólne funkcje skryptów testowych.

Skrypty działają na hoście, korzystając wyłącznie z biblioteki standardowej. Wszystko, co wymaga
sterowników baz danych, kodu aplikacji lub klucza JWT_SECRET, wykonywane jest w kontenerze `app`
(funkcja `in_app`), który ma te zależności i łączy się z bazami tak samo jak API.

Wymaga uruchomionego stacka (`docker compose up`).
"""

import json
import ssl
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CA = ROOT / "certificates" / "ca.pem"
API = "https://localhost:8000/api"  # API bezpośrednio (port wystawiony dla programisty)
WEB = "https://localhost:5173/api"  # API przez nginx, tak jak widzi je przeglądarka
CTX = ssl.create_default_context(cafile=str(CA))

# Prefiks identyfikatorów danych tymczasowych; dane z nim są usuwane po teście.
TAG = "test-"

# Kod wykonywany w kontenerze app przed kodem testu: sterowniki, konta API i tworzenie tokenów.
_PRELUDE = r'''
import asyncio, json, os, sys, time, uuid
import jwt
from app.graph_backend.database import driver

TAG = "test-"
SECRET = os.environ["JWT_SECRET"]

def token(idx, roles, ttl=600, **claims):
    """Token podpisany kluczem API, z tymi samymi roszczeniami co przy logowaniu (5.5.6)."""
    payload = {"sub": f"{idx}@test", "idx": idx, "roles": roles, "iat": time.time(), "exp": int(time.time()) + ttl}
    payload.update(claims)
    payload = {k: v for k, v in payload.items() if v is not None}
    return jwt.encode(payload, SECRET, algorithm="HS256")

async def q(query, **params):
    async with driver.session() as s:
        return [r.data() async for r in await s.run(query, **params)]

def new_id():
    return TAG + str(uuid.uuid4())
'''

_EPILOGUE = r'''
async def _entry():
    try:
        out = await main(json.loads(sys.argv[1]))
        print(json.dumps(out, default=str))
    finally:
        await driver.close()

asyncio.run(_entry())
'''


def in_app(code: str, _project: tuple[Path, str] | None = None, **args):
    """Wykonuje w kontenerze app kod definiujący `async def main(args)` i zwraca jego wynik (JSON).

    `_project` - (katalog, nazwa projektu Compose), gdy test dotyczy innej kopii środowiska niż domyślna.
    """
    cwd, project = _project or (ROOT, None)
    cmd = ["docker", "compose"] + (["-p", project] if project else [])
    out = subprocess.run(
        cmd + ["exec", "-T", "app", "python", "-", json.dumps(args)],
        input=_PRELUDE + code + _EPILOGUE, capture_output=True, text=True, cwd=cwd,
    )
    if out.returncode:
        raise RuntimeError(out.stderr.strip()[-1500:])
    return json.loads(out.stdout.strip().splitlines()[-1])


def request(method: str, path: str, token: str | None = None, body=None, base: str = API,
            headers: dict | None = None) -> tuple[int, object]:
    """Wysyła żądanie do API; zwraca kod statusu i treść odpowiedzi (JSON albo tekst)."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    for name, value in (headers or {}).items():
        req.add_header(name, value)
    try:
        with urllib.request.urlopen(req, context=CTX) as res:
            raw = res.read()
            status = res.status
    except urllib.error.HTTPError as err:
        raw, status = err.read(), err.code
    try:
        return status, json.loads(raw) if raw else None
    except ValueError:
        return status, raw.decode(errors="replace")


def detail(body) -> str:
    """Komunikat błędu z odpowiedzi API (pole `detail`)."""
    if isinstance(body, dict):
        d = body.get("detail", "")
        if isinstance(d, list):  # błąd walidacji 422: lista pól
            return "; ".join(f"{'.'.join(map(str, e.get('loc', [])[1:]))}: {e.get('msg')}" for e in d)
        return str(d)
    return ""


def table(header: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join(" --- " for _ in header) + "|"]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def finish(markdown: str, errors: list[str], out: Path | None) -> None:
    """Drukuje wynik, opcjonalnie zapisuje go do pliku i kończy skrypt kodem 0 (OK) lub 1 (błąd)."""
    print(markdown)
    result = "OK" if not errors else "BŁĄD\n- " + "\n- ".join(errors)
    print("\nWYNIK:", result)
    if out:
        out.write_text(markdown + "\n\nWynik: " + result + "\n")
    raise SystemExit(1 if errors else 0)


def ok(passed: bool) -> str:
    return "tak" if passed else "**NIE**"
