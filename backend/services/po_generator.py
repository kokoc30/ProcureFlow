"""ProcureFlow – purchase-order generation service.

Builds a structured PO draft from a request's catalog-matched items.
Unresolved items do not block generation; instead the PO is flagged
with ``review_required=True`` so procurement can review before release.
Generation is blocked only when there are zero matched items.
"""

from __future__ import annotations

import random
import string
import uuid
from collections import Counter
from datetime import datetime, timezone

from fastapi import HTTPException

from backend.audit import record_event
from backend.database import db
from backend.models import Item, PurchaseOrder
from backend.services.catalog import match_items
from backend.utils.enums import AuditAction


def _generate_po_number() -> str:
    """Create a human-readable PO number: PO-YYYYMMDD-XXXX."""
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    rand_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"PO-{date_part}-{rand_part}"


def _format_cents(cents: int) -> str:
    """Format integer cents as a dollar string (e.g. 165000 → '$1,650.00')."""
    dollars = cents / 100
    return f"${dollars:,.2f}"


def generate_purchase_order(request_id: str) -> PurchaseOrder:
    """Generate a PO draft for the given request.

    Raises
    ------
    HTTPException 404 – request not found.
    HTTPException 409 – PO already generated for this request.
    HTTPException 422 – no catalog-matched items to build a PO from.
    """
    # --- Load request ---
    req = db.get_request(request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")

    # --- Guard: already generated ---
    if req.po_id:
        raise HTTPException(
            status_code=409,
            detail="A purchase order has already been generated for this request.",
        )

    # --- Guard: must have matched items ---
    if not req.items:
        record_event(
            request_id=request_id,
            action=AuditAction.po_generation_blocked,
            detail="Cannot generate PO: no catalog-matched items on this request. "
                   "Run catalog matching first.",
        )
        raise HTTPException(
            status_code=422,
            detail="Cannot generate PO: no catalog-matched items on this request. "
                   "Run catalog matching first.",
        )

    # --- Build line items (already Item dicts on the request) ---
    items: list[Item] = [
        Item(**it) if isinstance(it, dict) else it
        for it in req.items
    ]

    # --- Compute total ---
    total_cents = sum(it.quantity * it.unit_price_cents for it in items)

    # --- Vendor summary ---
    vendor_counts: dict[str, int] = dict(
        Counter(it.vendor or "Unknown" for it in items)
    )

    # --- Detect unresolved items (deterministic re-check) ---
    match_result = match_items(req.requested_items)
    unresolved_raw: list[str] = [
        u["original"] for u in match_result["unresolved_items"]
    ]
    review_required = len(unresolved_raw) > 0

    # --- PO number ---
    po_number = _generate_po_number()

    # --- Summary text ---
    line_count = len(items)
    total_str = _format_cents(total_cents)
    if review_required:
        summary = (
            f"PO {po_number}: {line_count} line item(s), total {total_str}. "
            f"{len(unresolved_raw)} unresolved item(s) require review."
        )
    else:
        summary = (
            f"PO {po_number}: {line_count} line item(s), total {total_str}. "
            f"All items resolved."
        )

    # --- Create and persist ---
    now = datetime.now(timezone.utc).isoformat()
    po = PurchaseOrder(
        id=uuid.uuid4().hex,
        request_id=request_id,
        po_number=po_number,
        items=items,
        total_cents=total_cents,
        vendor_summary=vendor_counts,
        review_required=review_required,
        unresolved_items=unresolved_raw,
        summary=summary,
        created_at=now,
    )
    db.add_po(po)

    # --- Link PO to request ---
    db.update_request(request_id, po_id=po.id)

    # --- Audit ---
    review_note = " (review required)" if review_required else ""
    record_event(
        request_id=request_id,
        action=AuditAction.po_generated,
        detail=f"Generated {po_number}, total {total_str}{review_note}",
    )

    return po
