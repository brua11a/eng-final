from typing import Any

from neo4j import AsyncSession


def native(value: Any) -> Any:
    if isinstance(value, list):
        return [native(item) for item in value]
    if isinstance(value, dict):
        return {key: native(item) for key, item in value.items()}
    if hasattr(value, "to_native"):
        return value.to_native()
    return value


async def run(session: AsyncSession, query: str, **params: Any) -> list[dict[str, Any]]:
    result = await session.run(query, params)
    return [native(record.data()) async for record in result]


async def one(session: AsyncSession, query: str, **params: Any) -> dict[str, Any] | None:
    rows = await run(session, query, **params)
    return rows[0] if rows else None


async def tx_one(tx: Any, query: str, **params: Any) -> dict[str, Any] | None:
    result = await tx.run(query, params)
    rows = [native(record.data()) async for record in result]
    return rows[0] if rows else None


async def next_id(session: AsyncSession, label: str) -> int:
    row = await one(
        session,
        f"OPTIONAL MATCH (n:{label}) RETURN coalesce(max(n.id), 0) + 1 AS id",
    )
    return int(row["id"])
