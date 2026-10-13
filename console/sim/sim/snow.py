"""ServiceNow Table API (the parts an agent integration touches). See platforms.py for what is faithful to the real thing."""

import base64
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from . import platforms as P

router = APIRouter()
TABLES = {"incident", "sys_user"}
OPS = re.compile(r"^(\w+?)(!=|>=|<=|STARTSWITH|ENDSWITH|LIKE|IN|=|>|<)(.*)$")
INCIDENT_WRITABLE = {"short_description", "description", "urgency", "impact", "category", "caller_id", "correlation_id", "state",
                     "close_code", "close_notes", "assigned_to", "comments", "work_notes"}
HIBERNATING = """<html><head><title>Instance Hibernating</title></head><body><h1>Instance Hibernating</h1>
<p>This instance is hibernating because it was inactive. Wake it from the developer portal.</p></body></html>"""


def _err(status: int, message: str, detail: str = "", headers: dict | None = None) -> JSONResponse:
    return JSONResponse({"error": {"message": message, "detail": detail}, "status": "failure"}, status_code=status, headers=headers)


def _authed(request: Request) -> bool:
    h = request.headers.get("authorization", "")
    if not h.lower().startswith("basic "):
        return False
    try:
        user, _, pw = base64.b64decode(h[6:]).decode().partition(":")
    except Exception:
        return False
    return user == P.SNOW_USER and pw == P.SNOW_PASSWORD


def _gate(request: Request):
    """Order matters, as on the real thing: a hibernating instance answers before it asks who you are."""
    with P.lock:
        if P.chaos["snow_503"] > 0:
            P.chaos["snow_503"] -= 1
            return HTMLResponse(HIBERNATING, status_code=503)
        if not _authed(request):
            return _err(401, "User Not Authenticated", "Required to provide Auth information", {"WWW-Authenticate": 'Basic realm="Service-now"'})
        if P.chaos["snow_429"] > 0:
            P.chaos["snow_429"] -= 1
            return _err(429, "Too Many Requests", "Rate limit exceeded", {"Retry-After": str(P.chaos["retry_after"])})
    return None


def _match(rec: dict, field: str, op: str, val: str) -> bool:
    cur = str(rec.get(field, ""))
    if op == "=": return cur == val
    if op == "!=": return cur != val
    if op == "LIKE": return val.lower() in cur.lower()
    if op == "STARTSWITH": return cur.lower().startswith(val.lower())
    if op == "ENDSWITH": return cur.lower().endswith(val.lower())
    if op == "IN": return cur in val.split(",")
    if op == ">": return cur > val
    if op == "<": return cur < val
    if op == ">=": return cur >= val
    return cur <= val


def _query(rows: list[dict], q: str) -> list[dict]:
    order = None
    for clause in [c for c in (q or "").split("^") if c]:
        if clause.startswith("ORDERBYDESC"):
            order = (clause[len("ORDERBYDESC"):], True)
        elif clause.startswith("ORDERBY"):
            order = (clause[len("ORDERBY"):], False)
        elif (m := OPS.match(clause)):
            f, op, v = m.groups()
            rows = [r for r in rows if _match(r, f, op, v)]
    if order:
        rows = sorted(rows, key=lambda r: str(r.get(order[0], "")), reverse=order[1])
    return rows


def _render(table: str, rec: dict, base: str, display: bool, fields: list[str] | None) -> dict:
    names = {u["sys_id"]: u["name"] for u in P.users}
    out = {}
    for k, v in rec.items():
        if k in ("comments", "work_notes"):
            continue
        if k in ("caller_id", "assigned_to") and table == "incident":
            if display:
                out[k] = names.get(v, "")
            else:
                out[k] = {"link": f"{base}/api/now/table/sys_user/{v}", "value": v} if v else ""
        elif k == "state" and display:
            out[k] = P.STATE_LABELS.get(v, v)
        else:
            out[k] = v
    if table == "incident":
        out["comments"], out["work_notes"] = "", ""      # journal fields read back empty, as on the real thing
    if fields:
        out = {k: out[k] for k in fields if k in out}
    return out


def _table(table: str):
    return P.incidents if table == "incident" else P.users


@router.get("/api/now/table/{table}")
def list_rows(table: str, request: Request):
    if (g := _gate(request)):
        return g
    if table not in TABLES:
        return _err(400, "Invalid table", f"Invalid table {table}")
    qp = request.query_params
    with P.lock:
        rows = _query(list(_table(table)), qp.get("sysparm_query", ""))
        total = len(rows)
        try:
            limit = min(int(qp.get("sysparm_limit", P.SNOW_PAGE_CAP)), P.SNOW_PAGE_CAP)
            offset = max(int(qp.get("sysparm_offset", 0)), 0)
        except ValueError:
            return _err(400, "Invalid parameter", "sysparm_limit and sysparm_offset must be integers")
        page = rows[offset:offset + limit]
        base = str(request.base_url).rstrip("/") + "/servicenow"
        fields = [f for f in qp.get("sysparm_fields", "").split(",") if f] or None
        display = qp.get("sysparm_display_value", "false") == "true"
        body = [_render(table, r, base, display, fields) for r in page]
    headers = {"X-Total-Count": str(total)}
    links = []
    url = f"{base}/api/now/table/{table}"
    q = f"sysparm_query={qp.get('sysparm_query', '')}&" if qp.get("sysparm_query") else ""
    if offset + limit < total:
        links.append(f'<{url}?{q}sysparm_limit={limit}&sysparm_offset={offset + limit}>;rel="next"')
    links.append(f'<{url}?{q}sysparm_limit={limit}&sysparm_offset=0>;rel="first"')
    headers["Link"] = ",".join(links)
    return JSONResponse({"result": body}, headers=headers)


