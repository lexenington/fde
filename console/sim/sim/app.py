"""Customer simulator: the CRM, the admin API the Console uses, and the lab checkers."""

import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from . import admin, crm

app = FastAPI(title="FDE Console: customer simulator")
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


@app.get("/")
def root():
    return {"service": "customer simulator", "crm": "/crm/v3", "docs": "/docs"}
