from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, brief, portfolio, websocket
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Database schema is managed by Alembic; run `alembic upgrade head` before
    # starting the server (see backend/ local dev instructions in the README).
    # Registry of live alert WebSocket connections, keyed by user_id.
    app.state.connections = {}
    yield


app = FastAPI(
    title="Watchman",
    description="AI-powered proactive portfolio intelligence",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # Local Vite dev server.
        "http://localhost:5173",
        # Production frontend (Cloud Run, nginx/React).
        "https://watchman-frontend-828211648682.australia-southeast1.run.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(portfolio.router, prefix="/api/v1")
app.include_router(brief.router, prefix="/api/v1")
app.include_router(websocket.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "env": settings.APP_ENV}


@app.get("/root")
async def root() -> dict:
    return {
        "name": "Watchman",
        "tagline": "Most financial tools answer questions. Watchman asks them first.",
    }
