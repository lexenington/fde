"""Endpoints the Console UI uses to watch and poke the customer's systems. Not part of the CRM's public API."""

import threading

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from . import config, tokens
from .checks import SUITES
from .checks.base import list_runs, save_run
from .crm import deliver_with_retries, store, user_add_note, user_change_stage

router = APIRouter()
_run_lock = threading.Lock()


class Chaos(BaseModel):
    force_429: int = 0
    retry_after: int = 2


class Settings(BaseModel):
    learner_url: str


class Stage(BaseModel):
    stage: str


class Note(BaseModel):
    text: str


@router.get("/health")
def health():
    import httpx
    out = {"sim": True}
    try:
        r = httpx.get(f"{config.KEYCLOAK_INTERNAL_URL}/realms/{config.REALM}/.well-known/openid-configuration", timeout=3)
        out["keycloak"] = r.status_code == 200
    except httpx.HTTPError:
        out["keycloak"] = False
    try:
        r = httpx.get(store.learner_url + "/", timeout=3)
        out["learner"] = {"ok": True, "status": r.status_code, "url": store.learner_url}
    except httpx.HTTPError as e:
        out["learner"] = {"ok": False, "error": type(e).__name__, "url": store.learner_url}
    return out


@router.get("/state")
def state():
    with store.lock:
        return {
            "contacts": list(store.contacts.values()),
            "deals": list(store.deals.values()),
            "requests": list(store.requests)[-200:][::-1],
            "deliveries": list(store.deliveries),
            "chaos": store.chaos,
            "settings": {"learner_url": store.learner_url},
        }


@router.post("/reset")
def reset():
    store.reset()
    return {"ok": True}


@router.post("/chaos")
def chaos(body: Chaos):
    with store.lock:
        store.chaos.update(body.model_dump())
    return store.chaos


@router.put("/settings")
def settings(body: Settings):
    store.learner_url = body.learner_url.rstrip("/")
    return {"learner_url": store.learner_url}


@router.post("/deals/{deal_id}/stage")
def change_stage(deal_id: str, body: Stage):
    evt = user_change_stage(deal_id, body.stage)
    deliver_with_retries(evt)
    return evt


@router.post("/deals/{deal_id}/notes")
def add_note(deal_id: str, body: Note):
    evt = user_add_note(deal_id, body.text)
    deliver_with_retries(evt)
    return evt


@router.post("/events/{event_id}/redeliver")
def redeliver(event_id: str):
    evt = store.events.get(event_id)
    if not evt:
        raise HTTPException(404, "unknown event")
    deliver_with_retries(evt, attempts=1)
    return evt


@router.get("/users")
def users():
    return {"password": config.USER_PASSWORD, "issuer": f"{config.KEYCLOAK_PUBLIC_URL}/realms/{config.REALM}",
            "users": [{"key": k, **v} for k, v in config.USERS.items()]}


@router.get("/token/{user}")
def token(user: str, client: str = "runmysales"):
    if user not in config.USERS:
        raise HTTPException(404, "unknown user")
    try:
        t = tokens.get_token(user, client)
    except tokens.IdPError as e:
        raise HTTPException(503, str(e))
    return {"token": t, **tokens.decode(t)}


@router.get("/info")
def info():
    return {"crm_base_url": "http://localhost:8090/crm/v3", "crm_api_key": config.CRM_API_KEY,
            "webhook_secret": config.CRM_WEBHOOK_SECRET, "scim_token": config.SCIM_TOKEN,
            "issuer": f"{config.KEYCLOAK_PUBLIC_URL}/realms/{config.REALM}", "audience": "runmysales",
            "learner_url": store.learner_url}


checks = APIRouter()


@checks.get("/{lab}/runs")
def runs(lab: str):
    s = SUITES.get(lab) or _404()
    return {"lab": lab, "title": s["suite"].title,
            "checks": [{"id": c.id, "section": c.section, "title": c.title, "points": c.points} for c in s["suite"].checks],
            "runs": list_runs(s["runs_dir"])}


@checks.get("/{lab}/runs/{run_id}")
def run_detail(lab: str, run_id: str):
    s = SUITES.get(lab) or _404()
    p = s["runs_dir"] / f"{run_id}.json"
    if not p.exists():
        _404()
    import json
    return json.loads(p.read_text(encoding="utf-8"))


@checks.post("/{lab}/run")
def run_checks(lab: str):
    s = SUITES.get(lab) or _404()
    if not _run_lock.acquire(blocking=False):
        raise HTTPException(409, "a checker run is already in progress")
    try:
        result = s["run"]()
        save_run(s["runs_dir"], result)
        return result
    finally:
        _run_lock.release()


def _404():
    raise HTTPException(404, "unknown lab")
