"""Podsłuch ruchu sieciowego: czy dane przesyłane między elementami systemu są zaszyfrowane (3.3).

Skrypt nagrywa ruch na wszystkich czterech połączeniach systemu:
  przeglądarka -> nginx (443), nginx -> API (8000), API -> Neo4j (7687), API -> PostgreSQL (5432),
wysyła w tym czasie żądania zawierające znane, tajne wartości, a następnie przeszukuje nagrane
pakiety w poszukiwaniu tych wartości.

Nagrywanie: tcpdump w pomocniczym kontenerze dołączonym do przestrzeni sieciowej kontenerów
frontend i app (`--net container:...`), czyli tak, jak widziałby ten ruch atakujący w sieci Dockera.
Kontenery systemu nie są w żaden sposób modyfikowane.

API utrzymuje połączenia z bazami w pulach otwieranych przy starcie, więc w trakcie nagrania kontener
app otwiera dodatkowo nowe połączenia z tą samą konfiguracją co API, aby nagrać negocjację TLS.

Analiza (tshark na hoście):
  - wersja TLS wynegocjowana na każdym połączeniu,
  - przeszukanie surowej zawartości segmentów TCP: hasło, adres e-mail, znacznik wysłany w zapytaniu,
    token JWT, fragmenty zapytań Cypher i SQL - żadna z tych wartości nie może wystąpić jawnie,
  - kontrola: ruch przeglądarka -> nginx jest odszyfrowywany kluczami sesji zapisanymi przez klienta
    testowego (SSLKEYLOGFILE). Po odszyfrowaniu te same wartości są widoczne, co dowodzi, że
    w nagraniu rzeczywiście się znajdowały, a ukrywało je wyłącznie szyfrowanie.

Pliki .pcap i plik kluczy zostają w katalogu wyników (domyślnie tests/capture/), aby można je było
otworzyć w programie Wireshark (Preferencje -> Protocols -> TLS -> (Pre)-Master-Secret log filename).

Wymaga: Docker, tshark na hoście. Obraz z tcpdump (alpine + tcpdump) jest budowany przy pierwszym
uruchomieniu.

Uruchomienie:
    python tests/test_tls_capture.py [--out wynik.md] [--dir tests/capture]
"""

import argparse
import json
import os
import secrets
import ssl
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from common import CA, ROOT, finish, in_app, ok, table

IMAGE = "thesis-tcpdump:latest"
LOGIN = {"email": "279413@student.pwr.edu.pl", "password": "student123"}  # konto z danych początkowych

# nagranie: (kontener, filtr tcpdump)
CAPTURES = {"frontend": "tcp port 443 or tcp port 8000", "app": "tcp port 7687 or tcp port 5432"}
# połączenie: (plik, port, opis)
LEGS = [
    ("frontend", 443, "przeglądarka -> nginx"),
    ("frontend", 8000, "nginx -> API"),
    ("app", 7687, "API -> Neo4j (Bolt)"),
    ("app", 5432, "API -> PostgreSQL"),
]


def sh(*cmd, check=True, **kw) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, check=check, cwd=ROOT, **kw).stdout


def ensure_image() -> None:
    if not sh("docker", "images", "-q", IMAGE).strip():
        subprocess.run(["docker", "build", "-t", IMAGE, "-"], input="FROM alpine:3.20\nRUN apk add --no-cache tcpdump\n",
                       text=True, check=True, capture_output=True)


def start_capture(service: str, bpf: str, outdir: Path) -> str:
    target = sh("docker", "compose", "ps", "-q", service).strip()
    name = f"tls-capture-{service}"
    sh("docker", "rm", "-f", name, check=False)
    sh("docker", "run", "-d", "--name", name, "--net", f"container:{target}",
       "--cap-add", "NET_RAW", "--cap-add", "NET_ADMIN", "-v", f"{outdir}:/cap", IMAGE,
       "tcpdump", "-i", "any", "-U", "-s", "0", "-Z", "root", "-w", f"/cap/{service}.pcap", bpf)
    for _ in range(50):  # czekanie na start nasłuchu
        if "listening on" in subprocess.run(["docker", "logs", name], capture_output=True, text=True).stderr:
            return name
        time.sleep(0.1)
    raise RuntimeError(f"tcpdump w {name} nie wystartował")


