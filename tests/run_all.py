"""Uruchamia wszystkie testy po kolei i zapisuje wyniki (tabele Markdown) do katalogu tests/wyniki/.

Uruchomienie:
    python tests/run_all.py            # bez testu uruchomienia od zera (zatrzymuje środowisko, trwa kilka minut)
    python tests/run_all.py --all      # wszystkie testy
    python tests/run_all.py jwt opinions   # wybrane testy (nazwy bez prefiksu test_)
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "wyniki"

TESTS = [
    "permissions", "check_order", "jwt", "account_lifecycle", "role_revocation",
    "average_grade", "registration_turn", "opinions",
    "schema_constraints", "db_privileges", "tls_config", "tls_capture",
    "concurrent_registration", "concurrent_registration_rel", "login_timing",
]
SLOW = ["fresh_start"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("names", nargs="*")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    names = args.names or TESTS + (SLOW if args.all else [])
    OUT.mkdir(exist_ok=True)
    summary = []
    for name in names:
        script = HERE / f"test_{name}.py"
        start = time.time()
        # Starsze skrypty (concurrent_registration*, login_timing) mają własne argumenty, ale wszystkie
        # przyjmują --out.
        proc = subprocess.run([sys.executable, str(script), "--out", str(OUT / f"{name}.md")],
                              capture_output=True, text=True)
        status = "OK" if proc.returncode == 0 else "BŁĄD"
        summary.append((name, status, time.time() - start))
        print(f"{status:5} {name:30} {time.time() - start:6.1f} s")
        if proc.returncode:
            print("      " + (proc.stdout.strip().splitlines() or [""])[-1])
            print("      " + "\n      ".join(proc.stderr.strip().splitlines()[-5:]))
    failed = [n for n, s, _ in summary if s != "OK"]
    print(f"\n{len(summary) - len(failed)}/{len(summary)} testów zaliczonych" + (f"; błędy: {', '.join(failed)}" if failed else ""))
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
