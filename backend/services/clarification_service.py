"""ProcureFlow – clarification business logic.

Handles creation of follow-up questions and deterministic application
of answers back to the parent request.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException

from backend.audit import record_event
from backend.database import db
from backend.models import Clarification
from backend.utils.enums import (
    AuditAction,
    ClarificationStatus,
    RequestStatus,
)

# Request fields that can be filled deterministically from an answer.
_FILLABLE_FIELDS = {"justification", "delivery_date", "cost_center"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------------
# Create
# ------------------------------------------------------------------

def create_clarification(
    request_id: str,
    question: str,
    field: str | None = None,
) -> Clarification:
    """Create a pending clarification linked to *request_id*.

    Raises
    ------
    HTTPException 404  – request does not exist.
    HTTPException 409  – request is not in ``clarification`` status.
    """
    req = db.get_request(request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")

    if req.status != RequestStatus.clarification:
        raise HTTPException(
            status_code=409,
            detail=f"Request status is '{req.status.value}'; clarifications can only "
                   f"be created when status is 'clarification'",
        )

    now = _now_iso()
    clar = Clarification(
        id=uuid.uuid4().hex,
        request_id=request_id,
        question=question,
        field=field,
        status=ClarificationStatus.pending,
        created_at=now,
        updated_at=now,
    )
    db.add_clarification(clar)

    # Link to parent request
    db.update_request(
        request_id,
        clarification_ids=[*req.clarification_ids, clar.id],
    )

    record_event(
        request_id=request_id,
        action=AuditAction.clarification_requested,
        detail=f"Question: {question}",
    )

    return clar


# ------------------------------------------------------------------
# Answer
# ------------------------------------------------------------------

def answer_clarification(
    clarification_id: str,
    answer: str,
    user_id: str | None = None,
) -> dict:
    """Record an answer and optionally back-fill the parent request field.

    Returns ``{"clarification": Clarification, "request": Request}``.

    Raises
    ------
    HTTPException 404  – clarification does not exist.
    HTTPException 409  – already answered.
    HTTPException 422  – answer is blank.
    HTTPException 403  – user_id does not match the request owner.
    """
    clar = db.get_clarification(clarification_id)
    if clar is None:
        raise HTTPException(status_code=404, detail="Clarification not found")

    if clar.status == ClarificationStatus.answered:
        raise HTTPException(
            status_code=409,
            detail="Clarification has already been answered",
        )

    answer_text = answer.strip()
    if not answer_text:
        raise HTTPException(status_code=422, detail="Answer must not be blank")

    # Ownership check (MVP persona model)
    req = db.get_request(clar.request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Parent request not found")

    if user_id is not None and user_id != req.requester_id:
        raise HTTPException(
            status_code=403,
            detail="Only the request owner can answer clarifications",
        )

    # Persist the answer
    updated_clar = db.answer_clarification(clarification_id, answer_text)

    # Deterministic field back-fill
    request_updates: dict = {}
    if clar.field and clar.field in _FILLABLE_FIELDS:
        request_updates[clar.field] = answer_text

    # Check whether ALL clarifications for this request are now answered
    all_clars = db.list_clarifications(clar.request_id)
    all_answered = all(c.status == ClarificationStatus.answered for c in all_clars)

    if all_answered and req.status == RequestStatus.clarification:
        request_updates["status"] = RequestStatus.policy_review

    updated_req = req
    if request_updates:
        updated_req = db.update_request(clar.request_id, **request_updates)

    record_event(
        request_id=clar.request_id,
        action=AuditAction.clarification_answered,
        actor_id=user_id,
        detail=f"Answer: {answer_text}",
    )

    return {
        "clarification": updated_clar,
        "request": updated_req,
    }
