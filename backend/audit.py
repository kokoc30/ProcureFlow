"""ProcureFlow – audit event recording helpers."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from backend.database import db
from backend.models import AuditEvent
from backend.utils.enums import AuditAction


def record_event(
    request_id: str,
    action: AuditAction,
    actor_id: str | None = None,
    detail: str = "",
) -> AuditEvent:
    """Create and persist an AuditEvent, returning it."""
    event = AuditEvent(
        id=uuid.uuid4().hex,
        request_id=request_id,
        action=action,
        actor_id=actor_id,
        detail=detail,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    return db.record_audit_event(event)
