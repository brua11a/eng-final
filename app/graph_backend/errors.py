from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import ResponseValidationError
from fastapi.responses import JSONResponse
from neo4j.exceptions import Neo4jError


def db_err(exc: Neo4jError) -> str:
    message = getattr(exc, "message", None)
    return message or str(exc)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(Neo4jError)
    async def neo4j_error_handler(_request: Request, exc: Neo4jError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": db_err(exc)})

    @app.exception_handler(ResponseValidationError)
    async def response_validation_handler(
        _request: Request, _exc: ResponseValidationError
    ) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": "Invalid response data"})

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, HTTPException):
            raise exc
        return JSONResponse(status_code=400, content={"detail": str(exc)})
