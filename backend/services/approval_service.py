"""ProcureFlow – approval workflow service.

Creates approval tasks from policy-required approver roles,
records decisions, and transitions request status on completion.
All logic is deterministic; approver assignment uses seed personas.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException

from backend.audit import record_event
from backend.database import db
from backend.models import ApprovalTask
from backend.utils.enums import (
    ApprovalDecision,
    AuditAction,
    ClarificationStatus,
    RequestStatus,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------------
# Start approval
# ------------------------------------------------------------------

def start_approval(request_id: str) -> list[ApprovalTask]:
    """Create approval tasks for *request_id* based on the policy result.

    One task per required approver role, assigned to the mock persona
    for that role from personas.json.

    Raises
    ------
    HTTPException 404 – request not found.
    HTTPException 409 – request not in ``pending_approval`` status.
    HTTPException 409 – pending clarifications still exist.
    HTTPException 409 – approval tasks already created.
    HTTPException 422 – no policy result or no required approvers.
    """
    req = db.get_request(request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")

    if req.status != RequestStatus.pending_approval:
        raise HTTPException(
            status_code=409,
            detail=f"Request status is '{req.status.value}'; "
                   f"approval can only start when status is 'pending_approval'",
        )

    # Guard: no pending clarifications
    clars = db.list_clarifications(request_id)
    pending_clars = [
        c for c in clars if c.status != ClarificationStatus.answered
    ]
    if pending_clars:
        raise HTTPException(
            status_code=409,
            detail=f"{len(pending_clars)} clarification(s) still pending; "
                   f"resolve them before starting approval",
        )

    # Guard: idempotency — tasks already created
    existing_tasks = db.list_tasks_for_request(request_id)
    if existing_tasks:
        raise HTTPException(
            status_code=409,
            detail="Approval tasks have already been created for this request",
        )

    # Load policy result
    policy_result = db.get_policy_result(request_id)
    if policy_result is None or not policy_result.required_approvers:
        raise HTTPException(
            status_code=422,
            detail="No policy result with required approvers found for this request",
        )

    # Create one task per required role
    now = _now_iso()
    tasks: list[ApprovalTask] = []

    for role in policy_result.required_approvers:
        approver_id = db.get_approver_for_role(role.value)

        task = ApprovalTask(
            id=uuid.uuid4().hex,
            request_id=request_id,
            role=role,
            approver_id=approver_id,
            decision=ApprovalDecision.pending,
            created_at=now,
        )
        db.add_approval_task(task)
        tasks.append(task)

        # Resolve approver name for audit detail
        approver_name = "unassigned"
        if approver_id:
            user = db.get_user(approver_id)
            if user:
                approver_name = user.name

        record_event(
            request_id=request_id,
            action=AuditAction.approval_assigned,
            detail=f"Assigned {role.value} approval to {approver_name}",
        )

    # Link task IDs to request
    db.update_request(
        request_id,
        approval_ids=[t.id for t in tasks],
    )

    return tasks


# ------------------------------------------------------------------
# Record decision
# ------------------------------------------------------------------

_VALID_DECISIONS = {ApprovalDecision.approved, ApprovalDecision.rejected}


def record_decision(
    task_id: str,
    approver_id: str,
    decision: str,
    comment: str | None = None,
) -> dict:
    """Record a decision on an approval task and cascade status changes.

    Returns ``{"task": ApprovalTask, "request": Request}``.

    Raises
    ------
    HTTPException 404 – task not found.
    HTTPException 409 – task already decided.
    HTTPException 422 – invalid decision value.
    HTTPException 403 – approver_id does not match assigned approver.
    """
    task = db.get_approval_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Approval task not found")

    # Guard: already decided
    if task.decision != ApprovalDecision.pending:
        raise HTTPException(
            status_code=409,
            detail=f"Task has already been decided as '{task.decision.value}'",
        )

    # Validate decision value
    try:
        decision_enum = ApprovalDecision(decision)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid decision '{decision}'; must be 'approved' or 'rejected'",
        )

    if decision_enum not in _VALID_DECISIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid decision '{decision}'; must be 'approved' or 'rejected'",
        )

    # Guard: approver identity
    if task.approver_id and approver_id != task.approver_id:
        raise HTTPException(
            status_code=403,
            detail="Only the assigned approver can decide this task",
        )

    # Persist decision
    updated_task = db.decide_task(
        task_id=task_id,
        decision=decision,
        comment=comment,
    )

    # Audit
    comment_note = f" — {comment}" if comment else ""
    record_event(
        request_id=task.request_id,
        action=AuditAction.approval_decided,
        actor_id=approver_id,
        detail=f"{task.role.value} {decision}{comment_note}",
    )

    # Cascade: check all tasks for this request
    all_tasks = db.list_tasks_for_request(task.request_id)

    any_rejected = any(
        t.decision == ApprovalDecision.rejected for t in all_tasks
    )
    all_approved = all(
        t.decision == ApprovalDecision.approved for t in all_tasks
    )

    req = db.get_request(task.request_id)

    if any_rejected:
        req = db.update_request(task.request_id, status=RequestStatus.rejected)
    elif all_approved:
        req = db.update_request(task.request_id, status=RequestStatus.approved)

    return {"task": updated_task, "request": req}
