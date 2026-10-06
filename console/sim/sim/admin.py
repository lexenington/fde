"""Endpoints the Console UI uses to watch and poke the customer's systems. Not part of the CRM's public API."""

import threading

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from . import config, deploycheck, injects, katas as katas_mod, evalview, llm, messy, stakeholders, tokens
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
    out = {"sim": True, "llm": llm.configured()}
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
            "conditions": store.conditions,
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
    c = store.conditions
    return {"crm_base_url": "http://localhost:8090/crm/v3", "crm_api_key": config.CRM_API_KEY,
            "webhook_secret": config.CRM_WEBHOOK_SECRET if c["webhook_secret_mode"] != "new_only" else None,
            "webhook_secret_new": c["webhook_secret_new"], "scim_token": config.SCIM_TOKEN,
            "issuer": f"{config.KEYCLOAK_PUBLIC_URL}/realms/{config.REALM}", "audience": "runmysales",
            "learner_url": store.learner_url}


checks = APIRouter()


@checks.get("/{lab}/runs")
def runs(lab: str):
    s = SUITES.get(lab) or _404()
    return {"lab": lab, "title": s["suite"].title, "async": bool(s.get("async")),
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


_async: dict[str, dict] = {}


@checks.post("/{lab}/start")
def start_run(lab: str, only: str | None = None):
    """Long suites (Lakeside's conversations take minutes) run in the background; poll /progress."""
    s = SUITES.get(lab) or _404()
    st = _async.get(lab)
    if st and st["state"] == "running":
        raise HTTPException(409, "a run is already in progress")
    st = _async[lab] = {"state": "running", "done": 0, "total": 0, "latest": "", "run_id": None, "error": None}

    def progress(done, total, title):
        st.update(done=done, total=total, latest=title)

    def go():
        try:
            result = s["run"](only=set(only.split(",")) if only else None, progress=progress)
            save_run(s["runs_dir"], result)
            st.update(state="done", run_id=result["run_id"])
        except Exception as e:
            st.update(state="error", error=f"{type(e).__name__}: {e}")

    threading.Thread(target=go, daemon=True).start()
    return st


@checks.get("/{lab}/progress")
def run_progress(lab: str):
    return _async.get(lab, {"state": "idle"})


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


# ---------- Stakeholder chat ----------

chat = APIRouter()


class Start(BaseModel):
    scenario: str
    character: str


class Say(BaseModel):
    text: str


def _llm_guard(fn, *args):
    try:
        return fn(*args)
    except llm.LLMUnavailable as e:
        raise HTTPException(503, str(e))
    except KeyError as e:
        raise HTTPException(404, e.args[0] if e.args else "not found")
    except ValueError as e:
        raise HTTPException(400, str(e))


@chat.get("/scenarios")
def chat_scenarios():
    return {"llm_ready": llm.configured(), "scenarios": stakeholders.scenarios()}


@chat.post("/calls")
def chat_start(body: Start):
    return _llm_guard(stakeholders.start, body.scenario, body.character)


@chat.get("/calls/{sid}")
def chat_view(sid: str):
    return _llm_guard(stakeholders.view, sid)


@chat.post("/calls/{sid}/say")
def chat_say(sid: str, body: Say):
    return _llm_guard(stakeholders.say, sid, body.text)


@chat.post("/calls/{sid}/end")
def chat_end(sid: str):
    return _llm_guard(stakeholders.end, sid)


# ---------- Inject cards ----------

inject = APIRouter()


class Reply(BaseModel):
    text: str


def _inject_guard(fn, *args):
    try:
        return fn(*args)
    except injects.InjectError as e:
        raise HTTPException(400, str(e))
    except llm.LLMUnavailable as e:
        raise HTTPException(503, str(e))


@inject.get("/{lab}")
def inject_view(lab: str):
    return _inject_guard(injects.view, lab)


@inject.post("/{lab}/draw")
def inject_draw(lab: str):
    return _inject_guard(injects.draw, lab)


@inject.post("/{lab}/cards/{card_id}/hint")
def inject_hint(lab: str, card_id: str):
    return _inject_guard(injects.hint, lab, card_id)


@inject.post("/{lab}/cards/{card_id}/reply")
def inject_reply(lab: str, card_id: str, body: Reply):
    return _inject_guard(injects.respond, lab, card_id, body.text)


@inject.post("/{lab}/cards/{card_id}/action")
def inject_action(lab: str, card_id: str):
    return _inject_guard(injects.run_action, lab, card_id)


@inject.post("/{lab}/cards/{card_id}/reapply")
def inject_reapply(lab: str, card_id: str):
    return _inject_guard(injects.reapply, lab, card_id)


@inject.post("/{lab}/clear")
def inject_clear(lab: str):
    _inject_guard(injects.clear_conditions, lab)
    return injects.conditions()


@router.get("/conditions")
def conditions():
    return injects.conditions()


katas = APIRouter()


@katas.get("")
def katas_list():
    return {"katas": katas_mod.list_katas()}


@katas.get("/{kata_id}")
def katas_detail(kata_id: str):
    return katas_mod.detail(kata_id) or _404()


@katas.post("/{kata_id}/run")
def katas_run(kata_id: str):
    return katas_mod.run(kata_id) or _404()


messy_router = APIRouter()


@messy_router.get("")
def messy_state():
    return {**messy.status(), "history": messy.history()}


class MessyScore(BaseModel):
    note: str = ""


@messy_router.post("/score")
def messy_score(body: MessyScore):
    try:
        return messy.score(body.note)
    except messy.NotReady as e:
        raise HTTPException(409, str(e))


ai_router = APIRouter()


@ai_router.get("")
def ai_runs():
    return {"runs": evalview.list_runs(), "lab_path": "02-technical-depth/03-ai-engineering/lab"}


@ai_router.get("/runs/{run_id}")
def ai_run(run_id: str, compare: str | None = None, wrong_cost: float | None = None, review_cost: float | None = None):
    d = evalview.detail(run_id, compare, wrong_cost, review_cost)
    if d is None:
        raise HTTPException(404, "unknown run")
    return d


deploy_router = APIRouter()


class DrillStop(BaseModel):
    note: str = ""


@deploy_router.get("")
def deploy_state():
    return deploycheck.state()


@deploy_router.post("/drill/start")
def deploy_drill_start():
    return deploycheck.drill_start()


@deploy_router.post("/drill/stop")
def deploy_drill_stop(body: DrillStop):
    try:
        return deploycheck.drill_stop(body.note)
    except ValueError as e:
        raise HTTPException(409, str(e))


@deploy_router.post("/drill/cancel")
def deploy_drill_cancel():
    deploycheck.drill_cancel()
    return deploycheck.drill_state()
