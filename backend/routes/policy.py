"""ProcureFlow – /policy route handlers.

Routes
------
POST /policy/{request_id}/evaluate – run deterministic policy evaluation
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.services.policy_engine import evaluate_policy

router = APIRouter(prefix="/policy", tags=["policy"])


# ---------------------------------------------------------------------------
# POST /policy/{request_id}/evaluate – evaluate policy for a request
# ---------------------------------------------------------------------------

@router.post("/{request_id}/evaluate")
async def evaluate_policy_route(request_id: str):
    result = evaluate_policy(request_id)
    return result.model_dump()
