import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import ResponseValidationError
from fastapi.responses import JSONResponse
from neo4j.exceptions import ClientError, ConstraintError, Neo4jError

# Every error response has the same shape: {"detail": "<message>"} with a 4xx or 5xx status.
#   400 - the database rejected the query parameters (e.g. an invalid date)
#   401 - missing or invalid token, wrong login or password
#   403 - the caller's role or relations do not allow this operation
#   404 - a resource named in the path or the body does not exist
#   409 - the operation conflicts with the current state (duplicate, full group, last role)
#   422 - the request is well-formed but its values are invalid
#   500 - unexpected server or database error

logger = logging.getLogger(__name__)


def db_err(exc: Neo4jError) -> str:
    message = getattr(exc, "message", None)
    return message or str(exc)


def not_found(what: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{what} not found")


def forbidden(detail: str = "Forbidden") -> HTTPException:
    return HTTPException(status_code=403, detail=detail)


def conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=409, detail=detail)


def invalid(detail: str) -> HTTPException:
    return HTTPException(status_code=422, detail=detail)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ConstraintError)
    async def constraint_error_handler(_request: Request, exc: ConstraintError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": db_err(exc)})

    @app.exception_handler(ClientError)
    async def client_error_handler(_request: Request, exc: ClientError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": db_err(exc)})

    @app.exception_handler(Neo4jError)
    async def neo4j_error_handler(_request: Request, exc: Neo4jError) -> JSONResponse:
        logger.error("Database error: %s", db_err(exc))
        return JSONResponse(status_code=500, content={"detail": "Database error"})

    @app.exception_handler(ResponseValidationError)
    async def response_validation_handler(
        _request: Request, exc: ResponseValidationError
    ) -> JSONResponse:
        logger.error("Invalid response data: %s", exc.errors())
        return JSONResponse(status_code=500, content={"detail": "Invalid response data"})

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error", exc_info=exc)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
