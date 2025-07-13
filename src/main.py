from fastapi import Depends, FastAPI, HTTPException, APIRouter
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
import os

from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import traceback
import logging

logger = logging.getLogger("uvicorn.error")

from . import models
from .database import async_engine, get_async_db, init_db, close_db
from .auth.api import router as auth_router
from .onboarding.api import router as onboarding_router
from .webhooks.api import router as webhooks_router
from .habits.api import router as habits_router
from .friends.api import router as friends_router
from .chats.api import router as chats_router
from .posts.api import router as posts_router
from .support import router as support_router


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

# Mount static files immediately after app creation
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=200
)

@app.on_event("startup")
async def startup_event():
    async with async_engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

# Main API router with versioning
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router, prefix="/users", tags=["Users"])
api_router.include_router(onboarding_router, prefix="/onboarding", tags=["Onboarding"])
api_router.include_router(habits_router, prefix="/habits", tags=["Habits"])
api_router.include_router(friends_router, prefix="/friends", tags=["Friends"])
api_router.include_router(chats_router, prefix="/chats", tags=["Chats"])
api_router.include_router(posts_router, tags=["Posts"])
api_router.include_router(support_router, prefix="/support", tags=["Support"])

app.include_router(api_router)
app.include_router(webhooks_router, tags=["webhooks"])

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    body = await request.body()
    logger.error(
        f"[POSTS] Validation error for request {request.url}: {exc.errors()}\n"
        f"Body: {body}\n"
        f"Traceback: {traceback.format_exc()}"
    )
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )

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


