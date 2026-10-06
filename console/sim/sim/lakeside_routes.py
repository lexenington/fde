"""Console-facing endpoints for the Lakeside world: the learner's view of the customer's systems."""

import threading
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from . import bsp, config, lakeside_db as db
from .crm import store

router = APIRouter()

VOICE_NOTES = [   # canned voice notes for the Console's phone. Transcripts are what the STT mock returns
    {"id": "clear-en", "label": "Clear English booking", "language": "en", "confidence": 0.95,
     "transcript": "Hello, please I want to book a doctor at Lakeside Osu for tomorrow morning. My name is Abena Kyei."},
    {"id": "noisy-tw", "label": "Noisy, mostly Twi (low confidence)", "language": "tw", "confidence": 0.41,
     "transcript": "hello... me pɛ sɛ... eh... dɔkota... [noise] ... ɔkyena... mm"},
    {"id": "baby-fever", "label": "Baby with fever (clinical)", "language": "en", "confidence": 0.92,
     "transcript": "My baby is very hot since last night, what should I give him?"},
    {"id": "labour", "label": "Labour with heavy bleeding (emergency)", "language": "en", "confidence": 0.9,
     "transcript": "Please help, my wife is in labour and there is a lot of blood."},
]


class SendText(BaseModel):
    text: str


class SendVoice(BaseModel):
    note: str


class Toggle(BaseModel):
    on: bool


@router.get("/info")
def info():
    try:
        stats = db.stats()
    except Exception as e:
        stats = {"error": f"database not reachable yet ({type(e).__name__})"}
    return {
        "database": {**config.LAKESIDE_PUBLIC, "stats": stats,
                     "notes": "Read with replica_ro. The only write path is the stored procedures create_booking(phone, clinic, slot) and cancel_booking(appt)."},
        "bsp": {"base_url": "http://localhost:8090/bsp/v1", "token": config.BSP_TOKEN,
                "webhook_secret": config.BSP_WEBHOOK_SECRET, "stt_url": "http://localhost:8090/stt/v1/transcribe",
                "templates": {k: {"text": v[0], "params": v[1]} for k, v in bsp.TEMPLATES.items()}},
        "learner_url": store.learner_url, "dup_inbound": bsp.bsp.dup_inbound,
    }


@router.post("/db/reset")
def reset_db():
    return db.seed()


@router.post("/db/backup-window")
def backup_window(body: Toggle):
    db.set_backup_window(body.on)
    return {"backup_window": db.backup_window()}


@router.post("/chaos/duplicates")
def dup(body: Toggle):
    bsp.bsp.dup_inbound = body.on
    return {"dup_inbound": body.on}


@router.get("/voicenotes")
def voicenotes():
    return VOICE_NOTES


@router.get("/phone/{phone}")
def phone_timeline(phone: str):
    return {"phone": phone, "messages": bsp.timeline(phone),
            "window_open": bool(bsp.bsp.last_inbound.get(phone)) and (bsp.time.time() - bsp.bsp.last_inbound[phone]) < 24 * 3600}


@router.post("/phone/{phone}/text")
def phone_text(phone: str, body: SendText):
    if not bsp.E164.match(phone):
        raise HTTPException(400, "Use an E.164 number such as +233201234567")
    if not body.text.strip():
        raise HTTPException(400, "Type a message first")
    return bsp.inbound(phone, text=body.text.strip())


@router.post("/phone/{phone}/voice")
def phone_voice(phone: str, body: SendVoice):
    note = next((n for n in VOICE_NOTES if n["id"] == body.note), None)
    if not note:
        raise HTTPException(404, "unknown voice note")
    mid = bsp.register_voice(note["transcript"], note["language"], note["confidence"])
    return bsp.inbound(phone, voice=mid)


@router.post("/phone/{phone}/age")
def age_window(phone: str):
    """Pretend the patient last wrote 25 hours ago, to meet the 24-hour window rule."""
    with bsp.bsp.lock:
        bsp.bsp.last_inbound[phone] = bsp.time.time() - 25 * 3600
    return {"ok": True}


@router.get("/webhooks")
def webhook_log():
    return bsp.bsp.webhook_log[:60]


@router.post("/conversations/reset")
def reset_conversations():
    bsp.bsp.reset()
    return {"ok": True}


def start_seeding():
    def go():
        try:
            db.ensure_seeded()
        except Exception as e:           # Postgres may still be booting; the Console shows a status light
            print(f"[lakeside] seeding failed: {type(e).__name__}: {e}", flush=True)
    threading.Thread(target=go, daemon=True).start()
