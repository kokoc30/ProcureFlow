"""Tests for /api/v1/po endpoints."""

import re

from tests.conftest import API, catalog_match, make_policy_review_request


PO_NUMBER_RE = re.compile(r"^PO-\d{8}-[A-Z0-9]{4}$")


def _setup_matched_request(client):
    """Create a request with catalog-matched items."""
    req = make_policy_review_request(client, requested_items=["krf photoresist"])
    catalog_match(client, req["id"])
    return req


# ---- Generation ----

def test_generate_po_success(client):
    req = _setup_matched_request(client)

    resp = client.post(f"{API}/po/generate", json={"request_id": req["id"]})
    assert resp.status_code == 201
    po = resp.json()
    assert PO_NUMBER_RE.match(po["po_number"])
    assert po["total_cents"] == 165000  # 1 photoresist container
    assert len(po["items"]) >= 1
    assert po["request_id"] == req["id"]


def test_generate_po_not_found(client):
    resp = client.post(f"{API}/po/generate", json={"request_id": "nonexistent"})
    assert resp.status_code == 404


def test_generate_po_no_items(client):
    """PO generation blocked when no catalog match has been run."""
    req = make_policy_review_request(client)
    # Skip catalog matching - request has no items
    resp = client.post(f"{API}/po/generate", json={"request_id": req["id"]})
    assert resp.status_code == 422
    assert "catalog" in resp.json()["detail"].lower()


def test_generate_po_idempotency(client):
    req = _setup_matched_request(client)

    resp1 = client.post(f"{API}/po/generate", json={"request_id": req["id"]})
    assert resp1.status_code == 201

    resp2 = client.post(f"{API}/po/generate", json={"request_id": req["id"]})
    assert resp2.status_code == 409


# ---- Retrieval ----

def test_get_po(client):
    req = _setup_matched_request(client)
    po = client.post(f"{API}/po/generate", json={"request_id": req["id"]}).json()

    resp = client.get(f"{API}/po/{po['id']}")
    assert resp.status_code == 200
    assert resp.json()["po_number"] == po["po_number"]
