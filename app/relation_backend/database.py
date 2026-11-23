import os

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

# Connection string without the password (host, database, user, TLS settings); the password
# is passed separately, so it never appears in logged connection strings.
PG_CONNINFO = os.environ["PG_CONNINFO"]
PG_PASSWORD = os.environ["PG_PASSWORD"]

# One pool shared by the whole application, like the Neo4j driver (5.5.3).
pool = AsyncConnectionPool(
    PG_CONNINFO,
    kwargs={"password": PG_PASSWORD, "row_factory": dict_row},
    min_size=1,
    max_size=20,
    open=False,
)


async def get_conn():
    # One transaction per request: committed when the endpoint returns,
    # rolled back when it raises.
    async with pool.connection() as conn:
        yield conn


async def open_pool():
    await pool.open(wait=True)


async def close_pool():
    await pool.close()
