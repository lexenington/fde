"""Customer simulator: the CRM, the admin API the Console uses, and the lab checkers."""

import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from . import admin, bsp, crm, lakeside_routes, savanna_sftp, savanna_world
from .keycloak_admin import IdPAdminError, set_groups_full_path


def _restore_idp_defaults():
    """Conditions live in memory, so a restarted simulator starts clean. Make the IdP match: a card may have
    changed its claim format before the restart. Keycloak may still be booting, so retry for a while."""
    for _ in range(12):
        try:
            set_groups_full_path(False)
            return
        except IdPAdminError:
            time.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=_restore_idp_defaults, daemon=True).start()
    lakeside_routes.start_seeding()
    threading.Thread(target=savanna_world.build, daemon=True).start()
    savanna_sftp.start()
    yield


app = FastAPI(title="FDE Console: customer simulator", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def log_crm_calls(request: Request, call_next):
    if not request.url.path.startswith("/crm/"):
        return await call_next(request)
    t = time.time()
    response = await call_next(request)
    with crm.store.lock:
        crm.store.requests.append({
            "t": t, "at": time.strftime("%H:%M:%S", time.localtime(t)) + f".{int(t % 1 * 1000):03d}",
            "method": request.method, "path": request.url.path + (f"?{request.url.query}" if request.url.query else ""),
            "status": response.status_code, "retry_after": response.headers.get("retry-after"),
        })
    return response


app.include_router(crm.router, prefix="/crm/v3", tags=["CRM API (what your app calls)"])
app.include_router(admin.router, prefix="/admin", tags=["Console admin"])
app.include_router(admin.checks, prefix="/checks", tags=["Lab checkers"])
app.include_router(admin.chat, prefix="/chat", tags=["Stakeholder chat"])
app.include_router(admin.katas, prefix="/katas", tags=["Katas"])
app.include_router(admin.inject, prefix="/injects", tags=["Inject cards"])
app.include_router(bsp.router, prefix="/bsp/v1", tags=["Lakeside: WhatsApp provider (what your bot calls)"])
app.include_router(bsp.stt, prefix="/stt/v1", tags=["Lakeside: speech-to-text"])
app.include_router(lakeside_routes.router, prefix="/lakeside", tags=["Lakeside world (Console)"])
app.include_router(savanna_world.router, prefix="/savanna", tags=["Savanna world (Console)"])


@app.get("/")
def root():
    return {"service": "customer simulator", "crm": "/crm/v3", "docs": "/docs"}
