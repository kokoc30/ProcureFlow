"""ProcureFlow – shared enumerations for entity status values."""

from enum import Enum


class RequestStatus(str, Enum):
    """Lifecycle states for a purchase request."""

    draft = "draft"
    clarification = "clarification"
    policy_review = "policy_review"
    pending_approval = "pending_approval"
    approved = "approved"
    rejected = "rejected"


class ClarificationStatus(str, Enum):
    """States for a single clarification question."""

    pending = "pending"
    answered = "answered"


class ApprovalDecision(str, Enum):
    """Per-task decision by an individual approver."""

    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class ApproverRole(str, Enum):
    """Roles that can appear in approval chains."""

    manager = "manager"
    dept_head = "dept_head"
    procurement = "procurement"
    finance = "finance"


class Urgency(str, Enum):
    """Request urgency levels."""

    low = "low"
    standard = "standard"
    high = "high"
    critical = "critical"


class AuditAction(str, Enum):
    """Actions recorded in the audit timeline."""

    request_created = "request_created"
    clarification_requested = "clarification_requested"
    clarification_answered = "clarification_answered"
    catalog_matched = "catalog_matched"
    catalog_review_required = "catalog_review_required"
    policy_evaluated = "policy_evaluated"
    approval_assigned = "approval_assigned"
    approval_decided = "approval_decided"
    po_generated = "po_generated"
    po_generation_blocked = "po_generation_blocked"
