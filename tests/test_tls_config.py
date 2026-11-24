"""Konfiguracja szyfrowania połączeń (3.3, 5.1.1, 5.1.6, 6.3).

Dla każdego portu wystawionego na hosta sprawdzane jest:
  - połączenie TLS z weryfikacją certyfikatu (lokalne CA) i nazwy hosta "localhost" - wersja i szyfr,
  - połączenie z nazwą hosta spoza certyfikatu - klient musi je odrzucić (weryfikacja nazwy),
  - połączenie bez szyfrowania - serwer nie może obsłużyć żądania,
  - połączenie TLS 1.2 - informacyjnie (wymaganie dotyczy szyfrowania, nie konkretnej wersji).
Ponadto:
  - porty są opublikowane wyłącznie na 127.0.0.1 (5.1.6),
  - wewnątrz sieci Dockera API odrzuca połączenie z bazami pod adresem IP zamiast nazwy z certyfikatu,
    a PostgreSQL odrzuca połączenie bez TLS (pg_hba.conf).

Skrypt korzysta wyłącznie z biblioteki standardowej na hoście; sprawdzenia z wnętrza sieci Dockera
wykonuje w kontenerze app.

Uruchomienie:
    python tests/test_tls_config.py [--out wynik.md]
"""

import argparse
import json
import socket
import ssl
import struct
import subprocess
from pathlib import Path

from common import CA, ROOT, finish, in_app, ok, table

HOST = "localhost"
# port: (opis, protokół)
PORTS = {
    5173: ("nginx: klient webowy i proxy API", "http"),
    8000: ("API (uvicorn)", "http"),
    7473: ("Neo4j: konsola HTTPS", "http"),
    7687: ("Neo4j: Bolt", "bolt"),
    5432: ("PostgreSQL", "postgres"),
}

BOLT_HANDSHAKE = bytes.fromhex("6060B017") + bytes.fromhex("00000505" "00000404" "00000000" "00000000")
PG_SSL_REQUEST = struct.pack("!ii", 8, 80877103)


def open_tcp(port: int, proto: str) -> socket.socket:
    sock = socket.create_connection((HOST, port), timeout=5)
    if proto == "postgres":  # TLS w PostgreSQL zaczyna się od pakietu SSLRequest
        sock.sendall(PG_SSL_REQUEST)
        if sock.recv(1) != b"S":
            raise ConnectionError("serwer odmówił TLS")
    return sock


def tls(port: int, proto: str, server_hostname: str = HOST, max_version=None) -> dict:
    ctx = ssl.create_default_context(cafile=str(CA))
    if max_version:
        ctx.maximum_version = max_version
    try:
        with ctx.wrap_socket(open_tcp(port, proto), server_hostname=server_hostname) as s:
            return {"ok": True, "version": s.version(), "cipher": s.cipher()[0]}
    except (ssl.SSLError, ssl.CertificateError, ConnectionError, OSError) as e:
        return {"ok": False, "error": (getattr(e, "reason", None) or str(e))[:80]}


def startup_message() -> bytes:
    """StartupMessage PostgreSQL bez TLS: wersja protokołu 3.0, konto API i baza."""
    params = b"user\0app\0database\0usos\0\0"
    return struct.pack("!ii", 8 + len(params), 196608) + params


def plaintext(port: int, proto: str) -> str:
    """Wysyła żądanie bez TLS; zwraca opis odpowiedzi serwera."""
    payload = {"http": f"GET /api/subjects HTTP/1.1\r\nHost: {HOST}\r\nConnection: close\r\n\r\n".encode(),
               "bolt": BOLT_HANDSHAKE,
               "postgres": startup_message()}[proto]
    try:
        with socket.create_connection((HOST, port), timeout=5) as s:
            s.sendall(payload)
            data = s.recv(200)
    except OSError as e:
        return f"połączenie zerwane ({e.__class__.__name__})"
    if not data:
        return "połączenie zamknięte bez odpowiedzi"
    if data.startswith(b"HTTP/"):
        return data.split(b"\r\n", 1)[0].decode(errors="replace")
    if proto == "postgres" and data[:1] == b"E":
        fields = dict((f[:1].decode(), f[1:].decode(errors="replace")) for f in data[5:].split(b"\0") if f)
        return f"błąd PostgreSQL: {fields.get('M', '')[:70]}"
    if data[:1] in (b"\x15", b"\x16"):
        return "odpowiedź w protokole TLS (alert/handshake)"
    return f"{len(data)} B: {data[:16].hex()}"


def plaintext_served(port: int, proto: str, answer: str) -> bool:
    """Czy serwer obsłużył żądanie bez szyfrowania."""
    if proto == "http":
        return answer.startswith("HTTP/") and " 400 " not in answer
    if proto == "bolt":  # obsłużony handshake Bolt to 4 bajty wersji
        return answer.startswith("4 B")
    return False if answer.startswith(("błąd PostgreSQL", "połączenie")) else True


