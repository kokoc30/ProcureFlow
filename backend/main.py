"""ProcureFlow Agent – FastAPI application entry point."""

from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=False)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from backend.routes import include_routers
from backend.utils.settings import (
    API_PREFIX,
    APP_TITLE,
    APP_VERSION,
    DEV_ALLOWED_ORIGINS,
    FRONTEND_DIR,
    FRONTEND_PAGES_DIR,
)

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(title=APP_TITLE, version=APP_VERSION)

# ---------------------------------------------------------------------------
# CORS – local development only; edit DEV_ALLOWED_ORIGINS in settings.py
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=DEV_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Infrastructure routes (not part of the API surface)
# ---------------------------------------------------------------------------

# Minimal 1x1 transparent ICO – prevents browser favicon 404
_FAVICON = (
    b"\x00\x00\x01\x00\x01\x00\x01\x01\x00\x00\x01\x00\x18\x00"
    b"0\x00\x00\x00\x16\x00\x00\x00(\x00\x00\x00\x01\x00\x00\x00"
    b"\x02\x00\x00\x00\x01\x00\x18\x00\x00\x00\x00\x00\x04\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
)


@app.get("/", include_in_schema=False)
async def root():
    """Serve the landing page."""
    return FileResponse(FRONTEND_PAGES_DIR / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Return a minimal favicon to suppress browser 404."""
    return Response(content=_FAVICON, media_type="image/x-icon")


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.get(f"{API_PREFIX}/health")
async def health_check():
    """Compact health probe with store statistics."""
    from backend.database import db

    return {
        "status": "ok",
        "app": APP_TITLE,
        "mode": "development",
        "store": {
            "users": len(db.users),
            "catalog": len(db.catalog),
            "policies": len(db.policies),
            "departments": len(db.departments),
            "requests": len(db.requests),
        },
    }


# ---------------------------------------------------------------------------
# Reference data endpoints (read-only seed data for form dropdowns)
# ---------------------------------------------------------------------------

@app.get(f"{API_PREFIX}/users", tags=["reference"])
async def list_users():
    """Return all mock users for form population."""
    from backend.database import db
    return [u.model_dump() for u in db.list_users()]


@app.get(f"{API_PREFIX}/departments", tags=["reference"])
async def list_departments():
    """Return all departments with cost centers."""
    from backend.database import db
    return db.get_departments()


# Register all feature routers from backend/routes/
include_routers(app)

# ---------------------------------------------------------------------------
# Static files – mounted AFTER explicit routes
# ---------------------------------------------------------------------------
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
