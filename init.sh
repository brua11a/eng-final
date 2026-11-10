#!/usr/bin/bash
# Runs as the Neo4j superuser (cypher-shell reads NEO4J_USERNAME / NEO4J_PASSWORD).
set -euo pipefail
export NEO4J_USERNAME="$NEO4J_USER"
run() { cypher-shell -a bolt://neo4j:7687 "$@"; }

for f in schema nodes edges; do
    run -d neo4j -f "/queries/$f.cypher"
done

run -d system -f /queries/security.cypher \
    --param "user => '$NEO4J_APP_USER'" \
    --param "pw => '${NEO4J_APP_PASSWORD//\'/\\\'}'"
