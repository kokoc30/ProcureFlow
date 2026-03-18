"""ProcureFlow -- Intake orchestration service.

Bridges the watsonx-assisted intake layer with the deterministic
clarification workflow. The agent layer can interpret messy request
language and draft questions, but this service creates the actual
Clarification records and transitions the request into
``clarification`` status.

All state mutations are deterministic. The agent contributes only
question text and a summary. Which fields are missing, whether a
clarification is needed, and how the workflow status changes are all
decided by Python logic, not AI.
"""

from __future__ import annotations

import logging

from backend.agents.intake_agent import analyze as intake_analyze
from backend.agents.agent_models import IntakeAnalysis
from backend.database import db
from backend.services.clarification_service import create_clarification
from backend.utils.enums import RequestStatus

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def run_intake(request_id: str) -> dict:
    """Analyze a request and auto-create clarifications for missing fields.

    Workflow
    -------
    1. Call ``intake_agent.analyze()`` to detect missing fields and draft
       questions (watsonx-assisted or deterministic fallback).
    2. If the request is in ``draft`` status, transition to ``clarification``.
    3. Create one ``Clarification`` record per suggested question via the
       clarification service.
    4. Return the analysis together with the IDs of created clarifications.

    Returns
    -------
    dict
        ``{"analysis": IntakeAnalysis, "clarifications_created": [str, ...]}``

    Expected output schema::

        {
          "analysis": {
            "request_id": str,
            "missing_fields": [str, ...],
            "suggested_questions": [
              {"field": str, "question": str, "reason": str}
            ],
            "intake_summary": str,
            "ai_available": bool
          },
          "clarifications_created": [str, ...]
        }
    """
    analysis: IntakeAnalysis = intake_analyze(request_id)

    # Nothing missing -- no clarifications to create
    if not analysis.missing_fields:
        return {
            "analysis": analysis,
            "clarifications_created": [],
        }

    req = db.get_request(request_id)
    if req is None:
        return {
            "analysis": analysis,
            "clarifications_created": [],
        }

    # Transition draft → clarification so create_clarification() accepts it
    if req.status == RequestStatus.draft:
        db.update_request(request_id, status=RequestStatus.clarification)

    # Only create clarifications when request is in clarification status
    req = db.get_request(request_id)
    if req is None or req.status != RequestStatus.clarification:
        return {
            "analysis": analysis,
            "clarifications_created": [],
        }

    created_ids: list[str] = []
    for sq in analysis.suggested_questions:
        try:
            clar = create_clarification(
                request_id=request_id,
                question=sq.question,
                field=sq.field,
            )
            created_ids.append(clar.id)
        except Exception:
            logger.warning(
                "intake_service: failed to create clarification for field=%s on request=%s",
                sq.field,
                request_id,
                exc_info=True,
            )

    logger.info(
        "intake_service: created %d clarification(s) for request %s "
        "(missing: %s, ai_available: %s)",
        len(created_ids),
        request_id,
        ", ".join(analysis.missing_fields),
        analysis.ai_available,
    )

    return {
        "analysis": analysis,
        "clarifications_created": created_ids,
    }
