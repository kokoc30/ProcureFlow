"""ProcureFlow – Pydantic data models.

Single source of truth for entity design.  All field names use snake_case.
IDs are UUID4 hex strings.  Timestamps are ISO 8601 strings.
Monetary values are integers in cents to avoid floating-point issues.
"""

from __future__ import annotations

from pydantic import BaseModel, field_validator

from backend.utils.enums import (
    ApprovalDecision,
    ApproverRole,
    AuditAction,
    ClarificationStatus,
    RequestStatus,
    Urgency,
)


# ---------------------------------------------------------------------------
# User (loaded from mock data, not persisted via API)
# ---------------------------------------------------------------------------

class User(BaseModel):
    id: str
    name: str
    email: str
    department: str
    role: ApproverRole | None = None


# ---------------------------------------------------------------------------
# Item – structured, catalog-matched line item
# ---------------------------------------------------------------------------

class Item(BaseModel):
    catalog_id: str | None = None
    description: str
    quantity: int = 1
    unit_price_cents: int = 0
    vendor: str | None = None

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("quantity must be at least 1")
        return v

    @field_validator("unit_price_cents")
    @classmethod
    def price_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("unit_price_cents must be non-negative")
        return v


# ---------------------------------------------------------------------------
# Request – the core procurement entity
# ---------------------------------------------------------------------------

class Request(BaseModel):
    id: str
    requester_id: str
    department: str
    cost_center: str | None = None
    title: str = ""
    description: str = ""
    justification: str | None = None
    urgency: Urgency = Urgency.standard
    delivery_date: str | None = None

    # Intake vs structured items
    requested_items: list[str]          # raw free-form strings from the user
    items: list[Item] = []              # structured after catalog matching

    total_cents: int = 0

    status: RequestStatus = RequestStatus.draft

    # Linked entity IDs
    clarification_ids: list[str] = []
    approval_ids: list[str] = []
    po_id: str | None = None

    created_at: str
    updated_at: str

    @field_validator("requested_items")
    @classmethod
    def requested_items_not_empty(cls, v: list[str]) -> list[str]:
        cleaned = [s.strip() for s in v if s.strip()]
        if not cleaned:
            raise ValueError("requested_items must contain at least one non-blank entry")
        return cleaned

    @field_validator("total_cents")
    @classmethod
    def total_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("total_cents must be non-negative")
        return v


# ---------------------------------------------------------------------------
# Clarification – follow-up question for missing info
# ---------------------------------------------------------------------------

class Clarification(BaseModel):
    id: str
    request_id: str
    question: str
    answer: str | None = None
    field: str | None = None  # target request field (e.g. justification, cost_center)
    status: ClarificationStatus = ClarificationStatus.pending
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Policy – computed result from the policy engine (not stored as entity)
# ---------------------------------------------------------------------------

class PolicyFlag(BaseModel):
    rule_id: str
    rule_name: str
    passed: bool
    message: str


class PolicyResult(BaseModel):
    request_id: str
    passed: bool
    flags: list[PolicyFlag] = []
    required_approvers: list[ApproverRole] = []
    evaluated_at: str


# ---------------------------------------------------------------------------
# ApprovalTask – one approval action per approver role
# ---------------------------------------------------------------------------

class ApprovalTask(BaseModel):
    id: str
    request_id: str
    role: ApproverRole
    approver_id: str | None = None
    decision: ApprovalDecision = ApprovalDecision.pending
    comment: str | None = None
    decided_at: str | None = None
    created_at: str


# ---------------------------------------------------------------------------
# PurchaseOrder – generated summary / PO draft
# ---------------------------------------------------------------------------

class PurchaseOrder(BaseModel):
    id: str
    request_id: str
    po_number: str
    items: list[Item]
    total_cents: int
    vendor_summary: dict[str, int] = {}
    review_required: bool = False
    unresolved_items: list[str] = []
    summary: str
    created_at: str


# ---------------------------------------------------------------------------
# AuditEvent – immutable timeline entry
# ---------------------------------------------------------------------------

class AuditEvent(BaseModel):
    id: str
    request_id: str
    action: AuditAction
    actor_id: str | None = None
    detail: str = ""
    created_at: str
