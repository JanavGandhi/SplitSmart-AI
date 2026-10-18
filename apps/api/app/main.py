"""
SplitSmart AI — FastAPI Application Entry Point

Features:
- Async lifespan for DB/Redis initialization
- CORS middleware with configurable origins
- Global exception handlers
- Structured logging via structlog
- API v1 router mounting
"""
import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import create_engine, init_db
from app.api.v1.health import router as health_router
from app.api.v1.groups import router as groups_router
from app.api.v1.sandbox import router as sandbox_router
from app.api.v1.ledger import router as ledger_router
from app.api.v1.stubs import (
    auth_router,
    receipts_router,
    rooms_router,
    copilot_router,
    metrics_router,
)

# ── Logging ───────────────────────────────────────────────────────────────────
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)
logger = structlog.get_logger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialize DB engine. Shutdown: dispose engine."""
    settings = get_settings()
    logger.info(
        "SplitSmart AI starting up",
        env=settings.app_env,
        ocr_mode="mock" if settings.use_mock_ocr else "gemini",
    )

    # Initialize async DB engine
    db_engine = create_engine()
    init_db(db_engine)
    logger.info("Database engine initialized", url=settings.database_url[:50] + "...")

    yield

    # Cleanup
    await db_engine.dispose()
    logger.info("Database engine disposed — shutdown complete")


# ── App Factory ───────────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "SplitSmart AI — Real-time multiplayer receipt splitting with "
            "Vision AI, exact paise arithmetic, and Min-Cash-Flow debt simplification."
        ),
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception Handlers ────────────────────────────────────────────────────
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": str(exc), "type": "validation_error"},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error", "type": "server_error"},
        )

    # ── Routers ───────────────────────────────────────────────────────────────
    api_prefix = "/api/v1"

    app.include_router(health_router, prefix=api_prefix)
    app.include_router(auth_router, prefix=api_prefix)
    app.include_router(groups_router, prefix=api_prefix)
    app.include_router(receipts_router, prefix=api_prefix)
    app.include_router(rooms_router, prefix=api_prefix)
    app.include_router(sandbox_router, prefix=api_prefix)
    app.include_router(ledger_router, prefix=api_prefix)
    app.include_router(copilot_router, prefix=api_prefix)
    app.include_router(metrics_router, prefix=api_prefix)

    # ── Root redirect ─────────────────────────────────────────────────────────
    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "message": "SplitSmart AI API",
            "version": settings.app_version,
            "docs": "/api/docs",
            "health": "/api/v1/health",
        }

    return app


app = create_app()
