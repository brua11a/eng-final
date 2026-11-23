#!/usr/bin/bash
# Least-privilege account used by the relational backend of the API
# (counterpart of queries/security.cypher).
#
# psql variables are substituted by psql itself: :"user" becomes a quoted identifier and :'pw'
# a quoted string literal, so values from .env never become part of the SQL code
# (unlike `cypher-shell --param`, see init.sh).

set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    -v user="$PG_APP_USER" -v pw="$PG_APP_PASSWORD" -v db="$POSTGRES_DB" <<'SQL'
CREATE ROLE :"user" LOGIN PASSWORD :'pw';
GRANT CONNECT ON DATABASE :"db" TO :"user";
GRANT USAGE ON SCHEMA public TO :"user";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO :"user";
-- No CREATE on the schema, no ownership of tables (no DDL), and no pg_read_server_files role,
-- so COPY ... FROM '<file>' is not allowed (counterpart of DENY LOAD in Neo4j).
SQL
