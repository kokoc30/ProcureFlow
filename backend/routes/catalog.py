"""ProcureFlow – /catalog route handlers.

Routes
------
POST /catalog/match – match raw item text against the catalog
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from backend.services.catalog import match_items, match_request_items

router = APIRouter(prefix="/catalog", tags=["catalog"])


# ---------------------------------------------------------------------------
# Input schema
# ---------------------------------------------------------------------------

class CatalogMatchBody(BaseModel):
    """Accept request_id (persist mode) or requested_items (preview mode)."""

    request_id: str | None = None
    requested_items: list[str] | None = None


# ---------------------------------------------------------------------------
# POST /catalog/match
# ---------------------------------------------------------------------------

@router.post("/match")
async def catalog_match_route(body: CatalogMatchBody):
    if body.request_id:
        # Persist mode: load request, match, save structured items
        return match_request_items(body.request_id)

    if body.requested_items:
        # Preview mode: match only, no persistence
        return match_items(body.requested_items)

    from fastapi import HTTPException
    raise HTTPException(
        status_code=422,
        detail="Provide either request_id or requested_items",
    )