def stop_capture(name: str) -> None:
    time.sleep(1)  # ostatnie pakiety (zamknięcie połączeń)
    sh("docker", "stop", "-t", "5", name, check=False)
    sh("docker", "rm", "-f", name, check=False)


def generate_traffic(keylog: Path, marker: str) -> dict:
    """Żądania przez nginx, tak jak z przeglądarki; klucze sesji TLS trafiają do pliku keylog."""
    ctx = ssl.create_default_context(cafile=str(CA))
    ctx.keylog_filename = str(keylog)

    def call(method, path, body=None, token=None):
        req = urllib.request.Request("https://localhost:5173/api" + path, method=method,
                                     data=json.dumps(body).encode() if body else None,
                                     headers={"Content-Type": "application/json",
                                              **({"Authorization": f"Bearer {token}"} if token else {})})
        try:
            with urllib.request.urlopen(req, context=ctx) as r:
                return r.status, json.loads(r.read() or b"null")
        except urllib.error.HTTPError as e:
            return e.code, None

    code, body = call("POST", "/login", LOGIN)
    assert code == 200, f"logowanie: {code}"
    token = body["token"]
    codes = [call("GET", f"/subjects?name={marker}", token=token)[0],       # zapytanie Cypher z $name
             call("GET", f"/rel/subjects?name={marker}", token=token)[0]]   # to samo w SQL
    return {"token": token, "codes": codes}


# API utrzymuje pule połączeń z bazami, otwierane przy starcie, więc ich negocjacja TLS nie trafia
# do nagrania. Dlatego w trakcie nagrania kontener app otwiera nowe połączenia z tą samą konfiguracją
# co API (ten sam adres, konto, weryfikacja certyfikatu) i wysyła zapytania ze znacznikiem.
_FRESH = r'''
import psycopg
from neo4j import AsyncGraphDatabase

async def main(args):
    d = AsyncGraphDatabase.driver(os.environ["NEO4J_URI"], auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]))
    try:
        async with d.session() as s:
            await (await s.run("MATCH (su:Subject) WHERE su.name CONTAINS $m RETURN count(su)", m=args["marker"])).consume()
    finally:
        await d.close()
    async with await psycopg.AsyncConnection.connect(os.environ["PG_CONNINFO"], password=os.environ["PG_PASSWORD"]) as c:
        await c.execute("SELECT count(*) FROM subject WHERE name LIKE %s", ("%" + args["marker"] + "%",))
    return {}
'''


def tshark(pcap: Path, *args) -> list[str]:
    out = sh("tshark", "-r", str(pcap), "-d", "tcp.port==8000,tls", "-d", "tcp.port==7687,tls", *args)
    return [line for line in out.splitlines() if line.strip()]


def payload(pcap: Path, port: int) -> bytes:
    """Zawartość wszystkich segmentów TCP danego połączenia, sklejona (tak jak przesłano ją siecią)."""
    lines = tshark(pcap, "-Y", f"tcp.port=={port} && tcp.len>0", "-T", "fields", "-e", "tcp.payload")
    return b"".join(bytes.fromhex(line.replace(":", "")) for line in lines)


def tls_version(pcap: Path, port: int) -> str:
    lines = tshark(pcap, "-Y", f"tcp.port=={port} && tls.handshake.type==2", "-T", "fields",
                   "-e", "tls.handshake.extensions.supported_version")
    versions = {v.split(",")[0] for v in lines}
    return ", ".join(sorted({"0x0304": "TLS 1.3", "0x0303": "TLS 1.2"}.get(v, v) for v in versions)) or "–"


