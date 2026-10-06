"""Lakeside's WhatsApp Business provider (BSP), simplified to what an FDE actually has to handle:

- outbound free-form text only inside the 24-hour customer-service window, otherwise an approved template
- inbound messages and delivery receipts arrive as signed, at-least-once webhooks (duplicates happen)
- voice notes arrive as media ids; a speech-to-text service turns them into text with a confidence score
"""

import hashlib
import hmac
import json
import re
import threading
import time
import uuid
from dataclasses import dataclass, field

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from . import config
from .crm import store as crm_store

TEMPLATES = {   # approved by the provider; free text is not allowed outside the 24h window
    "appointment_reminder": ("Hello {1}, this is a reminder of your appointment at {2} on {3}. Reply 1 to confirm or 2 to cancel.", 3),
    "appointment_confirmation": ("Hello {1}, your appointment at {2} on {3} is confirmed. Thank you for choosing Lakeside.", 3),
    "follow_up": ("Hello {1}, Lakeside Clinics is following up after your visit. Reply HELP if you need anything.", 1),
}
E164 = re.compile(r"^\+\d{11,15}$")


@dataclass
class Bsp:
    lock: threading.RLock = field(default_factory=threading.RLock)
    log: dict[str, list[dict]] = field(default_factory=dict)       # phone -> merged inbound/outbound timeline
    last_inbound: dict[str, float] = field(default_factory=dict)
    media: dict[str, dict] = field(default_factory=dict)           # media_id -> {transcript, language, confidence}
    dup_inbound: bool = False
    webhook_log: list[dict] = field(default_factory=list)
    seen_inbound: set = field(default_factory=set)

    def reset(self):
        with self.lock:
            self.log.clear(); self.last_inbound.clear(); self.webhook_log.clear(); self.seen_inbound.clear()

    def add(self, phone: str, entry: dict):
        with self.lock:
            self.log.setdefault(phone, []).append(entry)
            self.log[phone] = self.log[phone][-300:]


bsp = Bsp()


