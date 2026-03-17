"""ProcureFlow - deterministic catalog matching service.

Translates raw requested_items strings into structured Item objects
by matching against the seed catalog using:
  1. Quantity parsing  (e.g. "2 seal kits" -> qty=2)
  2. Alias map         (e.g. "photoresist" -> FAB-MAT-001)
  3. Token overlap     (Jaccard score >= 0.4)

No AI. All matching is deterministic and explainable.
"""

from __future__ import annotations

import re
import string
from typing import Any

from fastapi import HTTPException

from backend.audit import record_event
from backend.database import db
from backend.models import Item
from backend.utils.enums import AuditAction

# ---------------------------------------------------------------------------
# Alias map - hand-curated short names -> catalog IDs
# Sorted longest-first at lookup time so more specific phrases win.
# ---------------------------------------------------------------------------

_ALIASES: dict[str, str] = {
    # Wafers
    "prime silicon wafer": "WAF-001",
    "prime silicon wafers": "WAF-001",
    "silicon wafer": "WAF-001",
    "silicon wafers": "WAF-001",
    "prime wafers": "WAF-001",
    "monitor wafer": "WAF-002",
    "monitor wafers": "WAF-002",
    "test wafer": "WAF-002",
    "test wafers": "WAF-002",
    # Specialty chemicals
    "krf photoresist": "FAB-MAT-001",
    "photoresist": "FAB-MAT-001",
    "cmp slurry": "CHEM-002",
    "slurry": "CHEM-002",
    "electronic grade ipa": "CHEM-003",
    "isopropyl alcohol": "CHEM-003",
    "ipa": "CHEM-003",
    # Clean-room consumables
    "cleanroom wipes": "CR-001",
    "clean room wipes": "CR-001",
    "wiper case": "CR-001",
    "wiper cases": "CR-001",
    "cleanroom glove": "CR-002",
    "cleanroom gloves": "CR-002",
    "clean room gloves": "CR-002",
    "glove case": "CR-002",
    "glove cases": "CR-002",
    # Equipment spare parts
    "vacuum pump rebuild kit": "EQP-001",
    "pump rebuild kit": "EQP-001",
    "dry pump rebuild kit": "EQP-001",
    "etch chamber o-ring seal kit": "EQP-002",
    "etch chamber oring seal kit": "EQP-002",
    "o-ring seal kit": "EQP-002",
    "o-ring seal kits": "EQP-002",
    "seal kit": "EQP-002",
    "seal kits": "EQP-002",
    "mass flow controller": "EQP-003",
    "mfc spare module": "EQP-003",
    "mfc module": "EQP-003",
    # Testing materials
    "probe card cleaning sheet": "TST-001",
    "probe card cleaning sheets": "TST-001",
    "cleaning sheet pack": "TST-001",
    "qualification coupon": "TST-002",
    "qualification coupons": "TST-002",
    "metrology coupon": "TST-002",
    "metrology coupons": "TST-002",
    # MRO items
    "ulpa filter": "MRO-001",
    "ulpa filters": "MRO-001",
    "filter cartridge": "MRO-001",
    "filter cartridges": "MRO-001",
    "timing belt kit": "MRO-002",
    "conveyor belt kit": "MRO-002",
    # Supplier services
    "sensor calibration service": "SVC-001",
    "calibration service": "SVC-001",
    "supplier audit support": "SVC-002",
    "lot trace audit": "SVC-002",
}

# Pre-sorted by key length descending for longest-match-first
_ALIASES_SORTED: list[tuple[str, str]] = sorted(
    _ALIASES.items(), key=lambda kv: len(kv[0]), reverse=True
)

# Word -> number map for quantity parsing
_WORD_NUMBERS: dict[str, int] = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}

_TOKEN_THRESHOLD = 0.4

# Characters to strip for normalization
_PUNCT_TABLE = str.maketrans("", "", string.punctuation.replace("-", ""))


# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Lowercase, strip punctuation (keep hyphens), collapse whitespace."""
    t = text.lower().translate(_PUNCT_TABLE)
    return " ".join(t.split())


def _tokenize(text: str) -> set[str]:
    """Split normalized text into a set of tokens."""
    return set(text.split()) if text else set()


# ---------------------------------------------------------------------------
# Quantity parsing
# ---------------------------------------------------------------------------

_QTY_NUMERIC_RE = re.compile(r"^\s*(\d+)\s+(.+)$")


def _parse_quantity(raw: str) -> tuple[int, str]:
    """Extract leading quantity from raw text.

    Returns (quantity, remaining_text).
    """
    text = raw.strip()

    # Try numeric prefix: "2 seal kits"
    m = _QTY_NUMERIC_RE.match(text)
    if m:
        return int(m.group(1)), m.group(2).strip()

    # Try word prefix: "three wafer lots"
    words = text.split(None, 1)
    if len(words) == 2 and words[0].lower() in _WORD_NUMBERS:
        return _WORD_NUMBERS[words[0].lower()], words[1].strip()

    return 1, text


