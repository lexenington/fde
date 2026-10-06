import hashlib
import hmac
import time

import pytest
from fastapi.testclient import TestClient

from sim import bsp, config
from sim.app import app

AUTH = {"authorization": f"Bearer {config.BSP_TOKEN}"}
PHONE = "+233201230001"


@pytest.fixture(autouse=True)
def clean():
    bsp.bsp.reset()
    bsp.bsp.dup_inbound = False
    yield
    bsp.bsp.reset()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(bsp, "post_webhook", lambda *a, **k: 200)      # no learner app in unit tests
    monkeypatch.setattr(bsp, "_receipts", lambda *a, **k: None)
    return TestClient(app)


def send(client, body):
    return client.post("/bsp/v1/messages", json=body, headers=AUTH)


def test_needs_the_token(client):
    assert client.post("/bsp/v1/messages", json={"to": PHONE, "type": "text", "text": {"body": "hi"}}).status_code == 401


def test_free_text_needs_an_open_24h_window(client):
    r = send(client, {"to": PHONE, "type": "text", "text": {"body": "hello"}})
    assert r.status_code == 400 and r.json()["detail"]["error"]["code"] == 131047
    bsp.inbound(PHONE, text="hi")
    assert send(client, {"to": PHONE, "type": "text", "text": {"body": "hello"}}).status_code == 200
    bsp.bsp.last_inbound[PHONE] = time.time() - 25 * 3600
    assert send(client, {"to": PHONE, "type": "text", "text": {"body": "hello"}}).status_code == 400


def test_templates_work_outside_the_window_and_check_params(client):
    ok = send(client, {"to": PHONE, "type": "template", "template": {"name": "appointment_reminder", "params": ["Esi", "Lakeside Osu", "Thu 8 Oct, 10:00"]}})
    assert ok.status_code == 200
    assert "Hello Esi, this is a reminder of your appointment at Lakeside Osu" in bsp.timeline(PHONE)[-1]["body"]
    assert send(client, {"to": PHONE, "type": "template", "template": {"name": "appointment_reminder", "params": ["only one"]}}).status_code == 400
    assert send(client, {"to": PHONE, "type": "template", "template": {"name": "made_up", "params": []}}).status_code == 400


def test_numbers_must_be_e164(client):
    assert send(client, {"to": "0244123456", "type": "text", "text": {"body": "x"}}).status_code == 400


def test_inbound_is_logged_and_signed():
    sent = []
    orig = bsp.post_webhook
    try:
        bsp.post_webhook = lambda event, **k: sent.append(event) or 200
        res = bsp.inbound(PHONE, text="book me", times=3)
    finally:
        bsp.post_webhook = orig
    assert res["webhook_status"] == [200, 200, 200] and len(sent) == 3
    assert len({e["id"] for e in sent}) == 1               # duplicates share one message id
    assert bsp.timeline(PHONE)[0]["body"] == "book me" and bsp.bsp.last_inbound[PHONE] > 0


def test_signature_matches_documented_scheme():
    body, ts = b'{"id":"wamid.1"}', 1790000000
    expect = hmac.new(config.BSP_WEBHOOK_SECRET.encode(), b"1790000000." + body, hashlib.sha256).hexdigest()
    assert bsp._sig(body, ts) == f"t={ts},v1={expect}"


def test_voice_notes_and_stt(client):
    mid = bsp.register_voice("hello there", "en", 0.42)
    assert client.get(f"/bsp/v1/media/{mid}", headers=AUTH).status_code == 200
    r = client.post("/stt/v1/transcribe", json={"media_id": mid}, headers=AUTH).json()
    assert r == {"transcript": "hello there", "language": "en", "confidence": 0.42}
    assert client.post("/stt/v1/transcribe", json={"media_id": "nope"}, headers=AUTH).status_code == 404