@router.get("/api/now/table/{table}/{sys_id}")
def get_row(table: str, sys_id: str, request: Request):
    if (g := _gate(request)):
        return g
    if table not in TABLES:
        return _err(400, "Invalid table", f"Invalid table {table}")
    with P.lock:
        rec = next((r for r in _table(table) if r["sys_id"] == sys_id), None)
        if not rec:
            return _err(404, "No Record found", "Record doesn't exist or ACL restricts the record retrieval")
        qp = request.query_params
        return {"result": _render(table, rec, str(request.base_url).rstrip("/") + "/servicenow", qp.get("sysparm_display_value") == "true",
                                  [f for f in qp.get("sysparm_fields", "").split(",") if f] or None)}


def _resolve_caller(v: str):
    return next((u for u in P.users if u["sys_id"] == v or u["user_name"] == v), None)


def _validate(rec: dict):
    for f in ("urgency", "impact"):
        if rec.get(f) not in ("1", "2", "3"):
            return _err(400, "Operation Failed", f"Invalid value for {f}: must be 1, 2 or 3")
    return None


@router.post("/api/now/table/incident")
async def create_incident(request: Request):
    if (g := _gate(request)):
        return g
    try:
        body = await request.json()
    except Exception:
        return _err(400, "Invalid request", "Body must be JSON")
    body = {k: (str(v) if not isinstance(v, str) else v) for k, v in body.items()}
    if not body.get("short_description"):
        return _err(400, "Operation Failed", "Mandatory field short_description is missing")
    caller = _resolve_caller(body.get("caller_id", ""))
    if not caller:
        return _err(400, "Operation Failed", "caller_id must be the sys_id (or user_name) of a user in sys_user. Look the person up first.")
    rec = {"urgency": "3", "impact": "3", **{k: v for k, v in body.items() if k in P_FIELDS}}
    if (e := _validate(rec)):
        return e
    with P.lock:
        now = P._ts(datetime.now(timezone.utc))
        inc = P._incident(P.next_inc[0], caller, rec["short_description"], "1", rec["urgency"], datetime.now(timezone.utc),
                          impact=rec["impact"], description=rec.get("description", ""), category=rec.get("category", "inquiry"),
                          correlation_id=rec.get("correlation_id", ""))
        P.next_inc[0] += 1
        P.incidents.append(inc)
        for k in ("comments", "work_notes"):
            if body.get(k):
                P.journal.append({"incident": inc["sys_id"], "kind": k, "text": body[k], "at": now})
        out = _render("incident", inc, str(request.base_url).rstrip("/") + "/servicenow", False, None)
    return JSONResponse({"result": out}, status_code=201, headers={"Location": f"/servicenow/api/now/table/incident/{inc['sys_id']}"})


P_FIELDS = {"short_description", "description", "urgency", "impact", "category", "correlation_id"}


@router.patch("/api/now/table/incident/{sys_id}")
async def patch_incident(sys_id: str, request: Request):
    if (g := _gate(request)):
        return g
    try:
        body = await request.json()
    except Exception:
        return _err(400, "Invalid request", "Body must be JSON")
    body = {k: (str(v) if not isinstance(v, str) else v) for k, v in body.items()}
    with P.lock:
        inc = next((r for r in P.incidents if r["sys_id"] == sys_id), None)
        if not inc:
            return _err(404, "No Record found", "Record doesn't exist or ACL restricts the record retrieval")
        if inc["state"] in ("7", "8"):
            return _err(403, "Operation Failed", "ACL Exception Update Failed due to security constraints (closed incidents are read-only)")
        bad = set(body) - INCIDENT_WRITABLE
        if bad:
            return _err(400, "Operation Failed", f"Field(s) not writable: {', '.join(sorted(bad))}")
        new_state = body.get("state", inc["state"])
        if new_state in ("6", "7") and not ((body.get("close_code") or inc["close_code"]) and (body.get("close_notes") or inc["close_notes"])):
            return _err(403, "Operation Failed", "Operation against file 'incident' was aborted by Business Rule 'Incident Resolution Rules'. "
                                                "Error Message 'The following fields are mandatory: Resolution code, Resolution notes'")
        for f in ("urgency", "impact"):
            if f in body and body[f] not in ("1", "2", "3"):
                return _err(400, "Operation Failed", f"Invalid value for {f}")
        now = P._ts(datetime.now(timezone.utc))
        for k in ("comments", "work_notes"):
            if body.get(k):
                P.journal.append({"incident": inc["sys_id"], "kind": k, "text": body[k], "at": now})
        for k, v in body.items():
            if k not in ("comments", "work_notes"):
                inc[k] = v
        inc["priority"] = P.PRIORITY[(inc["urgency"], inc["impact"])]
        inc["sys_updated_on"] = now
        out = _render("incident", inc, str(request.base_url).rstrip("/") + "/servicenow", False, None)
    return {"result": out}


@router.delete("/api/now/table/{table}/{sys_id}")
def delete_row(table: str, sys_id: str, request: Request):
    if (g := _gate(request)):
        return g
    return _err(403, "Operation Failed", "ACL Exception Delete Failed due to security constraints")


def journal_for(number: str) -> list[dict]:
    with P.lock:
        inc = next((i for i in P.incidents if i["number"] == number), None)
        return [j for j in P.journal if inc and j["incident"] == inc["sys_id"]]