# ---------------------------------------------------------------------------
# Single-item matching
# ---------------------------------------------------------------------------

def _match_single(normalized_text: str) -> dict | None:
    """Try to match normalized text to a catalog item.

    Returns the catalog dict if matched, else None.
    """
    # Layer 2: alias map (longest match first)
    for alias, catalog_id in _ALIASES_SORTED:
        if alias in normalized_text or normalized_text in alias:
            return db.get_catalog_item(catalog_id)

    # Layer 3: token overlap against all catalog descriptions
    input_tokens = _tokenize(normalized_text)
    if not input_tokens:
        return None

    best_score = 0.0
    best_item = None

    for cat_item in db.list_catalog():
        desc_normalized = _normalize(cat_item.get("description", ""))
        cat_tokens = _tokenize(desc_normalized)
        if not cat_tokens:
            continue

        intersection = len(input_tokens & cat_tokens)
        union = len(input_tokens | cat_tokens)
        score = intersection / union if union > 0 else 0.0

        if score > best_score:
            best_score = score
            best_item = cat_item

    if best_score >= _TOKEN_THRESHOLD and best_item is not None:
        return best_item

    return None


# ---------------------------------------------------------------------------
# Bulk matching (pure logic, no persistence)
# ---------------------------------------------------------------------------

def match_items(raw_items: list[str]) -> dict[str, Any]:
    """Match a list of raw item strings against the catalog.

    Returns a dict with keys: matched_items, unresolved_items,
    review_required, summary.
    """
    # Accumulator: catalog_id -> {item_data, total_qty, matched_from_list}
    matched_accum: dict[str, dict] = {}
    unresolved: list[dict] = []

    for raw in raw_items:
        qty, text = _parse_quantity(raw)
        normalized = _normalize(text)

        if not normalized:
            unresolved.append({
                "original": raw,
                "reason": "Empty item description after normalization",
            })
            continue

        cat_item = _match_single(normalized)

        if cat_item is not None:
            cid = cat_item["catalog_id"]
            if cid in matched_accum:
                # Accumulate quantity for duplicate matches
                matched_accum[cid]["quantity"] += qty
                matched_accum[cid]["matched_from"].append(raw)
            else:
                matched_accum[cid] = {
                    "catalog_id": cid,
                    "description": cat_item["description"],
                    "quantity": qty,
                    "unit_price_cents": cat_item.get("unit_price_cents", 0),
                    "vendor": cat_item.get("vendor"),
                    "matched_from": [raw],
                }
        else:
            unresolved.append({
                "original": raw,
                "reason": "No confident catalog match found",
            })

    # Build response
    matched_list = []
    for entry in matched_accum.values():
        matched_list.append({
            "catalog_id": entry["catalog_id"],
            "description": entry["description"],
            "quantity": entry["quantity"],
            "unit_price_cents": entry["unit_price_cents"],
            "vendor": entry["vendor"],
            "matched_from": ", ".join(entry["matched_from"]),
        })

    total_raw = len(raw_items)
    matched_count = total_raw - len(unresolved)
    review_required = len(unresolved) > 0

    if review_required:
        summary = (
            f"Matched {matched_count} of {total_raw} items. "
            f"{len(unresolved)} item(s) require manual review."
        )
    else:
        summary = f"All {total_raw} items matched successfully."

    return {
        "matched_items": matched_list,
        "unresolved_items": unresolved,
        "review_required": review_required,
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# Request-level matching (with persistence)
# ---------------------------------------------------------------------------

def match_request_items(request_id: str) -> dict[str, Any]:
    """Match items for a request and persist structured items.

    Raises
    ------
    HTTPException 404 - request not found.
    """
    req = db.get_request(request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")

    result = match_items(req.requested_items)

    # Build Item model objects for persistence
    structured_items = [
        Item(
            catalog_id=m["catalog_id"],
            description=m["description"],
            quantity=m["quantity"],
            unit_price_cents=m["unit_price_cents"],
            vendor=m["vendor"],
        )
        for m in result["matched_items"]
    ]

    total_cents = sum(it.quantity * it.unit_price_cents for it in structured_items)

    # Persist to request (requested_items stays unchanged)
    db.update_request(
        request_id,
        items=[it.model_dump() for it in structured_items],
        total_cents=total_cents,
    )

    # Audit
    action = (
        AuditAction.catalog_matched
        if not result["review_required"]
        else AuditAction.catalog_review_required
    )
    record_event(
        request_id=request_id,
        action=action,
        detail=result["summary"],
    )

    return result
