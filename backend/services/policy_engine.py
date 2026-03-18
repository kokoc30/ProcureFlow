"""ProcureFlow – deterministic policy evaluation engine.

All threshold checks, approver selection, and auto-approve logic are
pure Python against seed policy rules.  No AI, no external calls.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from fastapi import HTTPException

from backend.audit import record_event
from backend.database import db
from backend.models import PolicyFlag, PolicyResult
from backend.utils.enums import ApproverRole, AuditAction, RequestStatus


def _cents_to_usd(cents: int) -> str:
    """Format cents as a USD string, e.g. 165000 → '$1,650.00'."""
    return f"${cents / 100:,.2f}"


def _determine_category(req) -> str:
    """Determine the policy category from structured items.

    Looks up each item's catalog entry to find its category.
    Returns the most common category, or 'default' if no catalog
    items are found.
    """
    if not req.items:
        return "default"

    categories: list[str] = []
    for item in req.items:
        if item.catalog_id:
            cat_entry = db.get_catalog_item(item.catalog_id)
            if cat_entry and "category" in cat_entry:
                categories.append(cat_entry["category"])

    if not categories:
        return "default"

    # Most common category wins
    counter = Counter(categories)
    return counter.most_common(1)[0][0]


def _compute_total(req) -> int:
    """Compute total cents from structured items, falling back to
    the request's total_cents field."""
    if req.items:
        return sum(it.quantity * it.unit_price_cents for it in req.items)
    return req.total_cents


def evaluate_policy(request_id: str) -> PolicyResult:
    """Evaluate the policy rules for *request_id* and return a result.

    Raises
    ------
    HTTPException 404  – request not found.
    HTTPException 409  – request is not in ``policy_review`` status.
    HTTPException 409  – policy already evaluated for this request.
    """
    req = db.get_request(request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")

    if req.status != RequestStatus.policy_review:
        raise HTTPException(
            status_code=409,
            detail=f"Request status is '{req.status.value}'; "
                   f"policy can only be evaluated in 'policy_review' status",
        )

    # Idempotency guard
    existing = db.get_policy_result(request_id)
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="Policy has already been evaluated for this request",
        )

    # ---- Step 1: category and total ----
    category = _determine_category(req)
    total = _compute_total(req)

    # ---- Step 2: get rules (auto-fallback to 'default') ----
    rules = db.get_policies_for_category(category)

    # Sort by max_amount_cents ascending; null (unlimited) goes last
    def _sort_key(r):
        max_amt = r.get("max_amount_cents")
        return max_amt if max_amt is not None else float("inf")

    rules_sorted = sorted(rules, key=_sort_key)

    # ---- Step 3: evaluate each rule, find the matching one ----
    flags: list[PolicyFlag] = []
    matching_rule = None

    for rule in rules_sorted:
        rule_id = rule["rule_id"]
        rule_name = rule["rule_name"]
        max_amount = rule.get("max_amount_cents")

        if max_amount is not None:
            if total <= max_amount:
                flags.append(PolicyFlag(
                    rule_id=rule_id,
                    rule_name=rule_name,
                    passed=True,
                    message=f"Total {_cents_to_usd(total)} is within "
                            f"{_cents_to_usd(max_amount)} limit",
                ))
                if matching_rule is None:
                    matching_rule = rule
            else:
                flags.append(PolicyFlag(
                    rule_id=rule_id,
                    rule_name=rule_name,
                    passed=False,
                    message=f"Total {_cents_to_usd(total)} exceeds "
                            f"{_cents_to_usd(max_amount)} limit",
                ))
        else:
            # Unlimited rule — always passes
            flags.append(PolicyFlag(
                rule_id=rule_id,
                rule_name=rule_name,
                passed=True,
                message="High-value rule applies (no upper limit)",
            ))
            if matching_rule is None:
                matching_rule = rule

    # Should always match at least the unlimited rule, but guard anyway
    if matching_rule is None:
        matching_rule = rules_sorted[-1] if rules_sorted else None

    # ---- Step 4: check auto-approve ----
    auto_approve = False
    auto_threshold = (
        matching_rule.get("auto_approve_below_cents")
        if matching_rule
        else None
    )
    if auto_threshold is not None and total < auto_threshold:
        auto_approve = True

    # ---- Step 5: collect approvers ----
    required_approvers: list[ApproverRole] = []
    if not auto_approve and matching_rule:
        raw_approvers = matching_rule.get("required_approvers", [])
        seen: set[str] = set()
        for role_str in raw_approvers:
            if role_str not in seen:
                seen.add(role_str)
                required_approvers.append(ApproverRole(role_str))

    # ---- Step 6: build summary ----
    rule_ref = matching_rule["rule_id"] if matching_rule else "N/A"
    if auto_approve:
        summary = (
            f"Auto-approved: total {_cents_to_usd(total)} is below "
            f"{_cents_to_usd(auto_threshold)} threshold ({rule_ref})"
        )
    elif required_approvers:
        roles_str = ", ".join(r.value for r in required_approvers)
        summary = (
            f"Total {_cents_to_usd(total)} ({category}) requires "
            f"{roles_str} approval per {rule_ref}"
        )
    else:
        summary = (
            f"Total {_cents_to_usd(total)} ({category}) evaluated "
            f"under {rule_ref}"
        )

    # ---- Step 7: transition status ----
    new_status = (
        RequestStatus.approved if auto_approve
        else RequestStatus.pending_approval
    )
    db.update_request(request_id, status=new_status)

    # ---- Step 8: store result ----
    now = datetime.now(timezone.utc).isoformat()
    result = PolicyResult(
        request_id=request_id,
        passed=True,
        flags=flags,
        required_approvers=required_approvers,
        evaluated_at=now,
    )
    db.add_policy_result(result)

    # ---- Step 9: audit ----
    record_event(
        request_id=request_id,
        action=AuditAction.policy_evaluated,
        detail=summary,
    )

    return result
