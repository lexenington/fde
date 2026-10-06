"""A small HubSpot-like CRM that behaves the way real ones do at the worst moment.

- API-key auth, a token-bucket rate limit (429 + Retry-After), and an admin "chaos" switch
- Contacts are unique by email (409 on duplicates); deals are NOT unique, so retries duplicate them
- Changes made by CRM users (not by the API) are sent as signed webhooks to the learner's app
"""

import hashlib
import hmac
import json
import threading
import time
import uuid
from collections import deque
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from . import config

STAGES = ["new", "qualified", "contract_sent", "won", "lost"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


class Store:
    def __init__(self):
        self.lock = threading.RLock()
        # Conditions are changed by inject cards. They survive a CRM wipe; only clear_conditions() undoes them.
        self.conditions: dict = {}
        self.clear_conditions()
        self.reset()
        self.learner_url = config.LEARNER_URL

    def clear_conditions(self):
        with self.lock:
            self.conditions = {
                "rate_per_sec": config.RATE_LIMIT_PER_SEC,
                "burst": config.RATE_LIMIT_BURST,
                "webhook_secret_mode": "normal",   # normal | overlap | new_only
                "webhook_secret_new": None,
                "idp_full_path": False,
                "active": [],                       # human-readable list shown in the Console
            }

    def reset(self):
        with self.lock:
            self.contacts: dict[str, dict] = {}
            self.deals: dict[str, dict] = {}
            self.requests: deque = deque(maxlen=1000)
            self.deliveries: deque = deque(maxlen=300)
            self.events: dict[str, dict] = {}
            self.chaos = {"force_429": 0, "retry_after": 2}
            self.tokens = float(self.conditions["burst"])
            self.last_refill = time.monotonic()

    def reset_tokens(self):
        with self.lock:
            self.tokens = float(self.conditions["burst"])
            self.last_refill = time.monotonic()

    def take_token(self) -> bool:
        now = time.monotonic()
        burst, rate = self.conditions["burst"], self.conditions["rate_per_sec"]
        self.tokens = min(burst, self.tokens + (now - self.last_refill) * rate)
        self.last_refill = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


store = Store()


# ---------- API guard: auth, chaos and rate limit ----------

def guard(request: Request):
    if request.headers.get("authorization") != f"Bearer {config.CRM_API_KEY}":
        raise HTTPException(401, "invalid API key")
    with store.lock:
        if store.chaos["force_429"] > 0:
            store.chaos["force_429"] -= 1
            ra = store.chaos["retry_after"]
            raise HTTPException(429, "rate limited (chaos)", headers={"Retry-After": str(ra)})
        if not store.take_token():
            raise HTTPException(429, "rate limited", headers={"Retry-After": "1"})


router = APIRouter(dependencies=[Depends(guard)])


class ContactIn(BaseModel):
    email: str
    name: str | None = None
    phone: str | None = None


class ContactPatch(BaseModel):
    name: str | None = None
    phone: str | None = None


class DealIn(BaseModel):
    contact_id: str
    name: str
    amount_ghs: float
    owner_email: str
    stage: str = "new"
    properties: dict[str, str] = {}


class DealPatch(BaseModel):
    name: str | None = None
    amount_ghs: float | None = None
    stage: str | None = None
    owner_email: str | None = None
    properties: dict[str, str] | None = None


@router.post("/contacts", status_code=201)
def create_contact(body: ContactIn):
    with store.lock:
        email = body.email.strip().lower()
        for c in store.contacts.values():
            if c["email"] == email:
                raise HTTPException(409, {"message": "contact with this email exists", "existing_id": c["id"]})
        c = {"id": _id("ct"), "email": email, "name": body.name, "phone": body.phone,
             "created_at": _now_iso(), "updated_at": _now_iso()}
        store.contacts[c["id"]] = c
        return c


@router.get("/contacts")
def search_contacts(email: str | None = None):
    with store.lock:
        rows = list(store.contacts.values())
        if email:
            rows = [c for c in rows if c["email"] == email.strip().lower()]
        return {"results": rows, "total": len(rows)}


@router.get("/contacts/{contact_id}")
def get_contact(contact_id: str):
    c = store.contacts.get(contact_id)
    if not c:
        raise HTTPException(404, "no such contact")
    return c


@router.patch("/contacts/{contact_id}")
def patch_contact(contact_id: str, body: ContactPatch):
    with store.lock:
        c = store.contacts.get(contact_id)
        if not c:
            raise HTTPException(404, "no such contact")
        c.update({k: v for k, v in body.model_dump().items() if v is not None}, updated_at=_now_iso())
        return c


@router.post("/deals", status_code=201)
def create_deal(body: DealIn):
    with store.lock:
        if body.contact_id not in store.contacts:
            raise HTTPException(404, "no such contact")
        if body.stage not in STAGES:
            raise HTTPException(400, f"stage must be one of {STAGES}")
        d = {"id": _id("dl"), **body.model_dump(), "notes": [], "created_at": _now_iso(), "updated_at": _now_iso()}
        store.deals[d["id"]] = d
        return d


@router.get("/deals")
def search_deals(contact_id: str | None = None, booking_id: str | None = None):
    with store.lock:
        rows = list(store.deals.values())
        if contact_id:
            rows = [d for d in rows if d["contact_id"] == contact_id]
        if booking_id:
            rows = [d for d in rows if d["properties"].get("booking_id") == booking_id]
        return {"results": rows, "total": len(rows)}


@router.get("/deals/{deal_id}")
def get_deal(deal_id: str):
    d = store.deals.get(deal_id)
    if not d:
        raise HTTPException(404, "no such deal")
    return d


@router.patch("/deals/{deal_id}")
def patch_deal(deal_id: str, body: DealPatch):
    with store.lock:
        d = store.deals.get(deal_id)
        if not d:
            raise HTTPException(404, "no such deal")
        changes = {k: v for k, v in body.model_dump().items() if v is not None}
        if "stage" in changes and changes["stage"] not in STAGES:
            raise HTTPException(400, f"stage must be one of {STAGES}")
        if "properties" in changes:
            d["properties"].update(changes.pop("properties"))
        d.update(changes, updated_at=_now_iso())
        return d


# ---------- Webhooks (CRM -> learner app) ----------

def _mac(secret: str, body: bytes, ts: int) -> str:
    return hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()


def sign(body: bytes, ts: int, secret: str | None = None) -> str:
    """Signature header. During a secret rotation the CRM signs with the new secret too (overlap),
    then only the new one (new_only), exactly as Stripe-style providers do."""
    if secret:  # explicit secret: used to make deliberately bad signatures
        return f"t={ts},v1={_mac(secret, body, ts)}"
    c = store.conditions
    old, new = config.CRM_WEBHOOK_SECRET, c["webhook_secret_new"]
    if c["webhook_secret_mode"] == "overlap" and new:
        return f"t={ts},v1={_mac(new, body, ts)},v1={_mac(old, body, ts)}"
    if c["webhook_secret_mode"] == "new_only" and new:
        return f"t={ts},v1={_mac(new, body, ts)}"
    return f"t={ts},v1={_mac(old, body, ts)}"


def make_event(event_type: str, data: dict, occurred_at: str | None = None) -> dict:
    evt = {"id": _id("evt"), "type": event_type, "occurred_at": occurred_at or _now_iso(), "data": data}
    with store.lock:
        store.events[evt["id"]] = evt
    return evt


def deliver(evt: dict, *, ts: int | None = None, bad_signature: bool = False, secret: str | None = None, label: str = "") -> int | None:
    """Send one webhook delivery. Returns the HTTP status, or None if the learner's app was unreachable."""
    body = json.dumps(evt, separators=(",", ":")).encode()
    ts = ts if ts is not None else int(time.time())
    sig = sign(body, ts, "wrong-secret" if bad_signature else secret)
    url = store.learner_url.rstrip("/") + "/webhooks/crm"
    rec = {"at": _now_iso(), "event_id": evt["id"], "type": evt["type"], "url": url, "label": label}
    try:
        r = httpx.post(url, content=body, timeout=5,
                       headers={"content-type": "application/json", "x-crm-signature": sig})
        rec["status"] = r.status_code
    except httpx.HTTPError as e:
        rec["status"] = None
        rec["error"] = type(e).__name__
    with store.lock:
        store.deliveries.appendleft(rec)
    return rec["status"]


def deliver_with_retries(evt: dict, attempts: int = 4):
    """What a real CRM does: retry non-2xx with backoff, in the background."""
    def run():
        for i in range(attempts):
            status = deliver(evt, label=f"attempt {i + 1}")
            if status is not None and 200 <= status < 300:
                return
            time.sleep(2 ** i)
    threading.Thread(target=run, daemon=True).start()


def user_change_stage(deal_id: str, stage: str) -> dict:
    """A salesperson changes the stage inside the CRM UI -> webhook."""
    with store.lock:
        d = store.deals.get(deal_id)
        if not d:
            raise HTTPException(404, "no such deal")
        if stage not in STAGES:
            raise HTTPException(400, f"stage must be one of {STAGES}")
        d["stage"], d["updated_at"] = stage, _now_iso()
    return make_event("deal.stage_changed", {"deal_id": deal_id, "stage": stage})


def user_add_note(deal_id: str, text: str) -> dict:
    with store.lock:
        d = store.deals.get(deal_id)
        if not d:
            raise HTTPException(404, "no such deal")
        note = {"note_id": _id("nt"), "text": text, "created_at": _now_iso()}
        d["notes"].append(note)
    return make_event("deal.note_added", {"deal_id": deal_id, "note_id": note["note_id"], "text": text})
