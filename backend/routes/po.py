"""ProcureFlow – /po route handlers.

Routes
------
POST /po/generate – generate a PO draft from a matched request
GET  /po/{po_id}  – retrieve a PO by ID
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.database import db
from backend.services.po_generator import generate_purchase_order

router = APIRouter(prefix="/po", tags=["purchase-orders"])


# ---------------------------------------------------------------------------
# Input schema
# ---------------------------------------------------------------------------

class GeneratePOBody(BaseModel):
    request_id: str


# ---------------------------------------------------------------------------
# POST /po/generate
# ---------------------------------------------------------------------------

@router.post("/generate", status_code=201)
async def generate_po_route(body: GeneratePOBody):
    po = generate_purchase_order(body.request_id)
    return po.model_dump()


# ---------------------------------------------------------------------------
# GET /po/{po_id}
# ---------------------------------------------------------------------------

@router.get("/{po_id}")
async def get_po_route(po_id: str):
    po = db.get_po(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return po.model_dump()
