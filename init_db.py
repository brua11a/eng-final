"""Initialise Neo4j: graph type, data, and the database account used by the API.

Run by the `init` service on every start of the stack, before the API. It replaces cypher-shell:
cypher-shell's `--param` takes a Cypher expression, so a password pasted into it became Cypher
code (injection, or a different password than in .env). The driver sends the account name and
password as query parameters, which are never parsed as code. The driver also verifies the
server certificate against ca.pem (SSL_CERT_FILE), so no Java truststore is needed.
"""

import os
import re
import sys
from pathlib import Path

from neo4j import GraphDatabase

QUERIES = Path(os.environ.get("QUERIES_DIR", "/queries"))


def statements(name: str) -> list[str]:
    """The statements of a .cypher file; each ends with a semicolon at the end of a line."""
    text = (QUERIES / name).read_text()
    return [s.strip() for s in re.split(r";\s*$", text, flags=re.MULTILINE) if s.strip()]


def main() -> None:
    uri = os.environ["NEO4J_URI"]
    auth = (os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"])
    app_user = os.environ["NEO4J_APP_USER"]
    app_password = os.environ["NEO4J_APP_PASSWORD"]

    with GraphDatabase.driver(uri, auth=auth) as driver:
        driver.verify_connectivity()

        with driver.session(database="neo4j") as session:
            # Schema changes cannot share a transaction with data writes.
            for query in statements("schema.cypher"):
                session.run(query).consume()

            # The whole import in one transaction: either all of the data is loaded or none.
            # MERGE makes it safe to run again on every start.
            with session.begin_transaction() as tx:
                for name in ("nodes.cypher", "edges.cypher"):
                    for query in statements(name):
                        tx.run(query).consume()
                tx.commit()

        # Administration commands run one per transaction in the system database.
        with driver.session(database="system") as session:
            for query in statements("security.cypher"):
                session.run(query, user=app_user, pw=app_password).consume()

    print("init: schema, data and API account ready", file=sys.stderr)


if __name__ == "__main__":
    main()
