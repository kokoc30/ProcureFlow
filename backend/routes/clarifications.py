"""ProcureFlow – /clarifications route handlers.

Routes
------
POST /clarifications             – create a clarification question
GET  /clarifications/{id}        – retrieve a single clarification
POST /clarifications/{id}/answer – submit an answer
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, field_validator

from backend.database import db
from backend.services.clarification_service import (
    answer_clarification,
    create_clarification,
)

router = APIRouter(prefix="/clarifications", tags=["clarifications"])


# ---------------------------------------------------------------------------
# Input schemas
# ---------------------------------------------------------------------------

class CreateClarificationBody(BaseModel):
    request_id: str
    question: str
    field: str | None = None

    @field_validator("question")
    @classmethod
    def question_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("question must not be blank")
        return v.strip()


class AnswerClarificationBody(BaseModel):
    answer: str
    user_id: str | None = None

    @field_validator("answer")
    @classmethod
    def answer_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("answer must not be blank")
        return v


# ---------------------------------------------------------------------------
# POST /clarifications – create a clarification for a request
# ---------------------------------------------------------------------------

@router.post("", status_code=201)
async def create_clarification_route(body: CreateClarificationBody):
    clar = create_clarification(
        request_id=body.request_id,
        question=body.question,
        field=body.field,
    )
    return clar.model_dump()


# ---------------------------------------------------------------------------
# GET /clarifications/{clarification_id} – single clarification
# ---------------------------------------------------------------------------

@router.get("/{clarification_id}")
async def get_clarification_route(clarification_id: str):
    clar = db.get_clarification(clarification_id)
    if clar is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Clarification not found")
    return clar.model_dump()


# ---------------------------------------------------------------------------
# POST /clarifications/{clarification_id}/answer – submit an answer
# ---------------------------------------------------------------------------

@router.post("/{clarification_id}/answer")
async def answer_clarification_route(
    clarification_id: str,
    body: AnswerClarificationBody,
):
    result = answer_clarification(
        clarification_id=clarification_id,
        answer=body.answer,
        user_id=body.user_id,
    )
    return {
        "clarification": result["clarification"].model_dump(),
        "request": result["request"].model_dump(),
    }
