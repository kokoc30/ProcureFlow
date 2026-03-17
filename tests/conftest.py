"""Shared fixtures for ProcureFlow test suite."""

import pytest
from fastapi.testclient import TestClient

from backend.database import db
from backend.main import app

# ---------------------------------------------------------------------------
# Seed-data user IDs (from shared/data/users.json)
# ---------------------------------------------------------------------------
ALICE_ID = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"   # Fab Operations, requester
BOB_ID = "b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6a7"     # Fab Operations, manager
CAROL_ID = "c3d4e5f6a7b8c9d0e1f2a3b4c5d6a7b8"   # Supply Chain, dept_head
FRANK_ID = "f6a7b8c9d0e1f2a3b4c5d6a7b8c9d0e1"   # Procurement
GRACE_ID = "a7b8c9d0e1f2a3b4c5d6a7b8c9d0e1f2"   # Finance

API = "/api/v1"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_db():
    """Clear mutable collections before each test; seed data stays intact."""
    db.requests.clear()
    db.clarifications.clear()
    db.approval_tasks.clear()
    db.policy_results.clear()
    db.purchase_orders.clear()
    db.audit_events.clear()


@pytest.fixture
def client():
    """FastAPI TestClient backed by the real app."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_request(client: TestClient, **overrides) -> dict:
    """POST a valid request with sensible defaults. Returns response JSON."""
    payload = {
        "requester_id": ALICE_ID,
        "department": "Fab Operations",
        "cost_center": "CC-FAB-100",
        "title": "Test request",
        "requested_items": ["2 cleanroom glove cases"],
        "justification": "Consumables are needed to support the next fab shift.",
        **overrides,
    }
    resp = client.post(f"{API}/requests", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def make_policy_review_request(client: TestClient, **overrides) -> dict:
    """Create a request that lands in policy_review status (all info provided)."""
    data = make_request(client, **overrides)
    assert data["status"] == "policy_review"
    return data


def catalog_match(client: TestClient, request_id: str) -> dict:
    """Run catalog matching for a request. Returns match result."""
    resp = client.post(f"{API}/catalog/match", json={"request_id": request_id})
    assert resp.status_code == 200, resp.text
    return resp.json()


def evaluate_policy(client: TestClient, request_id: str) -> dict:
    """Evaluate policy for a request. Returns policy result."""
    resp = client.post(f"{API}/policy/{request_id}/evaluate")
    assert resp.status_code == 200, resp.text
    return resp.json()


def advance_to_pending_approval(client: TestClient, request_id: str) -> dict:
    """Catalog match + policy evaluate -> returns policy result.
    Expects the request to need approval (not auto-approved)."""
    catalog_match(client, request_id)
    result = evaluate_policy(client, request_id)
    # Verify it actually needs approval
    req = client.get(f"{API}/requests/{request_id}").json()
    assert req["status"] == "pending_approval"
    return result
