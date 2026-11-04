from typing import Any

from uuid import uuid4

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


def new_id() -> str:
    return str(uuid4())


async def next_id(session: AsyncSession, label: str) -> str:
    """Return a new unique id for a domain node (label ignored; kept for call-site compatibility)."""
    del session, label
    return new_id()
