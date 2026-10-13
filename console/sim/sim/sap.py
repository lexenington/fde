"""SAP S/4HANA Sales Order OData v2 service (API_SALES_ORDER_SRV). See platforms.py for what is faithful to the real thing."""

import asyncio
import base64
import re
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from . import platforms as P

router = APIRouter()
COOKIE = "SAP_SESSIONID_S4H_100"
KEY = re.compile(r"^(A_SalesOrder|A_BusinessPartner)\('([^']+)'\)(/(to_Item))?$")
SETS = {"A_SalesOrder", "A_BusinessPartner"}
FILTER_TERM = re.compile(r"^(\w+)\s+(eq|ne|gt|ge|lt|le)\s+(.+)$")
BLOCK_CODES = {"", "01", "02", "03"}      # 01 = credit/risk hold (the one the agent may set)


def sap_error(status: int, code: str, message: str, headers: dict | None = None) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": {"lang": "en", "value": message}}}, status_code=status, headers=headers)


def _authed(request: Request) -> bool:
    h = request.headers.get("authorization", "")
    if not h.lower().startswith("basic "):
        return False
    try:
        user, _, pw = base64.b64decode(h[6:]).decode().partition(":")
    except Exception:
        return False
    return user.upper() == P.SAP_USER and pw == P.SAP_PASSWORD


def _date(dt: datetime) -> str:
    return f"/Date({int(dt.timestamp() * 1000)})/"


def _etag(o: dict) -> str:
    return f'W/"datetime\'2026-10-06T10:00:{o["_version"]:02d}.0000000\'"'


def _entity(set_name: str, rec: dict, base: str, with_items: bool = False) -> dict:
    if set_name == "A_BusinessPartner":
        key = rec["BusinessPartner"]
        return {"__metadata": {"id": f"{base}/A_BusinessPartner('{key}')", "type": "API_BUSINESS_PARTNER.A_BusinessPartnerType"}, **rec}
    d = {k: v for k, v in rec.items() if not k.startswith("_")}
    d["SalesOrderDate"], d["CreationDate"] = _date(rec["SalesOrderDate"]), _date(rec["CreationDate"])
    out = {"__metadata": {"id": f"{base}/A_SalesOrder('{rec['SalesOrder']}')", "type": "API_SALES_ORDER_SRV.A_SalesOrderType", "etag": _etag(rec)}, **d}
    out["to_Item"] = {"results": [{"__metadata": {"type": "API_SALES_ORDER_SRV.A_SalesOrderItemType"}, **it} for it in rec["_items"]]} if with_items \
        else {"__deferred": {"uri": f"{base}/A_SalesOrder('{rec['SalesOrder']}')/to_Item"}}
    return out


def _literal(tok: str):
    tok = tok.strip()
    if tok.startswith("datetime'"):
        return datetime.fromisoformat(tok[9:-1]).replace(tzinfo=timezone.utc)
    if tok.startswith("'") and tok.endswith("'"):
        return tok[1:-1].replace("''", "'")
    try:
        return float(tok)
    except ValueError:
        raise ValueError(f"cannot parse literal {tok!r}")


def _filter(rows: list[dict], expr: str) -> list[dict]:
    for term in re.split(r"\s+and\s+", expr.strip()):
        m = FILTER_TERM.match(term.strip())
        if not m:
            raise ValueError(f"unsupported $filter term {term!r}")
        field, op, lit = m.groups()
        want = _literal(lit)

        def ok(r, field=field, op=op, want=want):
            if field not in r:
                raise ValueError(f"unknown property {field}")
            have = r[field]
            if isinstance(have, datetime) and not isinstance(want, datetime):
                raise ValueError(f"{field} is a date: compare it with datetime'2026-10-01T00:00:00'")
            if isinstance(want, float):
                have = float(have)
            elif isinstance(want, datetime):
                pass
            else:
                have = str(have)
            return {"eq": have == want, "ne": have != want, "gt": have > want, "ge": have >= want, "lt": have < want, "le": have <= want}[op]
        rows = [r for r in rows if ok(r)]
    return rows


async def _common(request: Request):
    """Slowness, auth and content negotiation happen before anything else, and not in a helpful order."""
    if P.chaos["sap_slow_ms"]:
        await asyncio.sleep(P.chaos["sap_slow_ms"] / 1000)
    if not _authed(request):
        return sap_error(401, "AUTH", "Logon failed", {"WWW-Authenticate": 'Basic realm="SAP NetWeaver Application Server"'})
    return None


def _wants_json(request: Request) -> bool:
    return "json" in request.headers.get("accept", "").lower() or request.query_params.get("$format") == "json"


