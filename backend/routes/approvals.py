"""ProcureFlow – /approvals route handlers.

Routes
------
POST /approvals/start               – create approval tasks from policy result
POST /approvals/{task_id}/decide     – record an approver decision
GET  /approvals/{task_id}            – retrieve a single approval task
GET  /approvals                      – list tasks (optionally filtered by approver)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.database import db
from backend.services.approval_service import record_decision, start_approval

router = APIRouter(prefix="/approvals", tags=["approvals"])


# ---------------------------------------------------------------------------
# Input schemas
# ---------------------------------------------------------------------------

class StartApprovalBody(BaseModel):
    request_id: str


class DecisionBody(BaseModel):
    approver_id: str
    decision: str
    comment: str | None = None


# ---------------------------------------------------------------------------
# POST /approvals/start
# ---------------------------------------------------------------------------

@router.post("/start", status_code=201)
async def start_approval_route(body: StartApprovalBody):
    tasks = start_approval(body.request_id)
    return [t.model_dump() for t in tasks]


# ---------------------------------------------------------------------------
# POST /approvals/{task_id}/decide
# ---------------------------------------------------------------------------

@router.post("/{task_id}/decide")
async def decide_route(task_id: str, body: DecisionBody):
    result = record_decision(
        task_id=task_id,
        approver_id=body.approver_id,
        decision=body.decision,
        comment=body.comment,
    )
    return {
        "task": result["task"].model_dump(),
        "request": result["request"].model_dump(),
    }


# ---------------------------------------------------------------------------
# GET /approvals/{task_id}
# ---------------------------------------------------------------------------

@router.get("/{task_id}")
async def get_task_route(task_id: str):
    task = db.get_approval_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Approval task not found")
    return task.model_dump()


# ---------------------------------------------------------------------------
# GET /approvals?approver_id=...
# ---------------------------------------------------------------------------

@router.get("")
async def list_tasks_route(approver_id: str | None = Query(None)):
    if approver_id:
        tasks = db.list_tasks_for_user(approver_id)
    else:
        tasks = list(db.approval_tasks.values())
    return [t.model_dump() for t in tasks]
