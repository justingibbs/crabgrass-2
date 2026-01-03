"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from .config import settings
from .db.connection import get_connection, close_connection
from .db.migrations import run_migrations
from .api.routes import auth, ideas, agent, coherence
from .api import sse

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("application_starting")

    # Initialize database and run migrations
    get_connection()
    run_migrations()

    yield

    # Shutdown
    close_connection()
    logger.info("application_stopped")


app = FastAPI(
    title="Crabgrass",
    description="Innovation acceleration platform with AI-powered idea coaching",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(ideas.router)
app.include_router(agent.router)
app.include_router(coherence.router)
app.include_router(sse.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
