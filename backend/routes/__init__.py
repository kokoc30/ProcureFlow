"""Router registration – the single place to wire up API route modules."""

from fastapi import FastAPI

from backend.utils.settings import API_PREFIX

# Import routers as they are implemented:
from backend.routes.requests import router as requests_router
from backend.routes.clarifications import router as clarifications_router
from backend.routes.policy import router as policy_router
from backend.routes.catalog import router as catalog_router
from backend.routes.approvals import router as approvals_router
from backend.routes.audit import router as audit_router
from backend.routes.po import router as po_router
from backend.routes.agents import router as agents_router


def include_routers(app: FastAPI) -> None:
    """Register all API routers under the shared prefix.

    Each router defines its own sub-prefix (e.g. ``/requests``).
    This function adds the ``/api/v1`` prefix so the final paths
    become ``/api/v1/requests``, ``/api/v1/approvals``, etc.

    To add a new router:
      1. Create ``backend/routes/<name>.py`` with ``router = APIRouter(...)``
      2. Import it above
      3. Add ``app.include_router(<name>_router, prefix=API_PREFIX)`` below
    """
    app.include_router(requests_router, prefix=API_PREFIX)
    app.include_router(clarifications_router, prefix=API_PREFIX)
    app.include_router(policy_router, prefix=API_PREFIX)
    app.include_router(catalog_router, prefix=API_PREFIX)
    app.include_router(approvals_router, prefix=API_PREFIX)
    app.include_router(audit_router, prefix=API_PREFIX)
    app.include_router(po_router, prefix=API_PREFIX)
    app.include_router(agents_router, prefix=API_PREFIX)
