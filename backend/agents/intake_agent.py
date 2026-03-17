"""ProcureFlow -- Intake agent tool.

Identifies missing fields on a purchase request and drafts clarification
questions.  The missing-field detection is always deterministic; the
question language is AI-generated when watsonx is available.
"""

from __future__ import annotations

import json
import logging

from backend.agents.agent_models import IntakeAnalysis, SuggestedQuestion
from backend.agents.llm_client import LLMRequest, get_client, parse_json_response
from backend.database import db

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fields that trigger clarification when absent
# ---------------------------------------------------------------------------

_CHECKABLE_FIELDS: dict[str, str] = {
    "justification": "Business justification for the purchase",
    "cost_center": "Cost center for billing",
    "delivery_date": "Requested delivery date",
}

_FALLBACK_QUESTIONS: dict[str, SuggestedQuestion] = {
    "justification": SuggestedQuestion(
        field="justification",
        question="Please provide a business justification for this purchase request.",
        reason="A justification is required for policy evaluation and approval routing.",
    ),
    "cost_center": SuggestedQuestion(
        field="cost_center",
        question="Which cost center should this purchase be charged to?",
        reason="The cost center is needed for budget tracking and department allocation.",
    ),
    "delivery_date": SuggestedQuestion(
        field="delivery_date",
        question="When do you need these items delivered?",
        reason="A delivery date helps prioritize procurement and flag urgent requests.",
    ),
}

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a procurement intake assistant for an enterprise procurement system.
Your job is to draft clear, concise clarification questions for missing
information on purchase requests.

Rules:
- Be professional and concise (1-2 sentences per question).
- Do not fabricate information. Only ask about fields that are actually missing.
- Do not infer or assume answers. Ask explicitly.
- Do not discuss policy thresholds, approval chains, or pricing.
- Use business-appropriate language suitable for an enterprise environment.
- Tailor each question to the specific request context (title, items, department).

Return your response as a JSON object with these keys:
{
  "questions": [
    {"field": "<field_name>", "question": "<question_text>", "reason": "<why_needed>"}
  ],
  "summary": "<1-2 sentence summary of what is missing>"
}
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze(request_id: str) -> IntakeAnalysis:
    """Analyze a request for missing fields and suggest clarification questions.

    **Deterministic:** Missing-field detection (checks justification,
    cost_center, delivery_date).
    **AI-assisted:** Question text drafting (falls back to templates).

    Parameters
    ----------
    request_id:
        The ID of the request to analyze.

    Returns
    -------
    IntakeAnalysis
        Structured analysis with missing fields, suggested questions, and
        a summary.  ``ai_available`` indicates whether AI language was used.

    Output schema::

        {
          "request_id": str,
          "missing_fields": ["justification", "cost_center", ...],
          "suggested_questions": [
            {"field": str, "question": str, "reason": str}
          ],
          "intake_summary": str,
          "ai_available": bool
        }

    System-prompt guardrails:
        - Be professional and concise (1-2 sentences per question).
        - Do not fabricate information or infer answers.
        - Do not discuss policy thresholds, approval chains, or pricing.
        - Only ask about fields that are actually missing.
    """
    req = db.get_request(request_id)
    if req is None:
        return IntakeAnalysis(
            request_id=request_id,
            missing_fields=[],
            suggested_questions=[],
            intake_summary="Request not found.",
            ai_available=False,
        )

    # --- Deterministic: identify missing fields ---
    missing: list[str] = []
    for field_name in _CHECKABLE_FIELDS:
        value = getattr(req, field_name, None)
        if not value or (isinstance(value, str) and not value.strip()):
            missing.append(field_name)

    if not missing:
        return IntakeAnalysis(
            request_id=request_id,
            missing_fields=[],
            suggested_questions=[],
            intake_summary="All required fields are present. No clarifications needed.",
            ai_available=False,
        )

    # --- Try AI-generated questions ---
    client = get_client()
    if client.is_available():
        questions, summary, ai_ok = _generate_ai_questions(req, missing)
        if ai_ok:
            return IntakeAnalysis(
                request_id=request_id,
                missing_fields=missing,
                suggested_questions=questions,
                intake_summary=summary,
                ai_available=True,
            )

    # --- Deterministic fallback ---
    fallback_qs = [_FALLBACK_QUESTIONS[f] for f in missing if f in _FALLBACK_QUESTIONS]
    field_labels = [_CHECKABLE_FIELDS.get(f, f) for f in missing]
    summary = f"Missing information: {', '.join(field_labels)}."

    return IntakeAnalysis(
        request_id=request_id,
        missing_fields=missing,
        suggested_questions=fallback_qs,
        intake_summary=summary,
        ai_available=False,
    )


