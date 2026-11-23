from typing import Any

from psycopg import AsyncConnection


async def run(conn: AsyncConnection, query: str, **params: Any) -> list[dict[str, Any]]:
    # Parameters are sent separately from the query text (%(name)s placeholders),
    # as in the graph backend (5.5.5).
    async with conn.cursor() as cur:
        await cur.execute(query, params)
        return await cur.fetchall() if cur.description else []


async def one(conn: AsyncConnection, query: str, **params: Any) -> dict[str, Any] | None:
    rows = await run(conn, query, **params)
    return rows[0] if rows else None
