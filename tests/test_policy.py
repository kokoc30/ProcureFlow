"""Tests for /api/v1/policy/{request_id}/evaluate endpoint."""

from tests.conftest import API, catalog_match, make_policy_review_request, make_request


def test_auto_approve_small_amount(client):
    """Cleanroom wipes (8900c) auto-approve below the consumables threshold."""
    req = make_policy_review_request(client, requested_items=["cleanroom wipes"])
    catalog_match(client, req["id"])

    resp = client.post(f"{API}/policy/{req['id']}/evaluate")
    assert resp.status_code == 200
    result = resp.json()
    assert result["required_approvers"] == []

    # Request should be auto-approved
    updated = client.get(f"{API}/requests/{req['id']}").json()
    assert updated["status"] == "approved"


def test_needs_manager_approval(client):
    """Two glove cases (24800c) need manager approval but not procurement."""
    req = make_policy_review_request(client, requested_items=["2 cleanroom glove cases"])
    catalog_match(client, req["id"])

    resp = client.post(f"{API}/policy/{req['id']}/evaluate")
    assert resp.status_code == 200
    result = resp.json()
    assert result["required_approvers"] == ["manager"]

    updated = client.get(f"{API}/requests/{req['id']}").json()
    assert updated["status"] == "pending_approval"


def test_high_value_multiple_approvers(client):
    """Dry pump rebuild kit exceeds the equipment standard threshold."""
    req = make_policy_review_request(client, requested_items=["dry vacuum pump rebuild kit"])
    catalog_match(client, req["id"])

    resp = client.post(f"{API}/policy/{req['id']}/evaluate")
    assert resp.status_code == 200
    result = resp.json()
    approvers = result["required_approvers"]
    assert len(approvers) >= 2
    assert "manager" in approvers
    assert "procurement" in approvers


def test_wrong_status(client):
    """Cannot evaluate policy on a request in 'clarification' status."""
    req = make_request(client, justification=None, cost_center="CC-FAB-100")
    assert req["status"] == "clarification"

    resp = client.post(f"{API}/policy/{req['id']}/evaluate")
    assert resp.status_code == 409


def test_not_found(client):
    resp = client.post(f"{API}/policy/nonexistent-id/evaluate")
    assert resp.status_code == 404


def test_idempotency(client):
    """Second evaluation on same request returns 409."""
    req = make_policy_review_request(client, requested_items=["cleanroom wipes"])
    catalog_match(client, req["id"])

    resp1 = client.post(f"{API}/policy/{req['id']}/evaluate")
    assert resp1.status_code == 200

    resp2 = client.post(f"{API}/policy/{req['id']}/evaluate")
    assert resp2.status_code == 409
