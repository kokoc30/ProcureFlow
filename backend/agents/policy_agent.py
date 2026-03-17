"""ProcureFlow -- Policy agent tool.

Takes a deterministically-computed ``PolicyResult`` and produces a
plain-English summary.  The policy engine's thresholds, approver
assignments, and pass/fail decisions are never overridden.
"""

from __future__ import annotations

import json
import logging

from backend.agents.agent_models import FlagExplanation, PolicyExplanation
from backend.agents.llm_client import LLMRequest, get_client, parse_json_response
from backend.database import db

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a procurement policy advisor. You explain policy evaluation results
in clear business language for the person who submitted the purchase request.

Rules:
- Summarize what the policy engine determined. Do NOT override or reinterpret.
- Explain which rules applied and why, using the data provided.
- State the next steps (approval needed, auto-approved, etc.) based solely
  on the data provided.
- Do NOT fabricate policy rules. Only reference rules given in the input.
- Do NOT change thresholds, amounts, or approver assignments.
- Be concise: 2-4 sentences for the business summary.

Return your response as a JSON object with these keys:
{
  "business_summary": "<2-4 sentence plain-English summary>",
  "flag_explanations": [
    {"rule_name": "<rule>", "passed": true/false, "explanation": "<1 sentence>"}
  ],
  "next_steps": "<what the requester should expect next>"
}
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def explain(request_id: str) -> PolicyExplanation:
    """Produce a business-language explanation of a policy evaluation.

    **Deterministic:** Reads PolicyResult from the policy engine (thresholds,
    approver assignments, pass/fail are never overridden).
    **AI-assisted:** Translates flags into plain business language.

    Parameters
    ----------
    request_id:
        The request whose policy result to explain.

    Returns
    -------
    PolicyExplanation
        Structured explanation.  ``ai_available`` indicates whether
        AI language was used.

    Output schema::

        {
          "request_id": str,
          "business_summary": str,       // 2-4 sentence plain-English summary
          "flag_explanations": [
            {"rule_name": str, "passed": bool, "explanation": str}
          ],
          "next_steps": str,
          "ai_available": bool
        }

    System-prompt guardrails:
        - Summarize what the policy engine determined; do NOT override.
        - Do NOT fabricate policy rules or change thresholds/amounts.
        - State next steps based solely on the data provided.
    """
    policy = db.get_policy_result(request_id)
    req = db.get_request(request_id)

    if policy is None:
        return PolicyExplanation(
            request_id=request_id,
            business_summary="No policy evaluation found for this request.",
            flag_explanations=[],
            next_steps="The request must go through policy evaluation first.",
            ai_available=False,
        )

    # --- Try AI explanation ---
    client = get_client()
    if client.is_available():
        result = _generate_ai_explanation(policy, req)
        if result is not None:
            return result

    # --- Deterministic fallback ---
    flags: list[FlagExplanation] = []
    for f in policy.flags:
        flags.append(
            FlagExplanation(
                rule_name=f.rule_name,
                passed=f.passed,
                explanation=f.message,
            )
        )

    approvers = [r.value for r in policy.required_approvers]
    if approvers:
        next_steps = f"Approval required from: {', '.join(approvers)}."
    elif policy.passed:
        next_steps = "The request has been auto-approved per policy."
    else:
        next_steps = "The request did not pass policy evaluation."

    total_str = _format_cents(req.total_cents) if req else "unknown"
    summary_parts = [f"Policy evaluation {'passed' if policy.passed else 'did not pass'}."]
    if req:
        summary_parts.append(f"Request total: {total_str}.")
    if approvers:
        summary_parts.append(
            f"Required approvers: {', '.join(approvers)}."
        )
    elif policy.passed:
        summary_parts.append("No additional approval needed.")

    return PolicyExplanation(
        request_id=request_id,
        business_summary=" ".join(summary_parts),
        flag_explanations=flags,
        next_steps=next_steps,
        ai_available=False,
    )


# ---------------------------------------------------------------------------
# AI generation helper
# ---------------------------------------------------------------------------

def _generate_ai_explanation(policy, req) -> PolicyExplanation | None:
    """Call watsonx to produce a policy explanation.  Returns None on failure."""
    client = get_client()

    flags_data = [
        {
            "rule_id": f.rule_id,
            "rule_name": f.rule_name,
            "passed": f.passed,
            "message": f.message,
        }
        for f in policy.flags
    ]

    user_message = json.dumps(
        {
            "request_id": policy.request_id,
            "passed": policy.passed,
            "total_cents": req.total_cents if req else 0,
            "total_formatted": _format_cents(req.total_cents) if req else "$0.00",
            "department": req.department if req else "",
            "title": req.title if req else "",
            "flags": flags_data,
            "required_approvers": [r.value for r in policy.required_approvers],
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
        logger.warning("policy_agent: could not parse LLM response as JSON")
        return None

    flags: list[FlagExplanation] = []
    for fe in parsed.get("flag_explanations", []):
        if isinstance(fe, dict) and "rule_name" in fe:
            flags.append(
                FlagExplanation(
                    rule_name=fe["rule_name"],
                    passed=bool(fe.get("passed", True)),
                    explanation=fe.get("explanation", ""),
                )
            )

    return PolicyExplanation(
        request_id=policy.request_id,
        business_summary=parsed.get("business_summary", ""),
        flag_explanations=flags,
        next_steps=parsed.get("next_steps", ""),
        ai_available=True,
    )


# ---------------------------------------------------------------------------
# Formatting helper
# ---------------------------------------------------------------------------

def _format_cents(cents: int) -> str:
    """Format cents as USD string, e.g. 150000 -> '$1,500.00'."""
    dollars = cents / 100
    return f"${dollars:,.2f}"
