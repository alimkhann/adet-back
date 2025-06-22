from fastapi import Depends, FastAPI, HTTPException, APIRouter
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

from fastapi.middleware.cors import CORSMiddleware

from . import models
from .database import async_engine, get_async_db, init_db, close_db
from .auth.api import router as auth_router
from .onboarding.api import router as onboarding_router
from .webhooks.api import router as webhooks_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()

app = FastAPI(
    title="ädet FastAPI PostgreSQL Project",
    description="A FastAPI backend with PostgreSQL database",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.on_event("startup")
async def startup_event():
    async with async_engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

# Main API router with versioning
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router, prefix="/users", tags=["Users"])
api_router.include_router(onboarding_router, tags=["Onboarding"])

app.include_router(api_router)
app.include_router(webhooks_router) # Webhooks are not versioned with the API

@app.get("/")
async def root():
    return {"message": "Welcome to ädet's FastAPI backend with PostgreSQL!"}

@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_async_db)):
    try:
        await db.execute(text("SELECT 1"))
    except OperationalError:
        raise HTTPException(
            status_code=500, detail="Database connection failed"
        )

    return {
        "status": "ok",
        "database": "connected"
    }
