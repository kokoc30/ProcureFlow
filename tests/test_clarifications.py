"""Tests for /api/v1/clarifications endpoints."""

from tests.conftest import ALICE_ID, API, make_request


def _make_clarification_request(client):
    """Create a request in 'clarification' status (missing justification)."""
    return make_request(client, justification=None, cost_center="CC-FAB-100")


# ---- Creation ----

def test_create_clarification_success(client):
    req = _make_clarification_request(client)
    resp = client.post(f"{API}/clarifications", json={
        "request_id": req["id"],
        "question": "What is the business justification?",
        "field": "justification",
    })
    assert resp.status_code == 201
    clar = resp.json()
    assert clar["request_id"] == req["id"]
    assert clar["status"] == "pending"
    assert clar["question"] == "What is the business justification?"


def test_create_clarification_wrong_status(client):
    req = make_request(client)  # lands in policy_review
    resp = client.post(f"{API}/clarifications", json={
        "request_id": req["id"],
        "question": "Some question?",
    })
    assert resp.status_code == 409


def test_create_clarification_missing_request(client):
    resp = client.post(f"{API}/clarifications", json={
        "request_id": "nonexistent",
        "question": "Some question?",
    })
    assert resp.status_code == 404


# ---- Retrieval ----

def test_get_clarification(client):
    req = _make_clarification_request(client)
    create_resp = client.post(f"{API}/clarifications", json={
        "request_id": req["id"],
        "question": "Missing justification?",
    })
    clar_id = create_resp.json()["id"]

    resp = client.get(f"{API}/clarifications/{clar_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == clar_id


# ---- Answering ----

def test_answer_clarification_success(client):
    req = _make_clarification_request(client)
    clar = client.post(f"{API}/clarifications", json={
        "request_id": req["id"],
        "question": "What is the justification?",
        "field": "justification",
    }).json()

    resp = client.post(f"{API}/clarifications/{clar['id']}/answer", json={
        "answer": "Consumables are needed to maintain clean-room shift coverage.",
        "user_id": ALICE_ID,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["clarification"]["status"] == "answered"
    assert body["clarification"]["answer"] == "Consumables are needed to maintain clean-room shift coverage."
    # Back-fill: justification should be set on the request
    assert body["request"]["justification"] == "Consumables are needed to maintain clean-room shift coverage."


def test_answer_clarification_wrong_user(client):
    req = _make_clarification_request(client)
    clar = client.post(f"{API}/clarifications", json={
        "request_id": req["id"],
        "question": "What is the justification?",
    }).json()

    resp = client.post(f"{API}/clarifications/{clar['id']}/answer", json={
        "answer": "Some answer",
        "user_id": "someone-else",
    })
    assert resp.status_code == 403


def test_answer_all_transitions_to_policy_review(client):
    """When all clarifications are answered, request should move to policy_review."""
    req = _make_clarification_request(client)
    rid = req["id"]

    # Clear any auto-created clarifications from intake by answering them
    existing = client.get(f"{API}/requests/{rid}/clarifications").json()
    for c in existing:
        if c["status"] == "pending":
            client.post(f"{API}/clarifications/{c['id']}/answer", json={
                "answer": "auto-fill",
                "user_id": ALICE_ID,
            })

    # If request already transitioned, re-check
    req_check = client.get(f"{API}/requests/{rid}").json()
    if req_check["status"] == "policy_review":
        # Already transitioned from answering auto-created clarifications
        assert True
        return

    # Otherwise create our own clarification and answer it
    clar = client.post(f"{API}/clarifications", json={
        "request_id": rid,
        "question": "Justification needed",
        "field": "justification",
    }).json()

    resp = client.post(f"{API}/clarifications/{clar['id']}/answer", json={
        "answer": "Shift coverage",
        "user_id": ALICE_ID,
    })
    assert resp.status_code == 200
    assert resp.json()["request"]["status"] == "policy_review"
