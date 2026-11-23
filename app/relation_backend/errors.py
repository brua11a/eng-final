import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from psycopg import errors as pg

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    # Same mapping as for Neo4j (graph_backend/errors.py): a violated constraint is 409,
    # a value rejected by the database is 400, anything else 500.
    @app.exception_handler(pg.IntegrityError)
    async def integrity_error_handler(_request: Request, exc: pg.IntegrityError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": exc.diag.message_primary or str(exc)})

    @app.exception_handler(pg.DataError)
    async def data_error_handler(_request: Request, exc: pg.DataError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": exc.diag.message_primary or str(exc)})

    @app.exception_handler(pg.Error)
    async def database_error_handler(_request: Request, exc: pg.Error) -> JSONResponse:
        logger.error("Database error: %s", exc)
        return JSONResponse(status_code=500, content={"detail": "Database error"})
