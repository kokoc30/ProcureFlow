"""ProcureFlow -- Catalog agent tool.

Explains catalog matching results in user-friendly language.  Accepts the
output of ``catalog.match_items()`` and produces a narrative explanation
of what matched, what didn't, and guidance for unresolved items.
"""

from __future__ import annotations

import json
import logging

from backend.agents.agent_models import CatalogExplanation, ItemExplanation
from backend.agents.llm_client import LLMRequest, get_client, parse_json_response

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a procurement catalog assistant. You explain catalog matching results
to requesters in plain, professional language.

Rules:
- Describe what each requested item was matched to in the catalog.
- For unresolved items, suggest how the requester might clarify (e.g., use a
  more specific name, check the product catalog, or contact procurement).
- Do NOT change match results. Only explain and clarify them.
- Do NOT assign or modify prices, vendors, or catalog IDs.
- Be concise and helpful. Use 1-2 sentences per item.

Return your response as a JSON object with these keys:
{
  "match_narrative": "<2-3 sentence overall summary>",
  "item_explanations": [
    {"original_text": "<raw item>", "matched_to": "<catalog item or null>", "confidence_note": "<brief note>"}
  ],
  "unresolved_guidance": "<advice for unresolved items, or empty string>"
}
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def explain(
    match_result: dict,
    request_id: str | None = None,
) -> CatalogExplanation:
    """Explain catalog match results in user-friendly language.

    **Deterministic:** Reads match result from ``catalog.match_items()``
    (matching algorithm, prices, vendors are never changed).
    **AI-assisted:** Produces narrative explanations and unresolved guidance.

    Parameters
    ----------
    match_result:
        The dict returned by ``catalog.match_items()`` containing
        ``matched_items``, ``unresolved_items``, ``summary``, and
        ``review_required``.
    request_id:
        Optional request ID for context.

    Returns
    -------
    CatalogExplanation
        Structured explanation.

    Output schema::

        {
          "request_id": str | null,
          "match_narrative": str,          // 2-3 sentence overall summary
          "item_explanations": [
            {"original_text": str, "matched_to": str | null, "confidence_note": str}
          ],
          "unresolved_guidance": str,
          "ai_available": bool
        }

    System-prompt guardrails:
        - Do NOT change match results, prices, vendors, or catalog IDs.
        - Describe what each item was matched to.
        - For unresolved items, suggest how to clarify.
    """
    matched = match_result.get("matched_items", [])
    unresolved = match_result.get("unresolved_items", [])

    # --- Try AI explanation ---
    client = get_client()
    if client.is_available():
        result = _generate_ai_explanation(match_result, request_id)
        if result is not None:
            return result

    # --- Deterministic fallback ---
    items: list[ItemExplanation] = []

    for m in matched:
        matched_from = m.get("matched_from", "")
        originals = [s.strip() for s in matched_from.split(",") if s.strip()] if matched_from else []
        original = originals[0] if originals else m.get("description", "Unknown item")
        items.append(
            ItemExplanation(
                original_text=original,
                matched_to=m.get("description", ""),
                confidence_note="Matched to catalog item.",
            )
        )

    for u in unresolved:
        items.append(
            ItemExplanation(
                original_text=u.get("original", "Unknown item") if isinstance(u, dict) else str(u),
                matched_to=None,
                confidence_note=u.get("reason", "No match found in catalog.") if isinstance(u, dict) else "No match found in catalog.",
            )
        )

    n_matched = len(matched)
    n_unresolved = len(unresolved)
    narrative = f"{n_matched} item(s) matched to the catalog."
    if n_unresolved > 0:
        narrative += f" {n_unresolved} item(s) could not be matched and may require review."

    guidance = ""
    if n_unresolved > 0:
        guidance = (
            "For unresolved items, try using a more specific product name, "
            "check the product catalog, or contact the procurement team for assistance."
        )

    return CatalogExplanation(
        request_id=request_id,
        match_narrative=narrative,
        item_explanations=items,
        unresolved_guidance=guidance,
        ai_available=False,
    )


# ---------------------------------------------------------------------------
# AI generation helper
# ---------------------------------------------------------------------------

def _generate_ai_explanation(
    match_result: dict,
    request_id: str | None,
) -> CatalogExplanation | None:
    """Call watsonx to produce a catalog explanation.  Returns None on failure."""
    client = get_client()

    user_message = json.dumps(
        {
            "matched_items": [
                {
                    "original": m.get("matched_from", ""),
                    "catalog_description": m.get("description", ""),
                    "vendor": m.get("vendor", ""),
                }
                for m in match_result.get("matched_items", [])
            ],
            "unresolved_items": [
                {
                    "original": u.get("original", "") if isinstance(u, dict) else str(u),
                    "reason": u.get("reason", "") if isinstance(u, dict) else "",
                }
                for u in match_result.get("unresolved_items", [])
            ],
        },
        indent=2,
    )

    response = client.generate(
        LLMRequest(
            system_prompt=_SYSTEM_PROMPT,
            user_message=user_message,
            max_tokens=768,
            temperature=0.2,
        )
    )

    if not response.ai_available or not response.content:
        return None

    parsed = parse_json_response(response.content)
    if not isinstance(parsed, dict):
        logger.warning("catalog_agent: could not parse LLM response as JSON")
        return None

    items: list[ItemExplanation] = []
    for ie in parsed.get("item_explanations", []):
        if isinstance(ie, dict) and "original_text" in ie:
            items.append(
                ItemExplanation(
                    original_text=ie["original_text"],
                    matched_to=ie.get("matched_to"),
                    confidence_note=ie.get("confidence_note", ""),
                )
            )

    return CatalogExplanation(
        request_id=request_id,
        match_narrative=parsed.get("match_narrative", ""),
        item_explanations=items,
        unresolved_guidance=parsed.get("unresolved_guidance", ""),
        ai_available=True,
    )
