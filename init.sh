#!/usr/bin/bash

set -euo pipefail

rm -f /tmp/truststore.p12
keytool -importcert -noprompt -alias ca -file /ca.pem \
    -keystore /tmp/truststore.p12 -storepass changeit
export JAVA_OPTS="-Djavax.net.ssl.trustStore=/tmp/truststore.p12 -Djavax.net.ssl.trustStorePassword=changeit"

cypher-shell -d neo4j -f /queries/schema.cypher
cypher-shell -d neo4j -f /queries/nodes.cypher
cypher-shell -d neo4j -f /queries/edges.cypher

cypher-shell -d system -f /queries/security.cypher \
    --param "user => '$NEO4J_APP_USER'" \
    --param "pw => '${NEO4J_APP_PASSWORD//\'/\\\'}'"
