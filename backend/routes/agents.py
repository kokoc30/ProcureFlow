"""ProcureFlow -- Agent API routes.

These endpoints expose the watsonx-assisted workflow layer used by
ProcureFlow. watsonx Orchestrate coordinates stage-specific tools for
intake, clarification, policy summary support, catalog support, and
approval-status handling, while deterministic Python services remain the
source of truth for thresholds, routing, totals, validation, and status
transitions.

Most endpoints are read-only. ``/run-intake`` is the exception: it
creates clarification records as a deterministic side effect after the
agent layer drafts question text.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.agents.agent_models import (
    ApprovalNotification,
    CatalogExplanation,
    IntakeAnalysis,
    PolicyExplanation,
)
from backend.agents.llm_client import get_client
from backend.agents.orchestrate_registry import registry
from backend.database import db
from backend.services.catalog import match_items

router = APIRouter(prefix="/agents", tags=["agents"])


# ---------------------------------------------------------------------------
# Status endpoint
# ---------------------------------------------------------------------------

class AgentStatusResponse(BaseModel):
    ai_available: bool
    client_type: str
    model_id: str
    registered_stages: dict[str, list[str]]


@router.get("/status", response_model=AgentStatusResponse)
def agent_status() -> AgentStatusResponse:
    """Report watsonx availability and the registered stage-to-tool map."""
    client = get_client()
    return AgentStatusResponse(
        ai_available=client.is_available(),
        client_type=client.client_type(),
        model_id=client.model_id(),
        registered_stages=registry.list_all(),
    )


# ---------------------------------------------------------------------------
# Intake analysis
# ---------------------------------------------------------------------------

@router.post(
    "/intake-analysis/{request_id}",
    response_model=IntakeAnalysis,
)
def intake_analysis(request_id: str) -> IntakeAnalysis:
    """Analyze a request for missing fields and draft clarification questions."""
    req = db.get_request(request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")

    from backend.agents.intake_agent import analyze

    return analyze(request_id)


# ---------------------------------------------------------------------------
# Intake preview (no DB writes)
# ---------------------------------------------------------------------------

class IntakePreviewBody(BaseModel):
    title: str = ""
    department: str = ""
    requested_items: list[str] = []
    justification: str | None = None
    cost_center: str | None = None
    delivery_date: str | None = None


@router.post("/intake-preview", response_model=IntakeAnalysis)
def intake_preview(body: IntakePreviewBody) -> IntakeAnalysis:
    """Preview intake analysis on unsaved form data.  Read-only, no side effects."""
    from backend.agents.intake_agent import analyze_preview

    return analyze_preview(body.model_dump())


# ---------------------------------------------------------------------------
# Policy explanation
# ---------------------------------------------------------------------------

@router.post(
    "/policy-explanation/{request_id}",
    response_model=PolicyExplanation,
)
def policy_explanation(request_id: str) -> PolicyExplanation:
    """Produce a grounded business explanation of a deterministic policy result."""
    req = db.get_request(request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")

    from backend.agents.policy_agent import explain

    return explain(request_id)


# ---------------------------------------------------------------------------
# Catalog explanation
# ---------------------------------------------------------------------------

class CatalogExplainBody(BaseModel):
    request_id: str | None = None
    requested_items: list[str] | None = None


@router.post(
    "/catalog-explanation",
    response_model=CatalogExplanation,
)
def catalog_explanation(body: CatalogExplainBody) -> CatalogExplanation:
    """Explain deterministic catalog matching results in grounded language.

    Provide either ``request_id`` (to use the request's items) or
    ``requested_items`` (for ad-hoc preview).
    """
    if body.request_id:
        req = db.get_request(body.request_id)
        if req is None:
            raise HTTPException(status_code=404, detail="Request not found")
        raw_items = req.requested_items
    elif body.requested_items:
        raw_items = body.requested_items
    else:
        raise HTTPException(
            status_code=422,
            detail="Provide either request_id or requested_items",
        )

    match_result = match_items(raw_items)

    from backend.agents.catalog_agent import explain

    return explain(match_result, request_id=body.request_id)


# ---------------------------------------------------------------------------
# Approval notification
# ---------------------------------------------------------------------------

class ApprovalNotifyBody(BaseModel):
    approver_role: str = ""


@router.post(
    "/approval-notification/{request_id}",
    response_model=ApprovalNotification,
)
def approval_notification(
    request_id: str,
    body: ApprovalNotifyBody | None = None,
) -> ApprovalNotification:
    """Draft approval-status context for an approver without recommending a decision."""
    req = db.get_request(request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")

    role = body.approver_role if body else ""

    from backend.agents.approval_agent import draft_notification

    return draft_notification(request_id, approver_role=role)


# ---------------------------------------------------------------------------
# Run intake (analyze + auto-create clarifications)
# ---------------------------------------------------------------------------

@router.post("/run-intake/{request_id}")
def run_intake(request_id: str):
    """Analyze a request for missing fields and auto-create clarifications.

    Unlike the read-only ``intake-analysis`` endpoint, this one actually
    creates Clarification records and transitions the request to
    ``clarification`` status when missing fields are detected. The
    workflow mutation remains deterministic; the agent layer only helps
    with clarification wording.
    """
    req = db.get_request(request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")

    from backend.services.intake_service import run_intake as _run_intake

    result = _run_intake(request_id)

    # Serialize the IntakeAnalysis model for JSON response
    analysis = result["analysis"]
    return {
        "analysis": analysis.model_dump(),
        "clarifications_created": result["clarifications_created"],
    }


# ---------------------------------------------------------------------------
# Run all agents for current stage
# ---------------------------------------------------------------------------

@router.post("/run-stage/{request_id}")
def run_stage(request_id: str):
    """Execute all agents registered for the request's current workflow stage.

    Returns the combined output from every agent tool that applies to
    the request's current status. This is the coordination point that a
    watsonx Orchestrate flow would call to gather stage-appropriate
    language assistance without changing deterministic business logic.
    """
    req = db.get_request(request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")

    result = registry.run_stage(request_id)

    # Serialize any Pydantic models in the results
    serialized: dict = {}
    for name, val in result.get("results", {}).items():
        if hasattr(val, "model_dump"):
            serialized[name] = val.model_dump()
        else:
            serialized[name] = val

    return {
        "stage": result["stage"],
        "results": serialized,
    }
