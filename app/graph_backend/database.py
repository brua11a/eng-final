import os

from neo4j import AsyncGraphDatabase

NEO4J_URI = os.environ["NEO4J_URI"]
NEO4J_USER = os.environ["NEO4J_USER"]
NEO4J_PASSWORD = os.environ["NEO4J_PASSWORD"]

driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

async def get_session():
    async with driver.session() as session:
        yield session


async def close_driver():
    await driver.close()


async def verify_connectivity():
    await driver.verify_connectivity()