def _atom(set_name: str, rows: list[dict], key: str) -> Response:
    entries = "".join(f"<entry><id>{set_name}('{r[key]}')</id><title>{r[key]}</title></entry>" for r in rows)
    return Response(f'<?xml version="1.0" encoding="utf-8"?><feed xmlns="http://www.w3.org/2005/Atom"><title>{set_name}</title>{entries}</feed>',
                    media_type="application/atom+xml")


METADATA = """<?xml version="1.0" encoding="utf-8"?>
<edmx:Edmx Version="1.0" xmlns:edmx="http://schemas.microsoft.com/ado/2007/06/edmx"><edmx:DataServices>
<Schema Namespace="API_SALES_ORDER_SRV" xmlns="http://schemas.microsoft.com/ado/2008/09/edm">
<EntityType Name="A_SalesOrderType"><Key><PropertyRef Name="SalesOrder"/></Key>
<Property Name="SalesOrder" Type="Edm.String" Nullable="false" MaxLength="10"/><Property Name="SoldToParty" Type="Edm.String" MaxLength="10"/>
<Property Name="SalesOrderDate" Type="Edm.DateTime" Precision="0"/><Property Name="TotalNetAmount" Type="Edm.Decimal" Precision="16" Scale="3"/>
<Property Name="TransactionCurrency" Type="Edm.String" MaxLength="5"/><Property Name="OverallSDProcessStatus" Type="Edm.String" MaxLength="1"/>
<Property Name="OverallDeliveryStatus" Type="Edm.String" MaxLength="1"/><Property Name="DeliveryBlockReason" Type="Edm.String" MaxLength="2"/>
<NavigationProperty Name="to_Item" Relationship="API_SALES_ORDER_SRV.assoc_Item" FromRole="FromRole_assoc_Item" ToRole="ToRole_assoc_Item"/></EntityType>
<EntityType Name="A_SalesOrderItemType"><Key><PropertyRef Name="SalesOrder"/><PropertyRef Name="SalesOrderItem"/></Key>
<Property Name="SalesOrderItem" Type="Edm.String" MaxLength="6"/><Property Name="Material" Type="Edm.String" MaxLength="40"/>
<Property Name="RequestedQuantity" Type="Edm.Decimal" Precision="15" Scale="3"/><Property Name="NetAmount" Type="Edm.Decimal" Precision="16" Scale="3"/></EntityType>
<EntityContainer Name="API_SALES_ORDER_SRV_Entities"><EntitySet Name="A_SalesOrder" EntityType="API_SALES_ORDER_SRV.A_SalesOrderType"/></EntityContainer>
</Schema></edmx:DataServices></edmx:Edmx>"""


