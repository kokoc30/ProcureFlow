"""ProcureFlow -- Approval agent tool.

Drafts concise notification summaries for approvers.  Includes what is
being purchased, the total amount, why the approver's role is required,
and any urgency signals.  Never recommends approve or reject.
"""

from __future__ import annotations

import json
import logging

from backend.agents.agent_models import ApprovalNotification
from backend.agents.llm_client import LLMRequest, get_client, parse_json_response
from backend.database import db

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Role labels for fallback templates
# ---------------------------------------------------------------------------

_ROLE_LABELS: dict[str, str] = {
    "manager": "Manager",
    "dept_head": "Department Head",
    "procurement": "Procurement",
    "finance": "Finance",
}

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a procurement notification assistant. You draft concise
approval-request summaries for approvers in an enterprise procurement system.

Rules:
- Summarize what is being purchased, the total amount, and who requested it.
- Explain briefly why this approver's role is required (reference the policy).
- Note any urgency flags if the request urgency is high or critical.
- Do NOT make approval recommendations. Do NOT suggest approve or reject.
- Do NOT change amounts, approver assignments, or policy rules.
- Be concise: 3-5 sentences total for the notification summary.

Return your response as a JSON object with these keys:
{
  "notification_summary": "<3-5 sentence summary for the approver>",
  "line_items_summary": "<brief list of what is being purchased>",
  "policy_context": "<why this role's approval is required>",
  "urgency_note": "<urgency signal or empty string if standard>"
}
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def draft_notification(
    request_id: str,
    approver_role: str = "",
) -> ApprovalNotification:
    """Draft an approval notification summary.

    **Deterministic:** Reads request, policy result, and user data.
    **AI-assisted:** Drafts concise notification text (never recommends
    approve or reject).

    Parameters
    ----------
    request_id:
        The request needing approval.
    approver_role:
        The role of the approver (e.g. "manager", "finance").

    Returns
    -------
    ApprovalNotification
        Structured notification content.

    Output schema::

        {
          "request_id": str,
          "notification_summary": str,   // 3-5 sentence summary for approver
          "line_items_summary": str,     // brief list of purchased items
          "policy_context": str,         // why this role's approval is needed
          "urgency_note": str,           // urgency flag or empty
          "ai_available": bool
        }

    System-prompt guardrails:
        - Do NOT make approval recommendations.
        - Do NOT change amounts, approver assignments, or policy rules.
        - Note urgency flags only if high or critical.
    """
    req = db.get_request(request_id)
    if req is None:
        return ApprovalNotification(
            request_id=request_id,
            notification_summary="Request not found.",
            line_items_summary="",
            policy_context="",
            urgency_note="",
            ai_available=False,
        )

    policy = db.get_policy_result(request_id)
    requester = db.get_user(req.requester_id)
    requester_name = requester.name if requester else req.requester_id

    # --- Try AI notification ---
    client = get_client()
    if client.is_available():
        result = _generate_ai_notification(req, policy, requester_name, approver_role)
        if result is not None:
            return result

    # --- Deterministic fallback ---
    total_str = _format_cents(req.total_cents)
    role_label = _ROLE_LABELS.get(approver_role, approver_role or "Approver")

    # Line items
    if req.items:
        items_parts = []
        for it in req.items[:5]:
            items_parts.append(f"{it.description} (x{it.quantity})")
        line_items = ", ".join(items_parts)
        if len(req.items) > 5:
            line_items += f", and {len(req.items) - 5} more"
    else:
        line_items = ", ".join(req.requested_items[:5])
        if len(req.requested_items) > 5:
            line_items += f", and {len(req.requested_items) - 5} more"

    # Policy context
    if policy and policy.required_approvers:
        roles = [r.value for r in policy.required_approvers]
        policy_context = (
            f"Your {role_label} approval is required per procurement policy. "
            f"Required approvers: {', '.join(roles)}."
        )
    else:
        policy_context = f"Your {role_label} approval is required per procurement policy."

    # Urgency
    urgency_note = ""
    if req.urgency in ("high", "critical"):
        urgency_note = f"This request is marked as {req.urgency} urgency."

    notification = (
        f"Purchase request \"{req.title}\" from {requester_name} "
        f"({req.department}) for {total_str}. "
        f"{len(req.items or req.requested_items)} line item(s). "
        f"{policy_context}"
    )

    return ApprovalNotification(
        request_id=request_id,
        notification_summary=notification,
        line_items_summary=line_items,
        policy_context=policy_context,
        urgency_note=urgency_note,
        ai_available=False,
    )


# ---------------------------------------------------------------------------
# AI generation helper
# ---------------------------------------------------------------------------

def _generate_ai_notification(
    req, policy, requester_name: str, approver_role: str
) -> ApprovalNotification | None:
    """Call watsonx to draft an approval notification.  Returns None on failure."""
    client = get_client()

    items_data = []
    if req.items:
        for it in req.items[:10]:
            items_data.append(
                {
                    "description": it.description,
                    "quantity": it.quantity,
                    "unit_price": _format_cents(it.unit_price_cents),
                    "vendor": it.vendor or "",
                }
            )
    else:
        items_data = [{"description": ri} for ri in req.requested_items[:10]]

    policy_data = {}
    if policy:
        policy_data = {
            "passed": policy.passed,
            "required_approvers": [r.value for r in policy.required_approvers],
            "flags": [
                {"rule_name": f.rule_name, "message": f.message}
                for f in policy.flags
            ],
        }

    user_message = json.dumps(
        {
            "title": req.title,
            "requester": requester_name,
            "department": req.department,
            "total": _format_cents(req.total_cents),
            "urgency": req.urgency,
            "items": items_data,
            "approver_role": approver_role,
            "policy": policy_data,
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
        return None

    parsed = parse_json_response(response.content)
    if not isinstance(parsed, dict):
        logger.warning("approval_agent: could not parse LLM response as JSON")
        return None

    return ApprovalNotification(
        request_id=req.id,
        notification_summary=parsed.get("notification_summary", ""),
        line_items_summary=parsed.get("line_items_summary", ""),
        policy_context=parsed.get("policy_context", ""),
        urgency_note=parsed.get("urgency_note", ""),
        ai_available=True,
    )


# ---------------------------------------------------------------------------
# Formatting helper
# ---------------------------------------------------------------------------

def _format_cents(cents: int) -> str:
    """Format cents as USD string, e.g. 150000 -> '$1,500.00'."""
    dollars = cents / 100
    return f"${dollars:,.2f}"
