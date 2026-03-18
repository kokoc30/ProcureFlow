"""Tests for /api/v1/requests endpoints."""

from tests.conftest import ALICE_ID, API, make_request


# ---- Creation ----

def test_create_request_success(client):
    data = make_request(client)
    assert data["status"] == "policy_review"
    assert data["requester_id"] == ALICE_ID
    assert data["department"] == "Fab Operations"
    assert len(data["id"]) == 32  # uuid hex


def test_create_request_missing_justification(client):
    data = make_request(client, justification=None)
    assert data["status"] == "clarification"


def test_create_request_missing_cost_center(client):
    data = make_request(client, cost_center=None)
    assert data["status"] == "clarification"


def test_create_request_unknown_requester(client):
    resp = client.post(f"{API}/requests", json={
        "requester_id": "nonexistent-user",
        "department": "Fab Operations",
        "requested_items": ["krf photoresist"],
    })
    assert resp.status_code == 404
    assert "Requester not found" in resp.json()["detail"]


def test_create_request_invalid_cost_center(client):
    resp = client.post(f"{API}/requests", json={
        "requester_id": ALICE_ID,
        "department": "Fab Operations",
        "cost_center": "INVALID-CC",
        "requested_items": ["krf photoresist"],
        "justification": "test",
    })
    assert resp.status_code == 422
    assert "cost_center" in resp.json()["detail"].lower()


def test_create_request_empty_items(client):
    resp = client.post(f"{API}/requests", json={
        "requester_id": ALICE_ID,
        "department": "Fab Operations",
        "requested_items": ["", "  "],
    })
    assert resp.status_code == 422


# ---- Listing / retrieval ----

def test_list_requests_empty(client):
    resp = client.get(f"{API}/requests")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"] == []
    assert body["total"] == 0


def test_get_request_not_found(client):
    resp = client.get(f"{API}/requests/nonexistent-id")
    assert resp.status_code == 404
