#!/usr/bin/bash
# PostgreSQL refuses to use a private key that other users can read. The key is mounted
# read-only with mode 644, so a copy with mode 600 owned by postgres is made first.

set -euo pipefail

install -m 600 -o postgres -g postgres /certs/private.key /tmp/server.key
exec docker-entrypoint.sh "$@"
