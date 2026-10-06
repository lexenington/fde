"""Tests for the simulator itself, so a checker failure always means your app, not the simulator."""

import hashlib
import hmac

import pytest
from fastapi.testclient import TestClient

from sim import config
from sim.app import app
from sim.crm import sign, store

AUTH = {"authorization": f"Bearer {config.CRM_API_KEY}"}


@pytest.fixture
def client():
    store.reset()
    return TestClient(app)


def test_rejects_bad_api_key(client):
    assert client.get("/crm/v3/contacts").status_code == 401


def test_contact_unique_by_email(client):
    a = client.post("/crm/v3/contacts", json={"email": "A@x.com"}, headers=AUTH)
    b = client.post("/crm/v3/contacts", json={"email": "a@x.com"}, headers=AUTH)
    assert a.status_code == 201 and b.status_code == 409
    assert b.json()["detail"]["existing_id"] == a.json()["id"]


def test_deals_are_not_deduplicated(client):
    c = client.post("/crm/v3/contacts", json={"email": "a@x.com"}, headers=AUTH).json()
    deal = {"contact_id": c["id"], "name": "d", "amount_ghs": 1, "owner_email": "o@x", "properties": {"booking_id": "b"}}
    client.post("/crm/v3/deals", json=deal, headers=AUTH)
    client.post("/crm/v3/deals", json=deal, headers=AUTH)
    assert client.get("/crm/v3/deals", params={"booking_id": "b"}, headers=AUTH).json()["total"] == 2


def test_chaos_429_then_recovers(client):
    store.chaos.update(force_429=2, retry_after=3)
    codes = [client.get("/crm/v3/contacts", headers=AUTH) for _ in range(3)]
    assert [r.status_code for r in codes] == [429, 429, 200]
    assert codes[0].headers["retry-after"] == "3"
    assert store.requests[0]["status"] == 429 and store.requests[0]["retry_after"] == "3"


def test_rate_limit_kicks_in(client):
    codes = [client.get("/crm/v3/contacts", headers=AUTH).status_code for _ in range(config.RATE_LIMIT_BURST + 5)]
    assert 429 in codes


def test_signature_format():
    body, ts = b'{"id":"evt_1"}', 1700000000
    expected = hmac.new(config.CRM_WEBHOOK_SECRET.encode(), b"1700000000." + body, hashlib.sha256).hexdigest()
    assert sign(body, ts) == f"t=1700000000,v1={expected}"