def tls_records(pcap: Path, port: int) -> int:
    return len(tshark(pcap, "-Y", f"tcp.port=={port} && tls.app_data", "-T", "fields", "-e", "frame.number"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    parser.add_argument("--dir", type=Path, default=ROOT / "tests" / "capture")
    args = parser.parse_args()
    outdir = args.dir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    keylog = outdir / "client-keys.log"
    keylog.unlink(missing_ok=True)
    marker = "tajny-znacznik-" + secrets.token_hex(4)

    ensure_image()
    names = [start_capture(svc, bpf, outdir) for svc, bpf in CAPTURES.items()]
    try:
        traffic = generate_traffic(keylog, marker)
        in_app(_FRESH, marker=marker)
    finally:
        for name in names:
            stop_capture(name)
        # tcpdump zapisuje pliki jako root; zmiana właściciela, by można je było usunąć bez sudo
        sh("docker", "run", "--rm", "-v", f"{outdir}:/cap", "alpine:3.20", "chown", f"{os.getuid()}:{os.getgid()}",
           "/cap/frontend.pcap", "/cap/app.pcap", check=False)

    secrets_to_find = {
        "hasło": LOGIN["password"].encode(),
        "adres e-mail": LOGIN["email"].encode(),
        "znacznik z zapytania": marker.encode(),
        "token JWT": traffic["token"][:40].encode(),
        "Cypher (`MATCH (`)": b"MATCH (",
        "SQL (`SELECT `)": b"SELECT ",
    }
    errors, rows = [], []
    found_per_leg = {}
    for svc, port, desc in LEGS:
        pcap = outdir / f"{svc}.pcap"
        data = payload(pcap, port)
        found = [name for name, value in secrets_to_find.items() if value in data]
        found_per_leg[port] = found
        version = tls_version(pcap, port)
        records = tls_records(pcap, port)
        rows.append([desc, port, f"{len(data)} B", version, records, ", ".join(found) or "brak", ok(not found and records > 0)])
        if not data:
            errors.append(f"{desc}: brak nagranego ruchu")
        if found:
            errors.append(f"{desc}: jawnie widoczne: {', '.join(found)}")
        if version == "–" or records == 0:
            errors.append(f"{desc}: brak ruchu TLS")

    # Kontrola: odszyfrowanie połączenia przeglądarka -> nginx kluczami klienta.
    decrypted = tshark(outdir / "frontend.pcap", "-o", f"tls.keylog_file:{keylog}", "-Y", "http.request",
                       "-T", "fields", "-e", "http.request.method", "-e", "http.request.uri", "-e", "http.file_data")
    plain = "\n".join(decrypted)
    control = [[name, ok(value.decode() in plain or value.hex() in plain.replace(":", ""))]
               for name, value in secrets_to_find.items() if name in ("hasło", "adres e-mail", "znacznik z zapytania")]
    if not all(r[1] == "tak" for r in control):
        errors.append("kontrola: po odszyfrowaniu nie znaleziono wysłanych wartości")
    requests_shown = [line.split("\t")[:2] for line in decrypted]

    md = "\n\n".join([
        f"Wysłane żądania (przez nginx): `POST /api/login`, `GET /api/subjects?name={marker}`, "
        f"`GET /api/rel/subjects?name={marker}` – kody {traffic['codes']}.",
        "## Nagrany ruch",
        table(["Połączenie", "Port", "Dane w segmentach TCP", "Wersja TLS", "Rekordy TLS z danymi",
               "Jawnie widoczne wartości", "Zaszyfrowane"], rows),
        "Szukane wartości: " + ", ".join(secrets_to_find) + ".",
        "## Kontrola: połączenie przeglądarka -> nginx odszyfrowane kluczami sesji klienta",
        table(["Metoda", "Adres"], requests_shown),
        table(["Wartość widoczna po odszyfrowaniu", "Znaleziono"], control),
        f"Pliki: `{outdir / 'frontend.pcap'}`, `{outdir / 'app.pcap'}`, klucze sesji: `{keylog}`.",
    ])
    finish(md, errors, args.out)


if __name__ == "__main__":
    main()
