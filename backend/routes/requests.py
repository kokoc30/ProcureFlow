"""ProcureFlow – /requests route handlers."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, field_validator

from backend.audit import record_event
from backend.database import db
from backend.models import Request
from backend.services.intake_service import run_intake
from backend.services.summary_service import build_request_summary
from backend.utils.enums import AuditAction, RequestStatus

router = APIRouter(prefix="/requests", tags=["requests"])


# ---------------------------------------------------------------------------
# Input schema
# ---------------------------------------------------------------------------

class CreateRequestBody(BaseModel):
    """Fields accepted when creating a new purchase request."""

    requester_id: str
    department: str
    cost_center: str | None = None
    title: str = ""
    description: str = ""
    requested_items: list[str]
    justification: str | None = None
    delivery_date: str | None = None

    @field_validator("requested_items")
    @classmethod
    def at_least_one_item(cls, v: list[str]) -> list[str]:
        cleaned = [s.strip() for s in v if s.strip()]
        if not cleaned:
            raise ValueError("requested_items must contain at least one non-blank entry")
        return cleaned


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_cost_center(code: str) -> bool:
    """Return True if *code* matches any department's cost_center."""
    return any(d.get("cost_center") == code for d in db.departments)


# ---------------------------------------------------------------------------
# POST /requests – create a new purchase request
# ---------------------------------------------------------------------------

@router.post("", status_code=201)
async def create_request(body: CreateRequestBody):
    # Requester must exist in seed data
    user = db.get_user(body.requester_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Requester not found")

    # Cost center validation (when provided)
    if body.cost_center and not _valid_cost_center(body.cost_center):
        raise HTTPException(status_code=422, detail="Invalid cost_center")

    # Determine initial status
    missing_info = (not body.justification) or (not body.cost_center)
    status = (
        RequestStatus.clarification if missing_info else RequestStatus.policy_review
    )

    now = datetime.now(timezone.utc).isoformat()

    req = Request(
        id=uuid.uuid4().hex,
        requester_id=body.requester_id,
        department=body.department,
        cost_center=body.cost_center,
        title=body.title,
        description=body.description,
        requested_items=body.requested_items,
        justification=body.justification,
        delivery_date=body.delivery_date,
        status=status,
        created_at=now,
        updated_at=now,
    )
    db.add_request(req)

    record_event(
        request_id=req.id,
        action=AuditAction.request_created,
        actor_id=body.requester_id,
    )

    # Auto-create clarification records when intake detects missing fields
    if status == RequestStatus.clarification:
        try:
            run_intake(req.id)
        except Exception:
            pass  # Non-critical: clarifications can be triggered later

    return req.model_dump()


# ---------------------------------------------------------------------------
# GET /requests – paginated list with optional filters
# ---------------------------------------------------------------------------

@router.get("")
async def list_requests(
    requester_id: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    results = db.list_requests(requester_id=requester_id, status=status)

    # Stable ordering: newest first
    results.sort(key=lambda r: r.created_at, reverse=True)

    total = len(results)
    start = (page - 1) * page_size
    page_items = results[start : start + page_size]

    return {
        "data": [r.model_dump() for r in page_items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ---------------------------------------------------------------------------
# GET /requests/{request_id} – single request with linked entities
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# GET /requests/{request_id}/clarifications – list clarifications for a request
# ---------------------------------------------------------------------------

@router.get("/{request_id}/clarifications")
async def list_request_clarifications(request_id: str):
    req = db.get_request(request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")
    clars = db.list_clarifications(request_id)
    return [c.model_dump() for c in clars]


# ---------------------------------------------------------------------------
# GET /requests/{request_id} – single request with linked entities
# ---------------------------------------------------------------------------

@router.get("/{request_id}")
async def get_request(request_id: str):
    req = db.get_request(request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")

    result = req.model_dump()

    # Attach linked entities (empty until later workflow steps populate them)
    result["clarifications"] = [
        c.model_dump() for c in db.list_clarifications(request_id)
    ]
    result["approval_tasks"] = [
        t.model_dump() for t in db.list_tasks_for_request(request_id)
    ]
    result["purchase_order"] = None
    if req.po_id:
        po = db.get_po(req.po_id)
        result["purchase_order"] = po.model_dump() if po else None

    policy_result = db.get_policy_result(request_id)
    result["policy_result"] = (
        policy_result.model_dump() if policy_result else None
    )

    result["audit_events"] = [
        e.model_dump() for e in db.list_audit_events(request_id)
    ]

    result["summary"] = build_request_summary(request_id)

    return result
