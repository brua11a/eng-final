from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import close_driver, verify_connectivity
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


app = FastAPI(title="eng-final", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(public_router)
app.include_router(catalogue_router)
app.include_router(student_router)
app.include_router(teacher_router)
app.include_router(admin_router)
