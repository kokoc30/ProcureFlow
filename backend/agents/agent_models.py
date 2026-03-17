"""ProcureFlow -- Pydantic output models for all agent tools.

Each model defines the structured contract an agent returns.  The
``ai_available`` field signals whether the content was AI-generated
or filled from a deterministic fallback.
"""

from __future__ import annotations

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Intake agent
# ---------------------------------------------------------------------------

class SuggestedQuestion(BaseModel):
    """A single clarification question suggestion."""

    field: str
    question: str
    reason: str


class IntakeAnalysis(BaseModel):
    """Output of the intake agent."""

    request_id: str
    missing_fields: list[str]
    suggested_questions: list[SuggestedQuestion]
    intake_summary: str
    ai_available: bool


# ---------------------------------------------------------------------------
# Policy agent
# ---------------------------------------------------------------------------

class FlagExplanation(BaseModel):
    """Human-friendly explanation of one policy flag."""

    rule_name: str
    passed: bool
    explanation: str


class PolicyExplanation(BaseModel):
    """Output of the policy agent."""

    request_id: str
    business_summary: str
    flag_explanations: list[FlagExplanation]
    next_steps: str
    ai_available: bool


# ---------------------------------------------------------------------------
# Catalog agent
# ---------------------------------------------------------------------------

class ItemExplanation(BaseModel):
    """Explanation for one matched or unresolved catalog item."""

    original_text: str
    matched_to: str | None = None
    confidence_note: str


class CatalogExplanation(BaseModel):
    """Output of the catalog agent."""

    request_id: str | None = None
    match_narrative: str
    item_explanations: list[ItemExplanation]
    unresolved_guidance: str
    ai_available: bool


# ---------------------------------------------------------------------------
# Approval agent
# ---------------------------------------------------------------------------

class ApprovalNotification(BaseModel):
    """Output of the approval agent."""

    request_id: str
    notification_summary: str
    line_items_summary: str
    policy_context: str
    urgency_note: str
    ai_available: bool
