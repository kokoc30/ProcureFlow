"""Tests for /api/v1/approvals endpoints."""

from tests.conftest import (
    ALICE_ID,
    API,
    advance_to_pending_approval,
    make_policy_review_request,
)


def _setup_approval(client):
    """Create a request in pending_approval with approval tasks started.
    Returns (request_data, tasks_list)."""
    req = make_policy_review_request(client, requested_items=["2 cleanroom glove cases"])
    advance_to_pending_approval(client, req["id"])

    resp = client.post(f"{API}/approvals/start", json={"request_id": req["id"]})
    assert resp.status_code == 201
    tasks = resp.json()
    return req, tasks


# ---- Start approval ----

def test_start_approval_success(client):
    req = make_policy_review_request(client, requested_items=["2 cleanroom glove cases"])
    advance_to_pending_approval(client, req["id"])

    resp = client.post(f"{API}/approvals/start", json={"request_id": req["id"]})
    assert resp.status_code == 201
    tasks = resp.json()
    assert len(tasks) >= 1
    assert all(t["request_id"] == req["id"] for t in tasks)
    assert all(t["decision"] == "pending" for t in tasks)


def test_start_approval_wrong_status(client):
    req = make_policy_review_request(client)
    # Request is in policy_review, not pending_approval
    resp = client.post(f"{API}/approvals/start", json={"request_id": req["id"]})
    assert resp.status_code == 409


def test_start_approval_not_found(client):
    resp = client.post(f"{API}/approvals/start", json={"request_id": "nonexistent"})
    assert resp.status_code == 404


# ---- Record decision ----

def test_approve_task_success(client):
    req, tasks = _setup_approval(client)
    task = tasks[0]  # manager task
    approver_id = task["approver_id"]

    resp = client.post(f"{API}/approvals/{task['id']}/decide", json={
        "approver_id": approver_id,
        "decision": "approved",
        "comment": "Looks good",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["task"]["decision"] == "approved"


def test_reject_task(client):
    req, tasks = _setup_approval(client)
    task = tasks[0]
    approver_id = task["approver_id"]

    resp = client.post(f"{API}/approvals/{task['id']}/decide", json={
        "approver_id": approver_id,
        "decision": "rejected",
        "comment": "Budget exceeded",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["task"]["decision"] == "rejected"
    # Cascade: request should be rejected
    assert body["request"]["status"] == "rejected"


def test_decide_invalid_decision(client):
    req, tasks = _setup_approval(client)
    task = tasks[0]

    resp = client.post(f"{API}/approvals/{task['id']}/decide", json={
        "approver_id": task["approver_id"],
        "decision": "maybe",
    })
    assert resp.status_code == 422


def test_decide_wrong_approver(client):
    req, tasks = _setup_approval(client)
    task = tasks[0]

    resp = client.post(f"{API}/approvals/{task['id']}/decide", json={
        "approver_id": ALICE_ID,  # Alice is not the assigned approver
        "decision": "approved",
    })
    assert resp.status_code == 403