_INTERNAL = r'''
import socket, ssl, psycopg
from neo4j import AsyncGraphDatabase

async def main(args):
    out = {}
    ip = socket.gethostbyname("neo4j")
    d = AsyncGraphDatabase.driver(f"bolt+s://{ip}:7687", auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]))
    try:
        await d.verify_connectivity(); out["neo4j_ip"] = "połączono"
    except Exception as e:
        out["neo4j_ip"] = f"odrzucono: {str(e).splitlines()[-1][:60]}"
    finally:
        await d.close()
    plain = AsyncGraphDatabase.driver("bolt://neo4j:7687", auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]))
    try:
        await plain.verify_connectivity(); out["neo4j_plain"] = "połączono"
    except Exception as e:
        out["neo4j_plain"] = f"odrzucono: {str(e).splitlines()[-1][:110]}"
    finally:
        await plain.close()
    pg_ip = socket.gethostbyname("postgres")
    base = os.environ["PG_CONNINFO"]
    for key, conninfo in (("pg_ip", base.replace("host=postgres", f"host={pg_ip}")),
                          ("pg_plain", base.replace("sslmode=verify-full", "sslmode=disable"))):
        try:
            c = await psycopg.AsyncConnection.connect(conninfo, password=os.environ["PG_PASSWORD"])
            await c.close(); out[key] = "połączono"
        except psycopg.Error as e:
            out[key] = "odrzucono: " + str(e).strip().split("failed: ")[-1][:120]
    out["neo4j_ip_addr"], out["pg_ip_addr"] = ip, pg_ip
    return out
'''


def published() -> list[tuple[str, str, int]]:
    out = subprocess.run(["docker", "compose", "ps", "--format", "json"], capture_output=True, text=True,
                         cwd=ROOT, check=True).stdout
    result = []
    for line in out.splitlines():
        svc = json.loads(line)
        for p in svc["Publishers"]:
            if p["PublishedPort"]:
                result.append((svc["Service"], p["URL"], p["PublishedPort"]))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    errors, rows = [], []
    for port, (name, proto) in PORTS.items():
        good = tls(port, proto)
        wrong_name = tls(port, proto, server_hostname="evil.example")
        v12 = tls(port, proto, max_version=ssl.TLSVersion.TLSv1_2)
        plain = plaintext(port, proto)
        served = plaintext_served(port, proto, plain)
        rows.append([port, name, f"{good.get('version', '–')}, {good.get('cipher', good.get('error'))}",
                     "odrzucona" if not wrong_name["ok"] else "**przyjęta**",
                     plain.replace("|", "/"), "przyjęte" if v12["ok"] else "odrzucone"])
        if not good["ok"]:
            errors.append(f"{port}: brak połączenia TLS: {good['error']}")
        if wrong_name["ok"]:
            errors.append(f"{port}: certyfikat przyjęty dla nazwy spoza certyfikatu")
        if served:
            errors.append(f"{port}: żądanie bez szyfrowania obsłużone: {plain}")

    bind_rows = []
    for service, url, port in published():
        bind_rows.append([service, f"{url}:{port}", ok(url == "127.0.0.1")])
        if url != "127.0.0.1":
            errors.append(f"{service}: port {port} opublikowany na {url}")

    internal = in_app(_INTERNAL)
    int_rows = [
        [f"API -> Neo4j pod adresem IP ({internal['neo4j_ip_addr']}), bolt+s", internal["neo4j_ip"]],
        ["API -> Neo4j bez TLS (bolt://)", internal["neo4j_plain"]],
        [f"API -> PostgreSQL pod adresem IP ({internal['pg_ip_addr']}), verify-full", internal["pg_ip"]],
        ["API -> PostgreSQL bez TLS (sslmode=disable)", internal["pg_plain"]],
    ]
    for desc, res in int_rows:
        if not res.startswith("odrzucono"):
            errors.append(f"{desc}: {res}")

    md = "\n\n".join([
        "## Porty wystawione na hosta",
        table(["Port", "Usługa", "TLS z weryfikacją (wersja, szyfr)", "Obca nazwa hosta",
               "Żądanie bez TLS", "TLS 1.2 (informacyjnie)"], rows),
        "## Adresy, na których opublikowano porty",
        table(["Serwis", "Adres", "Tylko localhost"], bind_rows),
        "## Połączenia w sieci Dockera (z kontenera app)",
        table(["Próba", "Wynik"], [[d, r.replace("|", "/")] for d, r in int_rows]),
    ])
    finish(md, errors, args.out)


if __name__ == "__main__":
    main()
