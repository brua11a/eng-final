"""Uruchomienie środowiska od zera (3.3 - przenośność, Dodatki - instrukcja uruchomienia).

Skrypt odtwarza instrukcję uruchomienia na świeżym klonie repozytorium:
  1. `git clone` repozytorium do katalogu tymczasowego, skopiowanie pliku .env,
     wygenerowanie certyfikatów skryptem certs.sh (wymaga mkcert z zainstalowanym CA),
  2. `docker compose up --build` na pustych wolumenach - logowanie przez nginx i liczba węzłów,
     krawędzi oraz wierszy w obu bazach,
  3. ponowne uruchomienie (`down` + `up`, wolumeny zachowane) - serwis init wykonuje import ponownie;
     liczby węzłów i krawędzi nie mogą się zmienić (MERGE, 5.3.2),
  4. zmiana hasła konta API Neo4j w .env - po ponownym uruchomieniu API łączy się z nowym hasłem
     (CREATE OR REPLACE USER, 5.1.4),
  5. zmiana hasła konta API PostgreSQL w .env - skrypty inicjalizacyjne obrazu nie są wykonywane
     ponownie, więc API nie może się połączyć (zachowanie opisane w 6.3),
  6. `down -v` i usunięcie klonu.

Kopia działa jako osobny projekt Compose (osobne kontenery i wolumeny), ale na tych samych portach,
dlatego główne środowisko jest na czas testu zatrzymywane (bez usuwania wolumenów) i na końcu
uruchamiane ponownie. Test trwa kilka minut.

Uruchomienie:
    python tests/test_fresh_start.py [--out wynik.md] [--keep]
"""

import argparse
import json
import shutil
import ssl
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from common import ROOT, finish, in_app, ok, table

PROJECT = "thesis-fresh"
LOGIN = {"email": "279413@student.pwr.edu.pl", "password": "student123"}

_COUNTS = r'''
import psycopg

async def main(args):
    nodes = (await q("MATCH (n) RETURN count(n) AS n"))[0]["n"]
    edges = (await q("MATCH ()-[r]->() RETURN count(r) AS n"))[0]["n"]
    async with await psycopg.AsyncConnection.connect(os.environ["PG_CONNINFO"], password=os.environ["PG_PASSWORD"]) as c:
        tables = [r[0] for r in await (await c.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'")).fetchall()]
        rows = 0
        for t in tables:
            rows += (await (await c.execute(f'SELECT count(*) FROM "{t}"')).fetchone())[0]
    return {"nodes": nodes, "edges": edges, "tables": len(tables), "rows": rows}
'''


def run(cmd: list[str], cwd: Path, check=True, timeout=900) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check, timeout=timeout)


def compose(clone: Path, *args, check=True) -> subprocess.CompletedProcess:
    return run(["docker", "compose", "-p", PROJECT, *args], clone, check=check)


def login(clone: Path) -> int | None:
    ctx = ssl.create_default_context(cafile=str(clone / "certificates" / "ca.pem"))
    req = urllib.request.Request("https://localhost:5173/api/login", data=json.dumps(LOGIN).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except OSError:
        return None


def wait_login(clone: Path, limit: int = 300) -> tuple[int | None, float]:
    start = time.time()
    while time.time() - start < limit:
        code = login(clone)
        if code not in (None, 502):
            return code, time.time() - start
        time.sleep(3)
    return None, time.time() - start


def set_env(clone: Path, key: str, value: str) -> None:
    env = clone / ".env"
    lines = [f"{key}={value}" if line.startswith(f"{key}=") else line for line in env.read_text().splitlines()]
    env.write_text("\n".join(lines) + "\n")


def app_state(clone: Path) -> str:
    out = compose(clone, "ps", "-a", "--format", "json", "app", check=False).stdout.strip()
    if not out:
        return "brak kontenera"
    info = json.loads(out.splitlines()[0])
    return f"{info['State']} ({info['Status']})"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    parser.add_argument("--keep", action="store_true", help="nie usuwaj klonu ani wolumenów")
    args = parser.parse_args()

    running = run(["docker", "compose", "ps", "--services", "--status", "running"], ROOT).stdout.split()
    clone = Path(tempfile.mkdtemp(prefix="thesis-fresh-")) / "repo"
    rows, errors = [], []
    counts = {}
    target = (clone, PROJECT)

    def record(step, result, good, note=""):
        rows.append([step, result, ok(good)] + ([note] if note else ["–"]))
        if not good:
            errors.append(f"{step}: {result}")

    try:
        run(["git", "clone", "-q", str(ROOT), str(clone)], ROOT)
        shutil.copy(ROOT / ".env", clone / ".env")
        certs = run(["bash", "certs.sh"], clone, check=False)
        record("1. klon, .env, certs.sh", f"certs.sh: kod {certs.returncode}", certs.returncode == 0)
        if running:
            run(["docker", "compose", "stop"], ROOT)

        t0 = time.time()
        up = compose(clone, "up", "-d", "--build", check=False)
        code, waited = wait_login(clone)
        counts["first"] = in_app(_COUNTS, _project=target) if code == 200 else {}
        record("2. pierwsze uruchomienie na pustych wolumenach",
               f"logowanie przez nginx: {code} po {time.time() - t0:.0f} s; {counts['first']}",
               up.returncode == 0 and code == 200)

        compose(clone, "down")
        compose(clone, "up", "-d")
        code, _ = wait_login(clone)
        counts["second"] = in_app(_COUNTS, _project=target) if code == 200 else {}
        record("3. ponowne uruchomienie (init wykonuje import drugi raz)",
               f"logowanie: {code}; {counts['second']}", code == 200 and counts["second"] == counts["first"],
               "liczby bez zmian" if counts["second"] == counts["first"] else "liczby się zmieniły")

        compose(clone, "down")
        set_env(clone, "NEO4J_APP_PASSWORD", "nowe-haslo-neo4j-" + str(int(time.time())))
        compose(clone, "up", "-d")
        code, _ = wait_login(clone)
        record("4. zmiana NEO4J_APP_PASSWORD w .env", f"logowanie: {code}", code == 200)

        compose(clone, "down")
        set_env(clone, "PG_APP_PASSWORD", "nowe-haslo-pg-" + str(int(time.time())))
        compose(clone, "up", "-d")
        code, _ = wait_login(clone, limit=60)
        logs = compose(clone, "logs", "app", check=False).stdout
        auth_failed = "password authentication failed" in logs
        record("5. zmiana PG_APP_PASSWORD w .env (bez usunięcia wolumenu pg_data)",
               f"logowanie: {code}; kontener app: {app_state(clone)}", code != 200 and auth_failed,
               "API nie startuje: password authentication failed (oczekiwane, 6.3)" if auth_failed else "")
    finally:
        if not args.keep:
            compose(clone, "down", "-v", "--remove-orphans", check=False)
            shutil.rmtree(clone.parent, ignore_errors=True)
        if running:
            run(["docker", "compose", "up", "-d"], ROOT, check=False)
            wait_login(ROOT)

    md = "\n\n".join([
        f"Klon: `{clone}` (projekt Compose `{PROJECT}`), usunięty po teście: {'nie' if args.keep else 'tak'}.",
        table(["Krok", "Wynik", "Zgodny", "Uwagi"], rows),
    ])
    finish(md, errors, args.out)


if __name__ == "__main__":
    main()
