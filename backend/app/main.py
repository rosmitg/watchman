from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, portfolio
from app.core.config import settings
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Watchman",
    description="AI-powered proactive portfolio intelligence",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(portfolio.router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "env": settings.APP_ENV}


@app.get("/root")
async def root() -> dict:
    return {
        "name": "Watchman",
        "tagline": "Most financial tools answer questions. Watchman asks them first.",
    }
