"""ProcureFlow – app-level constants and path resolution."""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths – resolved from *this* file so the server works from any CWD
# ---------------------------------------------------------------------------
_UTILS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = _UTILS_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
FRONTEND_PAGES_DIR = FRONTEND_DIR / "pages"
STATIC_DIR = FRONTEND_DIR  # mounted at /static
SHARED_DATA_DIR = PROJECT_ROOT / "shared" / "data"

# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
API_PREFIX = "/api/v1"

# ---------------------------------------------------------------------------
# CORS – configurable via CORS_ORIGINS env var (comma-separated).
# Falls back to localhost defaults for local development.
# ---------------------------------------------------------------------------
_DEFAULT_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

_env_origins = os.environ.get("CORS_ORIGINS", "")
ALLOWED_ORIGINS: list[str] = (
    [o.strip() for o in _env_origins.split(",") if o.strip()]
    if _env_origins
    else _DEFAULT_ORIGINS
)

# ---------------------------------------------------------------------------
# App metadata
# ---------------------------------------------------------------------------
APP_TITLE = "ProcureFlow Agent"
APP_VERSION = "1.0"
