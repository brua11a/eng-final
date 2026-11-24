"""Wpływ rozszerzenia neo4j-rust-ext na czas warstw sterownika i API (Neo4j).

neo4j-rust-ext to oficjalne rozszerzenie sterownika Neo4j dla Pythona: zastępuje implementację
kodowania i dekodowania PackStream (format danych protokołu Bolt) kodem w języku Rust, bez zmian
w API sterownika. Skrypt mierzy tę samą bazę dwukrotnie: z obrazem API bez rozszerzenia i z obrazem
z rozszerzeniem (thesis-app-rust, budowany automatycznie), i zapisuje bench/results/rust_ext.csv
(scale, students, variant, endpoint, backend, layer, run, ms).

Uruchomienie:
    python bench/rust_ext.py 3000 [--runs 50]
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from run import OUT, ROOT, compose_cmd, replace_rows, sh, wait_ready

IMAGE = "thesis-app-rust"
OVERRIDE = ROOT / "bench" / "docker-compose.rust.yml"


def build_image() -> None:
    base = sh("docker", "compose", "-p", "thesis-bench", "-f", "docker-compose.yml", "config", "--images").split()
    app_image = next(i for i in base if i.endswith("-app") or i.endswith("-app:latest"))
    subprocess.run(["docker", "build", "-q", "-t", IMAGE, "-"], check=True, capture_output=True, text=True,
                   input=f"FROM {app_image}\nUSER root\nRUN pip install --no-cache-dir neo4j-rust-ext==6.2.0.0\nUSER api\n")


def measure(cmd, env, runs) -> dict:
    return json.loads(sh(*cmd, "exec", "-T", "app", "python", "-",
                         json.dumps({"runs": runs, "warmup": 10, "login_runs": 5}), env=env,
                         input=(ROOT / "bench" / "measure.py").read_text()))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("scale")
    parser.add_argument("--runs", type=int, default=50)
    args = parser.parse_args()
    OVERRIDE.write_text(f"services:\n  app:\n    image: {IMAGE}\n    pull_policy: never\n")
    cmd, env = compose_cmd(args.scale)
    running = sh("docker", "compose", "ps", "--services", "--status", "running").split()
    if running:
        sh("docker", "compose", "stop")
    rows = []
    students = None
    try:
        sh(*cmd, "down", "-v", "--remove-orphans", env=env, check=False)
        sh(*cmd, "up", "-d", "--build", env=env)
        wait_ready()
        build_image()
        for variant in ("python", "rust"):
            if variant == "rust":
                sh(*cmd, "-f", str(OVERRIDE), "up", "-d", "--no-build", "--force-recreate", "app", env=env)
                wait_ready()
                check = sh(*cmd, "exec", "-T", "app", "python", "-c",
                           "import importlib.metadata as m; print(m.version('neo4j-rust-ext'))", env=env).strip()
                print(f"neo4j-rust-ext {check}", file=sys.stderr)
            time.sleep(3)
            m = measure(cmd, env, args.runs)
            students = students or len(open(
                (ROOT / "import" if args.scale == "seed" else ROOT / "bench" / "data" / args.scale / "import")
                / "nodes" / "students.csv").readlines()) - 1
            rows += [{"scale": args.scale, "students": students, "variant": variant, "endpoint": s["endpoint"],
                      "backend": s["backend"], "layer": s["layer"], "run": i, "ms": round(v, 4)}
                     for s in m["samples"] for i, v in enumerate(s["ms"])]
            print(f"[{args.scale}] {variant}: zmierzono", file=sys.stderr)
    finally:
        sh(*cmd, "down", "-v", "--remove-orphans", env=env, check=False)
        OVERRIDE.unlink(missing_ok=True)
        if running:
            sh("docker", "compose", "up", "-d")
    replace_rows("rust_ext.csv", args.scale, rows)
    print("zapisano", OUT / "rust_ext.csv", file=sys.stderr)


if __name__ == "__main__":
    main()
