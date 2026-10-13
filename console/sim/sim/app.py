"""Customer simulator: the CRM, the admin API the Console uses, and the lab checkers."""

import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from . import admin, bsp, crm, lakeside_routes, platforms, sap, savanna_sftp, savanna_world, snow
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


@app.middleware("http")
async def log_platform_calls(request: Request, call_next):
    path = request.url.path
    system = "servicenow" if path.startswith("/servicenow/") else "sap" if path.startswith("/sap/") else None
    if not system:
        return await call_next(request)
    response = await call_next(request)
    platforms.note({
        "t": time.time(), "at": time.strftime("%H:%M:%S"), "system": system, "method": request.method,
        "path": path.split("/api/now/table/")[-1] if system == "servicenow" else path.split("API_SALES_ORDER_SRV/")[-1],
        "query": request.url.query, "status": response.status_code, "content_type": response.headers.get("content-type", ""),
        "accept": request.headers.get("accept", ""), "auth_in_query": any(k.lower() in ("password", "user", "username", "pwd") for k in request.query_params),
        "has_auth": bool(request.headers.get("authorization")), "note": "",
    })
    return response


app.include_router(crm.router, prefix="/crm/v3", tags=["CRM API (what your app calls)"])
app.include_router(admin.router, prefix="/admin", tags=["Console admin"])
app.include_router(admin.checks, prefix="/checks", tags=["Lab checkers"])
app.include_router(admin.chat, prefix="/chat", tags=["Stakeholder chat"])
app.include_router(snow.router, prefix="/servicenow", tags=["Volta: ServiceNow Table API (what your agent calls)"])
app.include_router(sap.router, prefix="/sap/opu/odata/sap/API_SALES_ORDER_SRV", tags=["Volta: SAP Sales Order OData v2 (what your agent calls)"])
app.include_router(admin.platforms_router, prefix="/platforms", tags=["Volta platforms (Console)"])
app.include_router(admin.ramp_router, prefix="/labs/ramp", tags=["Lab 02/05 ramp clock"])
app.include_router(admin.deploy_router, prefix="/labs/deploy", tags=["Lab 02/04 reviewer"])
app.include_router(admin.ai_router, prefix="/labs/ai", tags=["Lab 02/03 run viewer"])
app.include_router(admin.messy_router, prefix="/labs/messy", tags=["Lab 02/01 scorer"])
app.include_router(admin.katas, prefix="/katas", tags=["Katas"])
app.include_router(admin.inject, prefix="/injects", tags=["Inject cards"])
app.include_router(bsp.router, prefix="/bsp/v1", tags=["Lakeside: WhatsApp provider (what your bot calls)"])
app.include_router(bsp.stt, prefix="/stt/v1", tags=["Lakeside: speech-to-text"])
app.include_router(lakeside_routes.router, prefix="/lakeside", tags=["Lakeside world (Console)"])
app.include_router(savanna_world.router, prefix="/savanna", tags=["Savanna world (Console)"])


@app.get("/")
def root():
    return {"service": "customer simulator", "crm": "/crm/v3", "docs": "/docs"}
