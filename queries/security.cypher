// Least-privilege database account for the API (run on the system database).
// The API may only read and write data. Not granted: schema management (graph type,
// constraints, indexes), name management, user/role management, DBMS administration.
CREATE USER $user IF NOT EXISTS SET PASSWORD $pw CHANGE NOT REQUIRED;
CREATE ROLE app_rw IF NOT EXISTS;
GRANT ACCESS ON DATABASE neo4j TO app_rw;
GRANT MATCH {*} ON GRAPH neo4j TO app_rw;
GRANT WRITE ON GRAPH neo4j TO app_rw;
// The built-in PUBLIC role allows LOAD CSV, which would expose files in /import
// (including password hashes).
DENY LOAD ON ALL DATA TO app_rw;
GRANT ROLE app_rw TO $user;
