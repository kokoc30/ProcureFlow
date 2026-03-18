"""ProcureFlow – request summary aggregation service.

Builds a computed summary dict from the current state of a request
and its linked entities.  Pure read-only computation — no side effects.
"""

from __future__ import annotations

from backend.database import db
from backend.utils.enums import (
    ApprovalDecision,
    ClarificationStatus,
    RequestStatus,
)


def _status_label(status: RequestStatus) -> str:
    """Convert a RequestStatus enum to a human-readable label."""
    labels = {
        RequestStatus.draft: "Draft",
        RequestStatus.clarification: "Clarification",
        RequestStatus.policy_review: "Policy Review",
        RequestStatus.pending_approval: "Pending Approval",
        RequestStatus.approved: "Approved",
        RequestStatus.rejected: "Rejected",
    }
    return labels.get(status, status.value)


def _build_next_action(
    req,
    clars_pending: int,
    approval_tasks: list,
    po,
) -> str:
    """Determine the next action hint based on current request state."""
    status = req.status

    if status == RequestStatus.draft:
        return "Request is in draft"

    if status == RequestStatus.clarification:
        if clars_pending == 0:
            return "Missing required information \u2014 clarifications needed"
        if clars_pending == 1:
            return "1 clarification pending \u2014 awaiting answer"
        return f"{clars_pending} clarifications pending \u2014 awaiting answers"

    if status == RequestStatus.policy_review:
        return "Ready for policy evaluation"

    if status == RequestStatus.pending_approval:
        pending = [
            t for t in approval_tasks
            if t.decision == ApprovalDecision.pending
        ]
        if pending:
            first = pending[0]
            approver_name = "unknown"
            if first.approver_id:
                user = db.get_user(first.approver_id)
                if user:
                    approver_name = user.name
            return f"Awaiting {first.role.value} approval from {approver_name}"
        return "Awaiting approval decisions"

    if status == RequestStatus.approved:
        if po:
            return f"Approved \u2014 PO {po.po_number} generated"
        return "Approved \u2014 ready for PO generation"

    if status == RequestStatus.rejected:
        rejected_tasks = [
            t for t in approval_tasks
            if t.decision == ApprovalDecision.rejected
        ]
        if rejected_tasks:
            t = rejected_tasks[0]
            reason = t.comment or "no reason given"
            approver_name = t.role.value
            if t.approver_id:
                user = db.get_user(t.approver_id)
                if user:
                    approver_name = user.name
            return f"Rejected by {approver_name} \u2014 {reason}"
        return "Rejected"

    return status.value


def build_request_summary(request_id: str) -> dict | None:
    """Build a summary dict for *request_id*.

    Returns ``None`` if the request does not exist.
    """
    req = db.get_request(request_id)
    if req is None:
        return None

    # Clarifications
    clars = db.list_clarifications(request_id)
    clars_pending = sum(
        1 for c in clars if c.status != ClarificationStatus.answered
    )
    clars_answered = len(clars) - clars_pending

    # Policy
    policy_result = db.get_policy_result(request_id)
    policy_evaluated = policy_result is not None
    required_approvers: list[str] = []
    policy_summary: str | None = None
    if policy_result:
        required_approvers = [r.value for r in policy_result.required_approvers]
        # Build a short summary from flags
        passing = [f for f in policy_result.flags if f.passed]
        if passing:
            policy_summary = passing[0].message
        elif policy_result.flags:
            policy_summary = policy_result.flags[0].message

    # Approval tasks
    approval_tasks = db.list_tasks_for_request(request_id)
    tasks_decided = sum(
        1 for t in approval_tasks
        if t.decision != ApprovalDecision.pending
    )
    tasks_pending = len(approval_tasks) - tasks_decided
    all_approved = (
        len(approval_tasks) > 0
        and all(t.decision == ApprovalDecision.approved for t in approval_tasks)
    )
    any_rejected = any(
        t.decision == ApprovalDecision.rejected for t in approval_tasks
    )

    # PO
    po = db.get_po(req.po_id) if req.po_id else None

    # Item count
    item_count = len(req.items) if req.items else len(req.requested_items)

    return {
        "status": req.status.value,
        "status_label": _status_label(req.status),
        "total_cents": req.total_cents,
        "item_count": item_count,
        # Clarification state
        "clarifications_total": len(clars),
        "clarifications_pending": clars_pending,
        "clarifications_answered": clars_answered,
        # Policy state
        "policy_evaluated": policy_evaluated,
        "policy_summary": policy_summary,
        "required_approvers": required_approvers,
        # Approval state
        "approval_tasks_total": len(approval_tasks),
        "approval_tasks_decided": tasks_decided,
        "approval_tasks_pending": tasks_pending,
        "all_approved": all_approved,
        "any_rejected": any_rejected,
        # PO state
        "has_po": po is not None,
        "po_number": po.po_number if po else None,
        "po_review_required": po.review_required if po else False,
        # Next action
        "next_action": _build_next_action(req, clars_pending, approval_tasks, po),
    }
