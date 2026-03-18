"""ProcureFlow – /audit route handlers.

Routes
------
GET /audit/{request_id}  – timeline events for a single request
GET /audit               – list all events (optionally filtered)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.database import db

router = APIRouter(prefix="/audit", tags=["audit"])


# ---------------------------------------------------------------------------
# GET /audit/{request_id} – timeline for a single request
# ---------------------------------------------------------------------------

@router.get("/{request_id}")
async def get_audit_timeline(request_id: str):
    req = db.get_request(request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")

    events = db.list_audit_events(request_id)
    # Chronological order (oldest first)
    events.sort(key=lambda e: e.created_at)
    return [e.model_dump() for e in events]


# ---------------------------------------------------------------------------
# GET /audit – list all events with optional filters
# ---------------------------------------------------------------------------

@router.get("")
async def list_audit_events(
    request_id: str | None = Query(None),
    action: str | None = Query(None),
):
    events = db.list_audit_events(request_id)

    if action:
        events = [e for e in events if e.action.value == action]

    # Chronological order (oldest first)
    events.sort(key=lambda e: e.created_at)
    return [e.model_dump() for e in events]
