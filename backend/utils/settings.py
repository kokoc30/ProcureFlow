"""ProcureFlow – app-level constants and path resolution."""

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
# CORS – local development only; extend when deploying
# ---------------------------------------------------------------------------
DEV_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# ---------------------------------------------------------------------------
# App metadata
# ---------------------------------------------------------------------------
APP_TITLE = "ProcureFlow Agent"
APP_VERSION = "1.0"
