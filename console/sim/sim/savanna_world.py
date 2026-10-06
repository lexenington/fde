"""Builds Savanna's world on disk (documents, the SFTP export, field sheets) and serves it to the Console."""

import hashlib
import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

import httpx

from . import config, savanna_corpus as corpus, savanna_members as members, tokens
from .crm import store

VERSION = "1"
router = APIRouter()


def _fingerprint() -> str:
    h = hashlib.sha256(VERSION.encode())
    for name in ("rules.json", "whatsapp.json"):
        h.update((config.CONTENT_DIR / "savanna" / name).read_bytes())
    return h.hexdigest()[:16]


@lru_cache(maxsize=1)
def world() -> dict:
    return members.index(members.generate())


def build(force: bool = False) -> list[dict]:
    root = config.SAVANNA_DIR
    share, export = root / "share", root / "sftp" / "export"
    mf = root / "manifest.json"
    fp = _fingerprint()
    if not force and mf.exists():
        data = json.loads(mf.read_text())
        if data["fingerprint"] == fp:
            return data["files"]
    share.mkdir(parents=True, exist_ok=True)
    export.mkdir(parents=True, exist_ok=True)
    files = corpus.write_documents(share)
    w = world()
    stamp = members.AS_OF.strftime("%Y%m%d")
    for kind, text in members.core_csvs(w).items():
        (export / f"{kind}_{stamp}.csv").write_text(text, encoding="utf-8")
    (share / "field-sheets").mkdir(exist_ok=True)
    for code, (text, _truth) in members.field_sheets(w).items():
        name = f"field-sheets/{members.BRANCHES[code][0].lower().replace(' ', '-')}-2026-09.csv"
        (share / name).write_text(text, encoding="utf-8")
        files.append({"path": name, "title": f"Field sheet: {members.BRANCHES[code][0]} officers, September 2026", "kind": "field-sheet", "pages": None})
    mf.write_text(json.dumps({"fingerprint": fp, "files": files}, indent=1))
    return files


def manifest() -> list[dict]:
    mf = config.SAVANNA_DIR / "manifest.json"
    return json.loads(mf.read_text())["files"] if mf.exists() else []


def user_token(key: str, client: str = "copilot") -> str:
    u = config.SAVANNA_USERS[key]
    return tokens.get_realm_token(config.SAVANNA_REALM, client, u["email"], config.USER_PASSWORD)


class Try(BaseModel):
    user: str
    question: str
    as_of: str | None = None


@router.get("/info")
def info():
    return {
        "as_of": members.AS_OF.isoformat(), "files": manifest(), "sftp": config.SAVANNA_SFTP,
        "issuer": f"{config.KEYCLOAK_PUBLIC_URL}/realms/{config.SAVANNA_REALM}", "audience": "copilot", "password": config.USER_PASSWORD,
        "users": [{"key": k, **v} for k, v in config.SAVANNA_USERS.items()],
        "branches": {k: {"name": v[0], "region": v[1]} for k, v in members.BRANCHES.items()},
        "learner_url": store.learner_url,
    }


@router.get("/share/{path:path}")
def share(path: str):
    base = (config.SAVANNA_DIR / "share").resolve()
    target = (base / path).resolve()
    if base not in target.parents or not target.is_file():
        raise HTTPException(404, "no such document")
    return FileResponse(target, filename=target.name)


@router.get("/token/{user}")
def token(user: str, client: str = "copilot"):
    if user not in config.SAVANNA_USERS:
        raise HTTPException(404, "unknown user")
    try:
        t = user_token(user, client)
    except tokens.IdPError as e:
        raise HTTPException(503, str(e))
    return {"token": t, **tokens.decode(t)}


def _call(method: str, path: str, user: str, **kw) -> dict:
    if user not in config.SAVANNA_USERS:
        raise HTTPException(404, "unknown user")
    try:
        h = {"authorization": f"Bearer {user_token(user)}"}
    except tokens.IdPError as e:
        raise HTTPException(503, str(e))
    import time
    t0 = time.time()
    try:
        r = httpx.request(method, store.learner_url.rstrip("/") + path, headers=h, timeout=90, **kw)
    except httpx.HTTPError as e:
        raise HTTPException(502, f"could not reach your app at {store.learner_url} ({type(e).__name__})")
    try:
        body = r.json()
    except ValueError:
        body = r.text
    return {"status": r.status_code, "seconds": round(time.time() - t0, 1), "body": body}


@router.post("/try/ask")
def try_ask(body: Try):
    return _call("POST", "/api/ask", body.user, json={"question": body.question, "as_of": body.as_of or members.AS_OF.isoformat()})


@router.get("/try/summary")
def try_summary(user: str, q: str):
    return _call("GET", "/api/members/summary", user, params={"q": q})