def _sig(body: bytes, ts: int, secret: str | None = None) -> str:
    mac = hmac.new((secret or config.BSP_WEBHOOK_SECRET).encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    return f"t={ts},v1={mac}"


def post_webhook(event: dict, *, learner_url: str | None = None, bad_signature: bool = False) -> int | None:
    body = json.dumps(event, separators=(",", ":")).encode()
    url = (learner_url or crm_store.learner_url).rstrip("/") + "/webhooks/whatsapp"
    ts = int(time.time())
    rec = {"at": time.strftime("%H:%M:%S"), "type": event.get("type"), "id": event.get("id"), "url": url}
    try:
        r = httpx.post(url, content=body, timeout=10, headers={
            "content-type": "application/json", "x-bsp-signature": _sig(body, ts, "wrong" if bad_signature else None)})
        rec["status"] = r.status_code
    except httpx.HTTPError as e:
        rec["status"], rec["error"] = None, type(e).__name__
    with bsp.lock:
        bsp.webhook_log.insert(0, rec)
        del bsp.webhook_log[200:]
    return rec["status"]


# ---------- Inbound: a patient writes ----------

def inbound(phone: str, *, text: str | None = None, voice: str | None = None, message_id: str | None = None,
            times: int = 1) -> dict:
    """The patient sends a message. `voice` is a media id registered with register_voice()."""
    mid = message_id or "wamid." + uuid.uuid4().hex[:20]
    msg = ({"type": "audio", "audio": {"id": voice, "mime_type": "audio/ogg; codecs=opus"}} if voice
           else {"type": "text", "text": {"body": text}})
    event = {"object": "whatsapp_business_account", "type": "message", "id": mid, "from": phone,
             "timestamp": int(time.time()), "message": msg}
    with bsp.lock:
        bsp.last_inbound[phone] = time.time()
    bsp.add(phone, {"dir": "in", "id": mid, "at": time.time(), "kind": "audio" if voice else "text",
                    "body": text if text is not None else "(voice note)", "media": voice})
    n = times + (1 if bsp.dup_inbound and times == 1 else 0)
    codes = [post_webhook(event) for _ in range(n)]
    return {"id": mid, "webhook_status": codes}


def register_voice(transcript: str, language: str = "en", confidence: float = 0.93) -> str:
    mid = "media_" + uuid.uuid4().hex[:12]
    with bsp.lock:
        bsp.media[mid] = {"transcript": transcript, "language": language, "confidence": confidence}
    return mid


# ---------- Outbound: the learner's app sends ----------

router = APIRouter()
stt = APIRouter()


def auth(request: Request):
    if request.headers.get("authorization") != f"Bearer {config.BSP_TOKEN}":
        raise HTTPException(401, {"error": {"code": 190, "message": "invalid access token"}})


def err(status: int, code: int, message: str):
    raise HTTPException(status, {"error": {"code": code, "message": message}})


class TemplateIn(BaseModel):
    name: str
    language: str = "en"
    params: list[str] = []


class SendIn(BaseModel):
    to: str
    type: str = "text"
    text: dict | None = None
    template: TemplateIn | None = None


@router.post("/messages", dependencies=[Depends(auth)])
def send(body: SendIn):
    if not E164.match(body.to):
        err(400, 131009, "Parameter value is not valid: 'to' must be an E.164 number such as +233244123456")
    if body.type == "text":
        txt = (body.text or {}).get("body", "")
        if not txt.strip():
            err(400, 100, "text.body is required")
        if len(txt) > 4096:
            err(400, 100, "text.body exceeds 4096 characters")
        last = bsp.last_inbound.get(body.to)
        if last is None or time.time() - last > 24 * 3600:
            err(400, 131047, "Re-engagement message: more than 24 hours have passed since the customer last replied. Use an approved template.")
        entry = {"kind": "text", "body": txt}
    elif body.type == "template":
        t = body.template
        if not t or t.name not in TEMPLATES:
            err(400, 132001, f"Template does not exist. Approved templates: {sorted(TEMPLATES)}")
        pattern, n = TEMPLATES[t.name]
        if len(t.params) != n:
            err(400, 132000, f"Template '{t.name}' takes {n} parameters, got {len(t.params)}")
        rendered = pattern
        for i, v in enumerate(t.params, 1):
            rendered = rendered.replace("{%d}" % i, v)
        entry = {"kind": "template", "body": rendered, "template": t.name}
    else:
        err(400, 100, "type must be 'text' or 'template'")
    mid = "wamid." + uuid.uuid4().hex[:20]
    bsp.add(body.to, {"dir": "out", "id": mid, "at": time.time(), **entry})
    threading.Thread(target=_receipts, args=(mid, body.to), daemon=True).start()
    return {"messages": [{"id": mid}]}


def _receipts(mid: str, to: str):
    """sent -> delivered -> read, the way receipts trickle in. Numbers ending 0000 are undeliverable."""
    for status, wait in (("sent", 0.2), ("delivered", 1.0), ("read", 2.5)):
        time.sleep(wait)
        if to.endswith("0000") and status != "sent":
            post_webhook({"object": "whatsapp_business_account", "type": "status", "id": mid, "status": "failed",
                          "recipient": to, "timestamp": int(time.time()), "errors": [{"code": 131026, "message": "Message undeliverable"}]})
            return
        post_webhook({"object": "whatsapp_business_account", "type": "status", "id": mid, "status": status,
                      "recipient": to, "timestamp": int(time.time())})


@router.get("/media/{media_id}", dependencies=[Depends(auth)])
def media(media_id: str):
    from fastapi.responses import Response
    if media_id not in bsp.media:
        err(404, 131052, "Media not found or expired")
    return Response(content=b"OggS\x00\x02" + bytes(64), media_type="audio/ogg")


class SttIn(BaseModel):
    media_id: str
    language_hint: str | None = None


@stt.post("/transcribe", dependencies=[Depends(auth)])
def transcribe(body: SttIn):
    m = bsp.media.get(body.media_id)
    if not m:
        err(404, 404, "media not found")
    return {"transcript": m["transcript"], "language": m["language"], "confidence": m["confidence"]}


# ---------- Timeline for the Console's phone ----------

def timeline(phone: str) -> list[dict]:
    with bsp.lock:
        return list(bsp.log.get(phone, []))


def outbound_since(phone: str, since: float) -> list[dict]:
    return [e for e in timeline(phone) if e["dir"] == "out" and e["at"] >= since]
