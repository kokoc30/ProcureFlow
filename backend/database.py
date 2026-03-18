"""ProcureFlow - in-memory data store with CRUD helpers.

Loads reference seed data from ``shared/data/*.json`` at module init.
Mutable collections are optionally preloaded from ``demo_state.json`` so
the live demo can start from a believable in-progress request.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from backend.models import (
    ApprovalTask,
    AuditEvent,
    Clarification,
    PolicyResult,
    PurchaseOrder,
    Request,
    User,
)
from backend.utils.enums import ApprovalDecision, ClarificationStatus
from backend.utils.settings import SHARED_DATA_DIR

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Seed-data loaders (private)
# ---------------------------------------------------------------------------

def _load_json(filename: str) -> list | dict:
    """Load a JSON file from ``SHARED_DATA_DIR``. Returns [] on error."""
    path: Path = SHARED_DATA_DIR / filename
    try:
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            logger.warning("Seed file is empty: %s", path)
            return []
        return json.loads(text)
    except FileNotFoundError:
        logger.warning("Seed file not found: %s", path)
        return []
    except json.JSONDecodeError as exc:
        logger.warning("Malformed JSON in %s: %s", path, exc)
        return []


def _load_users() -> dict[str, User]:
    raw = _load_json("users.json")
    if not isinstance(raw, list):
        logger.warning("users.json: expected a list, got %s", type(raw).__name__)
        return {}
    users: dict[str, User] = {}
    for entry in raw:
        try:
            user = User(**entry)
            users[user.id] = user
        except Exception as exc:
            logger.warning("Skipping invalid user entry: %s", exc)
    return users


def _load_catalog() -> dict[str, dict]:
    raw = _load_json("catalog.json")
    if not isinstance(raw, list):
        logger.warning("catalog.json: expected a list, got %s", type(raw).__name__)
        return {}
    catalog: dict[str, dict] = {}
    for item in raw:
        cid = item.get("catalog_id")
        if not cid:
            logger.warning("Skipping catalog entry without catalog_id")
            continue
        if cid in catalog:
            logger.warning("Duplicate catalog_id '%s' - keeping first occurrence", cid)
            continue
        catalog[cid] = item
    return catalog


def _load_policies() -> list[dict]:
    raw = _load_json("policies.json")
    if not isinstance(raw, list):
        logger.warning("policies.json: expected a list, got %s", type(raw).__name__)
        return []
    return raw


def _load_departments() -> list[dict]:
    raw = _load_json("departments.json")
    if not isinstance(raw, list):
        logger.warning("departments.json: expected a list, got %s", type(raw).__name__)
        return []
    return raw


def _load_personas() -> dict[str, str]:
    raw = _load_json("personas.json")
    if not isinstance(raw, dict):
        logger.warning("personas.json: expected a dict, got %s", type(raw).__name__)
        return {}
    return raw


def _load_demo_state() -> dict:
    raw = _load_json("demo_state.json")
    if raw == []:
        return {}
    if not isinstance(raw, dict):
        logger.warning("demo_state.json: expected a dict, got %s", type(raw).__name__)
        return {}
    return raw


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hydrate_demo_state(store: "DB") -> None:
    """Optionally preload demo requests and linked entities."""
    raw = _load_demo_state()
    if not raw:
        return

    requests_raw = raw.get("requests", [])
    if not isinstance(requests_raw, list):
        logger.warning("demo_state.json: 'requests' must be a list")
        requests_raw = []

    for entry in requests_raw:
        try:
            req = Request(**entry)
            if req.id in store.requests:
                logger.warning("Skipping duplicate demo request '%s'", req.id)
                continue
            store.requests[req.id] = req
        except Exception as exc:
            logger.warning("Skipping invalid demo request entry: %s", exc)

    clarifications_raw = raw.get("clarifications", [])
    if not isinstance(clarifications_raw, list):
        logger.warning("demo_state.json: 'clarifications' must be a list")
        clarifications_raw = []

    for entry in clarifications_raw:
        try:
            clar = Clarification(**entry)
            if clar.request_id not in store.requests:
                logger.warning(
                    "Skipping clarification '%s' for unknown request '%s'",
                    clar.id,
                    clar.request_id,
                )
                continue
            store.clarifications[clar.id] = clar
        except Exception as exc:
            logger.warning("Skipping invalid demo clarification entry: %s", exc)

    tasks_raw = raw.get("approval_tasks", [])
    if not isinstance(tasks_raw, list):
        logger.warning("demo_state.json: 'approval_tasks' must be a list")
        tasks_raw = []

    for entry in tasks_raw:
        try:
            task = ApprovalTask(**entry)
            if task.request_id not in store.requests:
                logger.warning(
                    "Skipping approval task '%s' for unknown request '%s'",
                    task.id,
                    task.request_id,
                )
                continue
            store.approval_tasks[task.id] = task
        except Exception as exc:
            logger.warning("Skipping invalid demo approval task entry: %s", exc)

    policy_results_raw = raw.get("policy_results", [])
    if not isinstance(policy_results_raw, list):
        logger.warning("demo_state.json: 'policy_results' must be a list")
        policy_results_raw = []

    for entry in policy_results_raw:
        try:
            result = PolicyResult(**entry)
            if result.request_id not in store.requests:
                logger.warning(
                    "Skipping policy result for unknown request '%s'",
                    result.request_id,
                )
                continue
            store.policy_results[result.request_id] = result
        except Exception as exc:
            logger.warning("Skipping invalid demo policy result entry: %s", exc)

    purchase_orders_raw = raw.get("purchase_orders", [])
    if not isinstance(purchase_orders_raw, list):
        logger.warning("demo_state.json: 'purchase_orders' must be a list")
        purchase_orders_raw = []

    for entry in purchase_orders_raw:
        try:
            po = PurchaseOrder(**entry)
            if po.request_id not in store.requests:
                logger.warning(
                    "Skipping purchase order '%s' for unknown request '%s'",
                    po.id,
                    po.request_id,
                )
                continue
            store.purchase_orders[po.id] = po
        except Exception as exc:
            logger.warning("Skipping invalid demo purchase order entry: %s", exc)

    audit_events_raw = raw.get("audit_events", [])
    if not isinstance(audit_events_raw, list):
        logger.warning("demo_state.json: 'audit_events' must be a list")
        audit_events_raw = []

    for entry in audit_events_raw:
        try:
            event = AuditEvent(**entry)
            if event.request_id not in store.requests:
                logger.warning(
                    "Skipping audit event '%s' for unknown request '%s'",
                    event.id,
                    event.request_id,
                )
                continue
            store.audit_events.append(event)
        except Exception as exc:
            logger.warning("Skipping invalid demo audit event entry: %s", exc)

    store.audit_events.sort(key=lambda e: e.created_at)

    logger.info(
        "Loaded demo state: %d requests, %d clarifications, %d approval tasks, "
        "%d policy results, %d purchase orders, %d audit events",
        len(store.requests),
        len(store.clarifications),
        len(store.approval_tasks),
        len(store.policy_results),
        len(store.purchase_orders),
        len(store.audit_events),
    )


# ---------------------------------------------------------------------------
# DB dataclass
# ---------------------------------------------------------------------------

@dataclass
class DB:
    """In-memory store. Instantiated once at module level as ``db``."""

    # --- Seed data (read-only after init) ---
    users: dict[str, User] = field(default_factory=dict)
    catalog: dict[str, dict] = field(default_factory=dict)
    policies: list[dict] = field(default_factory=list)
    departments: list[dict] = field(default_factory=list)
    personas: dict[str, str] = field(default_factory=dict)

    # --- Mutable collections ---
    requests: dict[str, Request] = field(default_factory=dict)
    clarifications: dict[str, Clarification] = field(default_factory=dict)
    approval_tasks: dict[str, ApprovalTask] = field(default_factory=dict)
    policy_results: dict[str, PolicyResult] = field(default_factory=dict)
    purchase_orders: dict[str, PurchaseOrder] = field(default_factory=dict)
    audit_events: list[AuditEvent] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Users (read-only)
    # ------------------------------------------------------------------

    def get_user(self, user_id: str) -> User | None:
        return self.users.get(user_id)

    def list_users(self) -> list[User]:
        return list(self.users.values())

    # ------------------------------------------------------------------
    # Catalog (read-only)
    # ------------------------------------------------------------------

    def get_catalog_item(self, catalog_id: str) -> dict | None:
        return self.catalog.get(catalog_id)

    def list_catalog(self) -> list[dict]:
        return list(self.catalog.values())

    # ------------------------------------------------------------------
    # Policies (read-only)
    # ------------------------------------------------------------------

    def get_policies(self) -> list[dict]:
        return list(self.policies)

    def get_policies_for_category(self, category: str) -> list[dict]:
        """Return rules matching *category*, falling back to 'default'."""
        matched = [p for p in self.policies if p.get("category") == category]
        if matched:
            return matched
        return [p for p in self.policies if p.get("category") == "default"]

    # ------------------------------------------------------------------
    # Departments (read-only)
    # ------------------------------------------------------------------

    def get_departments(self) -> list[dict]:
        return list(self.departments)

    def get_cost_center(self, department: str) -> str | None:
        for dept in self.departments:
            if dept.get("name") == department:
                return dept.get("cost_center")
        return None

    # ------------------------------------------------------------------
    # Personas (read-only)
    # ------------------------------------------------------------------

    def get_approver_for_role(self, role: str) -> str | None:
        return self.personas.get(role)

    # ------------------------------------------------------------------
    # Requests
    # ------------------------------------------------------------------

    def add_request(self, req: Request) -> Request:
        self.requests[req.id] = req
        return req

    def get_request(self, request_id: str) -> Request | None:
        return self.requests.get(request_id)

    def list_requests(
        self,
        requester_id: str | None = None,
        status: str | None = None,
    ) -> list[Request]:
        results = list(self.requests.values())
        if requester_id is not None:
            results = [r for r in results if r.requester_id == requester_id]
        if status is not None:
            results = [r for r in results if r.status == status]
        return results

    def update_request(self, request_id: str, **kwargs: object) -> Request | None:
        req = self.requests.get(request_id)
        if req is None:
            return None
        kwargs.setdefault("updated_at", _now_iso())
        merged = {**req.model_dump(), **kwargs}
        updated = Request.model_validate(merged)
        self.requests[request_id] = updated
        return updated

    # ------------------------------------------------------------------
    # Clarifications
    # ------------------------------------------------------------------

    def add_clarification(self, clar: Clarification) -> Clarification:
        self.clarifications[clar.id] = clar
        return clar

    def get_clarification(self, clarification_id: str) -> Clarification | None:
        return self.clarifications.get(clarification_id)

    def list_clarifications(self, request_id: str) -> list[Clarification]:
        return [
            c for c in self.clarifications.values()
            if c.request_id == request_id
        ]

    def answer_clarification(
        self, clarification_id: str, answer: str
    ) -> Clarification | None:
        clar = self.clarifications.get(clarification_id)
        if clar is None:
            return None
        updated = clar.model_copy(update={
            "answer": answer,
            "status": ClarificationStatus.answered,
            "updated_at": _now_iso(),
        })
        self.clarifications[clarification_id] = updated
        return updated

    # ------------------------------------------------------------------
    # Approval Tasks
    # ------------------------------------------------------------------

    def add_approval_task(self, task: ApprovalTask) -> ApprovalTask:
        self.approval_tasks[task.id] = task
        return task

    def get_approval_task(self, task_id: str) -> ApprovalTask | None:
        return self.approval_tasks.get(task_id)

    def list_tasks_for_request(self, request_id: str) -> list[ApprovalTask]:
        return [
            t for t in self.approval_tasks.values()
            if t.request_id == request_id
        ]

    def list_tasks_for_user(self, approver_id: str) -> list[ApprovalTask]:
        return [
            t for t in self.approval_tasks.values()
            if t.approver_id == approver_id
        ]

    def decide_task(
        self,
        task_id: str,
        decision: str,
        comment: str | None = None,
        decided_at: str | None = None,
    ) -> ApprovalTask | None:
        task = self.approval_tasks.get(task_id)
        if task is None:
            return None
        updated = task.model_copy(update={
            "decision": ApprovalDecision(decision),
            "comment": comment,
            "decided_at": decided_at or _now_iso(),
        })
        self.approval_tasks[task_id] = updated
        return updated

    # ------------------------------------------------------------------
    # Policy Results
    # ------------------------------------------------------------------

    def add_policy_result(self, result: PolicyResult) -> PolicyResult:
        self.policy_results[result.request_id] = result
        return result

    def get_policy_result(self, request_id: str) -> PolicyResult | None:
        return self.policy_results.get(request_id)

    # ------------------------------------------------------------------
    # Purchase Orders
    # ------------------------------------------------------------------

    def add_po(self, po: PurchaseOrder) -> PurchaseOrder:
        self.purchase_orders[po.id] = po
        return po

    def get_po(self, po_id: str) -> PurchaseOrder | None:
        return self.purchase_orders.get(po_id)

    # ------------------------------------------------------------------
    # Audit Events
    # ------------------------------------------------------------------

    def record_audit_event(self, event: AuditEvent) -> AuditEvent:
        self.audit_events.append(event)
        return event

    def list_audit_events(
        self, request_id: str | None = None
    ) -> list[AuditEvent]:
        if request_id is None:
            return list(self.audit_events)
        return [e for e in self.audit_events if e.request_id == request_id]


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

def _init_db() -> DB:
    """Create and populate the in-memory store from seed files."""
    store = DB(
        users=_load_users(),
        catalog=_load_catalog(),
        policies=_load_policies(),
        departments=_load_departments(),
        personas=_load_personas(),
    )
    _hydrate_demo_state(store)
    logger.info(
        "DB initialized: %d users, %d catalog items, %d policy rules, %d departments, %d requests",
        len(store.users),
        len(store.catalog),
        len(store.policies),
        len(store.departments),
        len(store.requests),
    )
    return store


db = _init_db()
