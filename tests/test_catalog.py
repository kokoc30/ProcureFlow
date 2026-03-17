"""Tests for /api/v1/catalog/match endpoint."""

from tests.conftest import API, make_policy_review_request


# ---- Preview mode (no persistence) ----

def test_match_known_alias(client):
    resp = client.post(f"{API}/catalog/match", json={
        "requested_items": ["krf photoresist"],
    })
    assert resp.status_code == 200
    data = resp.json()
    matched = data["matched_items"]
    assert len(matched) >= 1
    item = matched[0]
    assert item["catalog_id"] == "FAB-MAT-001"
    assert item["unit_price_cents"] == 165000


def test_match_with_quantity(client):
    resp = client.post(f"{API}/catalog/match", json={
        "requested_items": ["2 etch chamber o-ring seal kits"],
    })
    data = resp.json()
    matched = data["matched_items"]
    assert len(matched) >= 1
    seal_kit = next(m for m in matched if m["catalog_id"] == "EQP-002")
    assert seal_kit["quantity"] == 2


def test_match_unknown_item(client):
    resp = client.post(f"{API}/catalog/match", json={
        "requested_items": ["quantum flux capacitor"],
    })
    data = resp.json()
    assert len(data["unresolved_items"]) >= 1
    assert data["review_required"] is True
    assert data["matched_items"] == []


def test_match_mixed(client):
    resp = client.post(f"{API}/catalog/match", json={
        "requested_items": ["krf photoresist", "quantum flux capacitor"],
    })
    data = resp.json()
    assert len(data["matched_items"]) >= 1
    assert len(data["unresolved_items"]) >= 1


# ---- Request mode (persistence) ----

def test_match_request_mode(client):
    req = make_policy_review_request(client)
    resp = client.post(f"{API}/catalog/match", json={
        "request_id": req["id"],
    })
    assert resp.status_code == 200

    # Verify items persisted on the request
    updated = client.get(f"{API}/requests/{req['id']}").json()
    assert len(updated["items"]) >= 1
    assert updated["total_cents"] > 0


# ---- Validation ----

def test_match_no_input(client):
    resp = client.post(f"{API}/catalog/match", json={})
    assert resp.status_code == 422
