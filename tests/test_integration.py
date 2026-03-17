"""Integration tests - full workflow paths through the API."""

import re

from tests.conftest import ALICE_ID, API, make_request


PO_NUMBER_RE = re.compile(r"^PO-\d{8}-[A-Z0-9]{4}$")


def test_full_happy_path(client):
    """create (clarification) -> clarify -> answer -> catalog -> policy -> approve -> PO"""

    # 1. Create request without justification -> clarification status
    req = make_request(
        client,
        justification=None,
        cost_center="CC-FAB-100",
        requested_items=["2 cleanroom glove cases"],
    )
    rid = req["id"]
    assert req["status"] == "clarification"

    # 2. Answer any auto-created clarifications first
    existing = client.get(f"{API}/requests/{rid}/clarifications").json()
    for c in existing:
        if c["status"] == "pending":
            client.post(f"{API}/clarifications/{c['id']}/answer", json={
                "answer": "auto-fill",
                "user_id": ALICE_ID,
            })

    # Check if already transitioned
    req_state = client.get(f"{API}/requests/{rid}").json()
    if req_state["status"] == "clarification":
        # 3. Create our own clarification and answer it
        clar = client.post(f"{API}/clarifications", json={
            "request_id": rid,
            "question": "What is the business justification?",
            "field": "justification",
        }).json()

        ans = client.post(f"{API}/clarifications/{clar['id']}/answer", json={
            "answer": "Glove inventory is below the minimum level for Fab Line 3.",
            "user_id": ALICE_ID,
        })
        assert ans.status_code == 200
        req_state = ans.json()["request"]

    assert req_state["status"] == "policy_review"

    # 4. Catalog match
    match_resp = client.post(f"{API}/catalog/match", json={"request_id": rid})
    assert match_resp.status_code == 200
    assert len(match_resp.json()["matched_items"]) >= 1

    # 5. Policy evaluate -> consumables need manager approval
    policy = client.post(f"{API}/policy/{rid}/evaluate")
    assert policy.status_code == 200
    assert policy.json()["required_approvers"] == ["manager"]

    req_state = client.get(f"{API}/requests/{rid}").json()
    assert req_state["status"] == "pending_approval"

    # 6. Start approval
    tasks_resp = client.post(f"{API}/approvals/start", json={"request_id": rid})
    assert tasks_resp.status_code == 201
    tasks = tasks_resp.json()
    assert len(tasks) >= 1

    # 7. Approve the manager task
    manager_task = next(t for t in tasks if t["role"] == "manager")
    decide = client.post(f"{API}/approvals/{manager_task['id']}/decide", json={
        "approver_id": manager_task["approver_id"],
        "decision": "approved",
        "comment": "Approved for scheduled clean-room replenishment.",
    })
    assert decide.status_code == 200
    assert decide.json()["request"]["status"] == "approved"

    # 8. Generate PO
    po_resp = client.post(f"{API}/po/generate", json={"request_id": rid})
    assert po_resp.status_code == 201
    po = po_resp.json()
    assert PO_NUMBER_RE.match(po["po_number"])
    assert po["total_cents"] == 24800

    # 9. Verify audit trail
    audit = client.get(f"{API}/audit/{rid}").json()
    actions = [e["action"] for e in audit]
    assert "request_created" in actions
    assert "policy_evaluated" in actions
    assert "approval_decided" in actions
    assert "po_generated" in actions


def test_auto_approve_path(client):
    """create (cleanroom wipes) -> catalog -> policy (auto-approve) -> PO"""

    # 1. Create with all info + cheap item
    req = make_request(client, requested_items=["cleanroom wipes"])
    rid = req["id"]
    assert req["status"] == "policy_review"

    # 2. Catalog match
    match_resp = client.post(f"{API}/catalog/match", json={"request_id": rid})
    assert match_resp.status_code == 200

    # 3. Policy -> auto-approve (8900c < 15000c threshold)
    policy = client.post(f"{API}/policy/{rid}/evaluate")
    assert policy.status_code == 200
    assert policy.json()["required_approvers"] == []

    req_state = client.get(f"{API}/requests/{rid}").json()
    assert req_state["status"] == "approved"

    # 4. Generate PO
    po_resp = client.post(f"{API}/po/generate", json={"request_id": rid})
    assert po_resp.status_code == 201
    po = po_resp.json()
    assert po["total_cents"] == 8900
    assert PO_NUMBER_RE.match(po["po_number"])
