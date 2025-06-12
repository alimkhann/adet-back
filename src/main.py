from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi.middleware.cors import CORSMiddleware

from . import models
from .database import async_engine, get_async_db
from .auth.api import router as auth_router
from .onboarding.api import router as onboarding_router

# from pydantic import BaseModel
# from fastapi.security import HTTPBearer

# models.Base.metadata.create_all(bind=async_engine) # Remove this line

app = FastAPI(
    title="ädet FastAPI PostgreSQL Project",
    description="A FastAPI backend with PostgreSQL database",
    version="1.0.0"
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

app.include_router(auth_router)
app.include_router(onboarding_router)

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
