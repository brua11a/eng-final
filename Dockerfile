FROM neo4j:2026.07.1-enterprise

ENV NEO4J_ACCEPT_LICENSE_AGREEMENT=yes
# No plugins: APOC was unused, and its file import/export would let queries
# read and write files on the server.
# Only the import directory is readable by LOAD CSV.
ENV NEO4J_server_directories_import=/import

VOLUME ["/data", "/logs", "/import", "/plugins", "/conf"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
  CMD wget -qO- http://localhost:7474 || exit 1

CMD ["neo4j"]
