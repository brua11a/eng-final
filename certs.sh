#!/usr/bin/bash

set -euo pipefail

cd "$(dirname "$0")"

# One key pair per service, so a compromised container cannot impersonate any other one.
# Each container mounts only its own directory (plus the public ca.pem).
cert() {
    local dir="certificates/$1"
    shift
    mkdir -p "$dir"
    mkcert -cert-file "$dir/public.crt" -key-file "$dir/private.key" "$@"
    # Readable by the container's own user, whose UID differs from the owner on the host.
    chmod 644 "$dir/private.key"
}

mkdir -p certificates
cp "$(mkcert -CAROOT)/rootCA.pem" certificates/ca.pem

cert neo4j neo4j localhost        # Bolt (init, app) and the Neo4j console over HTTPS
cert nginx localhost              # the web client in the browser
cert app app localhost            # the API, behind nginx
cert postgres postgres localhost  # PostgreSQL, for the API
