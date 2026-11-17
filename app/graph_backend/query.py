from typing import Any

from uuid import uuid4

from neo4j import AsyncSession, AsyncTransaction

Runner = AsyncSession | AsyncTransaction


def native(value: Any) -> Any:
    if isinstance(value, list):
        return [native(item) for item in value]
    if isinstance(value, dict):
        return {key: native(item) for key, item in value.items()}
    if hasattr(value, "to_native"):
        return value.to_native()
    return value


async def run(runner: Runner, query: str, **params: Any) -> list[dict[str, Any]]:
    result = await runner.run(query, params)
    return [native(record.data()) async for record in result]


async def one(runner: Runner, query: str, **params: Any) -> dict[str, Any] | None:
    rows = await run(runner, query, **params)
    return rows[0] if rows else None


def new_id() -> str:
    return str(uuid4())

