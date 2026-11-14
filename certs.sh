#!/usr/bin/bash

set -euo pipefail

cd "$(dirname "$0")"

mkdir -p certificates
cp "$(mkcert -CAROOT)/rootCA.pem" certificates/ca.pem
mkcert -cert-file certificates/public.crt -key-file certificates/private.key neo4j localhost
chmod 644 certificates/private.key
