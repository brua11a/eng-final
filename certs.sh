#!/usr/bin/bash

set -euo pipefail

cd "$(dirname "$0")"

mkdir -p certificates
cp "$(mkcert -CAROOT)/rootCA.pem" certificates/ca.pem
mkcert -cert-file certificates/public.crt -key-file certificates/private.key neo4j localhost
chmod 644 certificates/private.key

# Separate certificate for the API (nginx -> app traffic over TLS)
mkdir -p certificates/app
mkcert -cert-file certificates/app/public.crt -key-file certificates/app/private.key app localhost
chmod 644 certificates/app/private.key