@router.api_route("/{rest:path}", methods=["GET", "PATCH", "POST", "DELETE"])
async def odata(rest: str, request: Request):
    if (e := await _common(request)):
        return e
    base = str(request.base_url).rstrip("/") + "/sap/opu/odata/sap/API_SALES_ORDER_SRV"
    qp = request.query_params
    method = request.method

    if rest in ("", "/"):
        return JSONResponse({"d": {"EntitySets": sorted(SETS)}})
    if rest == "$metadata":
        return Response(METADATA, media_type="application/xml")

    # ----- writes -----
    if method in ("PATCH", "POST", "DELETE"):
        sid, token = request.cookies.get(COOKIE), request.headers.get("x-csrf-token", "")
        with P.lock:
            valid = bool(sid) and P.sessions.get(sid) == token and token not in ("", "Fetch")
        if not valid:
            return sap_error(403, "CSRF", "CSRF token validation failed", {"x-csrf-token": "Required"})
        m = KEY.match(rest)
        if method != "PATCH" or not m or m.group(1) != "A_SalesOrder" or m.group(3):
            return sap_error(405, "METHOD", "This service only supports PATCH on a single A_SalesOrder")
        no = m.group(2)
        with P.lock:
            o = P.orders.get(no)
            if not o:
                return sap_error(404, "/IWBEP/CM_MGW_RT/020", f"Resource not found for segment 'A_SalesOrder' ({no})")
            if no in P.chaos["sap_locked"]:
                return sap_error(400, "V1/311", f"Sales order {no} is currently being processed by user KOFI.M")
            if P.chaos["sap_etag_bump"] > 0:
                P.chaos["sap_etag_bump"] -= 1
                o["_version"] += 1      # someone else changed it between your read and your write
            match = request.headers.get("if-match")
            if not match:
                return sap_error(428, "PRECOND", "If-Match header is required for this operation")
            if match != "*" and match != _etag(o):
                return sap_error(412, "/IWBEP/CM_MGW_RT/024", "The entity was changed by another user. Read it again before you change it")
            try:
                body = await request.json()
            except Exception:
                return sap_error(400, "BODY", "Body must be JSON")
            if set(body) - {"DeliveryBlockReason"}:
                return sap_error(400, "PROP", f"Property not updatable: {', '.join(sorted(set(body) - {'DeliveryBlockReason'}))}")
            code = body.get("DeliveryBlockReason", "")
            if code not in BLOCK_CODES:
                return sap_error(400, "VALUE", f"Delivery block reason '{code}' does not exist")
            if o["OverallDeliveryStatus"] == "C":
                return sap_error(400, "V1/105", f"Sales order {no} is already completely delivered: a delivery block can no longer be set")
            o["DeliveryBlockReason"] = code
            o["_version"] += 1

        return Response(status_code=204)

    # ----- reads -----
    fetch = request.headers.get("x-csrf-token") == "Fetch"
    headers = {}
    if fetch:
        with P.lock:
            sid = request.cookies.get(COOKIE) or secrets.token_hex(8)
            token = P.sessions.setdefault(sid, secrets.token_urlsafe(16))
        headers["x-csrf-token"] = token
        headers["set-cookie"] = f"{COOKIE}={sid}; Path=/; HttpOnly"

    if rest.endswith("/$count"):
        s = rest[:-len("/$count")]
        if s not in SETS:
            return sap_error(404, "/IWBEP/CM_MGW_RT/020", f"Resource not found for segment '{s}'")
        rows = list(P.orders.values()) if s == "A_SalesOrder" else list(P.partners.values())
        if qp.get("$filter"):
            rows = _filter(rows, qp["$filter"])
        return Response(str(len(rows)), media_type="text/plain", headers=headers)

    m = KEY.match(rest)
    if m:
        set_name, key, _, nav = m.groups()
        with P.lock:
            rec = (P.orders if set_name == "A_SalesOrder" else P.partners).get(key)
            if not rec:
                return sap_error(404, "/IWBEP/CM_MGW_RT/020", f"Resource not found for segment '{set_name}' ({key}). Keys are zero-padded, e.g. '0000012345'")
            if not _wants_json(request):
                return _atom(set_name, [rec], "SalesOrder" if set_name == "A_SalesOrder" else "BusinessPartner")
            if nav:
                return JSONResponse({"d": {"results": [{"__metadata": {"type": "API_SALES_ORDER_SRV.A_SalesOrderItemType"}, **i} for i in rec["_items"]]}}, headers=headers)
            expand = "to_Item" in qp.get("$expand", "")
            ent = _entity(set_name, rec, base, expand)
            if qp.get("$select"):
                keep = set(qp["$select"].split(",")) | {"__metadata"} | ({"to_Item"} if expand else set())
                ent = {k: v for k, v in ent.items() if k in keep}
            if set_name == "A_SalesOrder":
                headers["ETag"] = _etag(rec)
            return JSONResponse({"d": ent}, headers=headers)

    if rest in SETS:
        with P.lock:
            rows = list((P.orders if rest == "A_SalesOrder" else P.partners).values())
            try:
                if qp.get("$filter"):
                    rows = _filter(rows, qp["$filter"])
            except (ValueError, TypeError) as ex:
                return sap_error(400, "/IWBEP/CM_MGW_RT/022", f"Invalid $filter: {ex}. Dates need datetime'2026-10-01T00:00:00'")
            if qp.get("$orderby"):
                f, _, direction = qp["$orderby"].partition(" ")
                if rows and f not in rows[0]:
                    return sap_error(400, "/IWBEP/CM_MGW_RT/022", f"Unknown property {f} in $orderby")
                rows = sorted(rows, key=lambda r: r[f], reverse=direction.strip() == "desc")
            total = len(rows)
            try:
                skip = int(qp.get("$skiptoken") or qp.get("$skip") or 0)
                top = int(qp["$top"]) if qp.get("$top") else None
            except ValueError:
                return sap_error(400, "/IWBEP/CM_MGW_RT/022", "$top, $skip and $skiptoken must be integers")
            cap = P.SAP_PAGE_CAP if top is None else min(top, P.SAP_PAGE_CAP)
            page = rows[skip:skip + cap]
            more = top is None and skip + cap < total
            if not _wants_json(request):
                return _atom(rest, page, "SalesOrder" if rest == "A_SalesOrder" else "BusinessPartner")
            expand = "to_Item" in qp.get("$expand", "")
            results = [_entity(rest, r, base, expand) for r in page]
            if qp.get("$select"):
                keep = set(qp["$select"].split(",")) | {"__metadata"} | ({"to_Item"} if expand else set())
                results = [{k: v for k, v in r.items() if k in keep} for r in results]
            d = {"results": results}
            if qp.get("$inlinecount") == "allpages":
                d["__count"] = str(total)
            if more:
                d["__next"] = f"{base}/{rest}?$skiptoken={skip + cap}" + "".join(f"&{k}={v}" for k, v in qp.items() if k not in ("$skiptoken", "$skip"))
            return JSONResponse({"d": d}, headers=headers)

    return sap_error(404, "/IWBEP/CM_MGW_RT/020", f"Resource not found for segment '{rest.split('/')[0]}'")