# ---------------------------------------------------------------------------
# AI generation helper
# ---------------------------------------------------------------------------

def _generate_ai_questions(
    req, missing: list[str]
) -> tuple[list[SuggestedQuestion], str, bool]:
    """Call watsonx to draft questions.  Returns (questions, summary, success)."""
    client = get_client()

    items_text = ", ".join(req.requested_items[:10])
    missing_labels = [_CHECKABLE_FIELDS.get(f, f) for f in missing]

    user_message = json.dumps(
        {
            "title": req.title,
            "department": req.department,
            "requested_items": items_text,
            "missing_fields": missing,
            "missing_field_descriptions": missing_labels,
        },
        indent=2,
    )

    response = client.generate(
        LLMRequest(
            system_prompt=_SYSTEM_PROMPT,
            user_message=user_message,
            max_tokens=512,
            temperature=0.2,
        )
    )

    if not response.ai_available or not response.content:
        return [], "", False

    parsed = parse_json_response(response.content)
    if not isinstance(parsed, dict):
        logger.warning("intake_agent: could not parse LLM response as JSON")
        return [], "", False

    questions: list[SuggestedQuestion] = []
    raw_qs = parsed.get("questions", [])
    if isinstance(raw_qs, list):
        for q in raw_qs:
            if isinstance(q, dict) and "field" in q and "question" in q:
                questions.append(
                    SuggestedQuestion(
                        field=q["field"],
                        question=q["question"],
                        reason=q.get("reason", ""),
                    )
                )

    summary = parsed.get("summary", "")
    if not summary:
        field_labels = [_CHECKABLE_FIELDS.get(f, f) for f in missing]
        summary = f"Missing information: {', '.join(field_labels)}."

    return questions, summary, True


# ---------------------------------------------------------------------------
# Preview analysis (no DB lookup)
# ---------------------------------------------------------------------------

def analyze_preview(data: dict) -> IntakeAnalysis:
    """Same logic as :func:`analyze` but operates on raw form data.

    This is used by the ``/agents/intake-preview`` endpoint so the
    frontend can show AI intake assistance *before* the request is saved.
    Read-only — no database writes, no status transitions.

    Parameters
    ----------
    data:
        Keys: ``title``, ``department``, ``requested_items``,
        ``justification``, ``cost_center``, ``delivery_date``.
    """

    class _Preview:
        pass

    preview = _Preview()
    preview.title = data.get("title", "")
    preview.department = data.get("department", "")
    preview.requested_items = data.get("requested_items", [])
    preview.justification = data.get("justification")
    preview.cost_center = data.get("cost_center")
    preview.delivery_date = data.get("delivery_date")

    # --- Deterministic: identify missing fields ---
    missing: list[str] = []
    for field_name in _CHECKABLE_FIELDS:
        value = getattr(preview, field_name, None)
        if not value or (isinstance(value, str) and not value.strip()):
            missing.append(field_name)

    if not missing:
        return IntakeAnalysis(
            request_id="",
            missing_fields=[],
            suggested_questions=[],
            intake_summary="All required fields are present. No clarifications needed.",
            ai_available=False,
        )

    # --- Try AI-generated questions ---
    client = get_client()
    if client.is_available():
        questions, summary, ai_ok = _generate_ai_questions(preview, missing)
        if ai_ok:
            return IntakeAnalysis(
                request_id="",
                missing_fields=missing,
                suggested_questions=questions,
                intake_summary=summary,
                ai_available=True,
            )

    # --- Deterministic fallback ---
    fallback_qs = [_FALLBACK_QUESTIONS[f] for f in missing if f in _FALLBACK_QUESTIONS]
    field_labels = [_CHECKABLE_FIELDS.get(f, f) for f in missing]
    summary = f"Missing information: {', '.join(field_labels)}."

    return IntakeAnalysis(
        request_id="",
        missing_fields=missing,
        suggested_questions=fallback_qs,
        intake_summary=summary,
        ai_available=False,
    )
