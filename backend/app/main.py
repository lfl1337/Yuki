"""
Yuki FastAPI application — v2.0.3
Local-only: binds to 127.0.0.1 exclusively.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .config import settings
from .database import init_db
from .logger import get_entries
from .middleware.audit import AuditMiddleware
from .middleware.rate_limit import limiter
from .routers import download, history, player, tagger, converter, updater, settings_router, system

logger = logging.getLogger("yuki.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Yuki backend starting — data_dir=%s", settings.data_dir)
    await init_db()

    # Give downloader service access to current event loop for thread→async bridge
    from .services import downloader as dl_service
    dl_service.set_event_loop(asyncio.get_event_loop())

    logger.info("Backend ready on port %s", settings.port)
    yield

    # Shutdown
    logger.info("Backend shutting down")
    from .services import player as player_service
    try:
        player_service.get_player().shutdown()
    except Exception:
        pass
    from .services import downloader as dl_service
    dl_service.cancel_all()


app = FastAPI(
    title="Yuki Backend",
    version="2.1.3",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

# --- Middleware (order matters: added last = outermost) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:1421",    # Vite dev server (specific port)
        "tauri://localhost",         # Tauri production
        "https://tauri.localhost",   # Tauri production (alternate)
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin"],
)
app.add_middleware(AuditMiddleware)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- Routers ---
app.include_router(download.router, prefix="/api/v1")
app.include_router(history.router, prefix="/api/v1")
app.include_router(player.router, prefix="/api/v1")
app.include_router(tagger.router, prefix="/api/v1")
app.include_router(converter.router, prefix="/api/v1")
app.include_router(updater.router, prefix="/api/v1")
app.include_router(settings_router.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "2.0.3",
        "service": "yuki-backend",
        "port": settings.port,
    }


@app.get("/api/v1/logs")
async def get_logs():
    return {"entries": get_entries()}
