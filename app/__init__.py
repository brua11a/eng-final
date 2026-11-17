from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.graph_backend.database import close_driver, verify_connectivity
from app.graph_backend.errors import register_exception_handlers
from app.graph_backend.routers.admin import router as admin_router
from app.graph_backend.routers.catalogue import router as catalogue_router
from app.graph_backend.routers.public import router as public_router
from app.graph_backend.routers.student import router as student_router
from app.graph_backend.routers.teacher import router as teacher_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await verify_connectivity()
    yield
    await close_driver()


# The whole API lives under /api, so it never shares a path with a page of the frontend.
API_PREFIX = "/api"

app = FastAPI(
    title="mini-usos",
    lifespan=lifespan,
    docs_url=f"{API_PREFIX}/docs",
    redoc_url=f"{API_PREFIX}/redoc",
    openapi_url=f"{API_PREFIX}/openapi.json",
)
register_exception_handlers(app)
app.include_router(public_router, prefix=API_PREFIX)
app.include_router(catalogue_router, prefix=API_PREFIX)
app.include_router(student_router, prefix=API_PREFIX)
app.include_router(teacher_router, prefix=API_PREFIX)
app.include_router(admin_router, prefix=API_PREFIX)
