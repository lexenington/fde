"""02/06 Enterprise platforms: drives YOUR agent's tool layer against Volta's ServiceNow and SAP, then scores it.

Contract: 02-technical-depth/06-enterprise-platforms/lab/CONTRACT.md
The checks play the part of the model: they make the tool calls an agent would make, and then look at what really happened
inside the two systems (which they can see and your app can only reach through the APIs).
"""

import re
import time
from concurrent.futures import ThreadPoolExecutor

import httpx

from .. import platforms as P
from .. import config
from ..crm import store
from .base import Blocked, Fail, Suite, expect

suite = Suite(lab="06-enterprise-platforms", title="Volta Industrial Supplies: agent tool layer")
ESI, KWABENA = "esi.tetteh@volta.example", P.BIG_CALLER
STATUS = {"A": "not yet processed", "B": "partially processed", "C": "completely processed"}


class Ctx:
    def __init__(self):
        self.run_id = time.strftime("%Y%m%d-%H%M%S")
        self.learner_url = store.learner_url.rstrip("/")
        self.http = httpx.Client(base_url=self.learner_url, timeout=45)
        self.status: dict[str, str] = {}
        self.tag = time.strftime("%H%M%S")
        self.n = 0
        P.seed()
        P.log.clear()

    def rid(self, what: str) -> str:
        self.n += 1
        return f"rq-{self.tag}-{what}-{self.n}"

    def needs(self, *ids):
        failed = [i for i in ids if self.status.get(i) != "pass"]
        if failed:
            raise Blocked(f"needs {', '.join(failed)} to pass first")

    def create(self, **over) -> httpx.Response:
        body = {"request_id": self.rid("inc"), "caller_email": ESI, "short_description": "Cannot open the payroll portal",
                "description": "Error 500 since this morning", "urgency": 2, "category": "software", **over}
        return self.http.post("/api/tools/create_incident", json=body)

    def hold(self, order: str, **over) -> httpx.Response:
        body = {"request_id": self.rid("hold"), "order": order, "reason": "Customer credit review pending", **over}
        return self.http.post("/api/tools/hold_order", json=body)


def incidents_with(corr: str) -> list[dict]:
    with P.lock:
        return [i for i in P.incidents if i["correlation_id"] == corr]


def comments_on(number: str) -> list[dict]:
    with P.lock:
        inc = next(i for i in P.incidents if i["number"] == number)
        return [j for j in P.journal if j["incident"] == inc["sys_id"] and j["kind"] == "comments"]


def user_id(email: str) -> str:
    return next(u["sys_id"] for u in P.users if u["email"] == email)


def json_of(r: httpx.Response, what: str) -> dict:
    try:
        return r.json()
    except Exception:
        raise Fail(f"{what}: the response was not JSON (status {r.status_code}): {r.text[:120]!r}")


def is_client_error(r: httpx.Response) -> bool:
    return 400 <= r.status_code < 500


def calls_since(mark: int, system: str | None = None) -> list[dict]:
    with P.lock:
        rows = list(P.log)[mark:] if mark <= len(P.log) else list(P.log)
    return [c for c in rows if system is None or c["system"] == system]


def mark() -> int:
    return len(P.log)


class chaos:
    """Set a platform condition for one check and always put it back."""
    def __init__(self, **kw):
        self.kw = kw

    def __enter__(self):
        with P.lock:
            P.chaos.update(self.kw)

    def __exit__(self, *a):
        with P.lock:
            P.chaos.update({"snow_429": 0, "snow_503": 0, "sap_slow_ms": 0, "sap_locked": [], "sap_etag_bump": 0})


@suite.check("preflight", "Setup", "Your agent's tool layer is reachable", 0,
             "Start your app on port 8000 and expose GET /health. See lab/CONTRACT.md.")
def preflight(ctx: Ctx):
    r = ctx.http.get("/health", timeout=5)
    expect(r, range(200, 300), "GET /health")
    return f"{ctx.learner_url} answered {r.status_code}"


# ======================= ServiceNow =======================

@suite.check("snow.create", "ServiceNow: incidents", "Creates a correct incident from a tool call", 8,
             "Look the caller up in sys_user by email, send their sys_id as caller_id, set correlation_id to your request_id, and send values as strings. Response: {number, sys_id, state, priority, created}.")
def snow_create(ctx: Ctx):
    rid = ctx.rid("create")
    r = expect(ctx.create(request_id=rid, urgency=1), range(200, 300), "create_incident")
    j = json_of(r, "create_incident")
    if not re.fullmatch(r"INC\d{7}", str(j.get("number", ""))):
        raise Fail(f"`number` should look like INC0010200, got {j.get('number')!r}")
    rows = incidents_with(rid)
    if len(rows) != 1:
        raise Fail(f"expected exactly one incident with correlation_id {rid!r}, found {len(rows)}")
    inc = rows[0]
    if inc["number"] != j["number"]:
        raise Fail(f"you returned {j['number']} but the incident ServiceNow made is {inc['number']}")
    if inc["caller_id"] != user_id(ESI):
        raise Fail("the incident's caller is not Esi Tetteh (caller_id must be the sys_id found by looking her up by email)")
    if (inc["short_description"], inc["urgency"], inc["category"], inc["state"]) != ("Cannot open the payroll portal", "1", "software", "1"):
        raise Fail(f"fields on the incident are wrong: short_description={inc['short_description']!r} urgency={inc['urgency']!r} category={inc['category']!r} state={inc['state']!r}")
    if str(j.get("priority")) != inc["priority"]:
        raise Fail(f"priority in your response is {j.get('priority')!r}; ServiceNow computed {inc['priority']!r}")
    if j.get("created") is not True:
        raise Fail("`created` should be true for a new incident")
    return f"{inc['number']} for Esi Tetteh, priority {inc['priority']}"


@suite.check("snow.caller", "ServiceNow: incidents", "Finds the caller however the email is typed, and refuses unknown callers", 6,
             "Normalise (trim, lowercase) before the sys_user lookup. If nobody matches, return 404 or 422 and create nothing: an incident with no caller is a ticket nobody can answer.")
def snow_caller(ctx: Ctx):
    rid = ctx.rid("caller")
    r = expect(ctx.create(request_id=rid, caller_email="  ESI.Tetteh@Volta.Example "), range(200, 300), "create_incident with a messy email")
    inc = (incidents_with(rid) or [None])[0]
    if not inc or inc["caller_id"] != user_id(ESI):
        raise Fail("a differently-typed email did not resolve to Esi Tetteh")
    before = len(P.incidents)
    rid2 = ctx.rid("nobody")
    r = ctx.create(request_id=rid2, caller_email="nobody.here@volta.example")
    if r.status_code not in (404, 422) or incidents_with(rid2):
        raise Fail(f"an unknown caller should give 404 or 422 and create nothing; got {r.status_code}, {len(incidents_with(rid2))} incident(s) created")
    return "messy email resolved; unknown caller refused"


@suite.check("snow.idem", "ServiceNow: incidents", "The same request twice is one incident", 8,
             "ServiceNow has no idempotency. Search `correlation_id=<request_id>` first (or keep a table), and return the existing number with created=false.")
def snow_idem(ctx: Ctx):
    rid = ctx.rid("idem")
    a = json_of(expect(ctx.create(request_id=rid), range(200, 300), "first create"), "first create")
    b = json_of(expect(ctx.create(request_id=rid), range(200, 300), "second create"), "second create")
    if a.get("number") != b.get("number"):
        raise Fail(f"the retry returned {b.get('number')} but the first call made {a.get('number')}")
    if len(incidents_with(rid)) != 1:
        raise Fail(f"{len(incidents_with(rid))} incidents exist for one request_id")
    if b.get("created") is not False:
        raise Fail("the repeat should say created=false")
    return f"one incident ({a['number']})"


@suite.check("snow.race", "ServiceNow: incidents", "Eight simultaneous identical requests make one incident", 6,
             "A check-then-create is a race. Serialise per request_id (a lock keyed by it) or use a unique constraint in your own store, before you call ServiceNow.")
def snow_race(ctx: Ctx):
    ctx.needs("snow.idem")
    rid = ctx.rid("race")
    with ThreadPoolExecutor(8) as pool:
        rs = list(pool.map(lambda _: ctx.create(request_id=rid), range(8)))
    bad = [r.status_code for r in rs if not 200 <= r.status_code < 300]
    if bad:
        raise Fail(f"some parallel calls failed: {bad}")
    n = len(incidents_with(rid))
    if n != 1:
        raise Fail(f"8 parallel calls created {n} incidents")
    return "one incident"


@suite.check("snow.validate", "ServiceNow: incidents", "Bad input is refused before it reaches ServiceNow", 4,
             "urgency must be 1, 2 or 3; short_description is required. Answer 422 (or 400) and create nothing.")
def snow_validate(ctx: Ctx):
    for label, over in (("urgency 7", {"urgency": 7}), ("empty summary", {"short_description": "  "})):
        rid = ctx.rid("bad")
        r = ctx.create(request_id=rid, **over)
        if not is_client_error(r) or incidents_with(rid):
            raise Fail(f"{label}: expected a 4xx and no incident, got {r.status_code} and {len(incidents_with(rid))} incident(s)")
    return "both refused"


@suite.check("snow.comment", "ServiceNow: comments", "Adds a customer-visible comment once", 6,
             "Find the incident by number, PATCH `comments` (journal fields read back empty, so you can't dedupe by reading them: keep your own record of request_ids). Response: {number, applied}.")
def snow_comment(ctx: Ctx):
    rid = ctx.rid("cmt")
    body = {"request_id": rid, "number": P.FOLLOW_UP_INCIDENT, "comment": "Still failing after the restart; tried on the office network too."}
    a = json_of(expect(ctx.http.post("/api/tools/add_comment", json=body), range(200, 300), "add_comment"), "add_comment")
    b = json_of(expect(ctx.http.post("/api/tools/add_comment", json=body), range(200, 300), "add_comment again"), "add_comment again")
    got = comments_on(P.FOLLOW_UP_INCIDENT)
    if len(got) != 1 or got[0]["text"] != body["comment"]:
        raise Fail(f"expected exactly one comment with the right text on {P.FOLLOW_UP_INCIDENT}, found {len(got)}")
    if a.get("applied") is not True or b.get("applied") is not False:
        raise Fail(f"`applied` should be true then false; got {a.get('applied')!r} then {b.get('applied')!r}")
    return "applied once"


@suite.check("snow.closed", "ServiceNow: comments", "A closed incident gives a clean refusal, not a 500", 4,
             "ServiceNow answers 403 for closed incidents. Turn that into 409 (or 422) with {error: ...}: the agent has to be able to tell the user to open a new one.")
def snow_closed(ctx: Ctx):
    before = len(comments_on(P.CLOSED_INCIDENT))
    r = ctx.http.post("/api/tools/add_comment", json={"request_id": ctx.rid("closed"), "number": P.CLOSED_INCIDENT, "comment": "Any update on this?"})
    if r.status_code not in (409, 422) or not json_of(r, "add_comment on closed").get("error"):
        raise Fail(f"expected 409 or 422 with an `error` message, got {r.status_code}: {r.text[:120]}")
    if len(comments_on(P.CLOSED_INCIDENT)) != before:
        raise Fail("a comment was written to a closed incident")
    return f"{r.status_code} with a message"


@suite.check("snow.page", "ServiceNow: reading", "Returns all 123 of Kwabena's incidents, across pages", 8,
             "The Table API caps a page at 50 and gives you X-Total-Count and a Link header (rel=\"next\"). Follow it, or keep adding sysparm_offset, until you have them all.")
def snow_page(ctx: Ctx):
    r = expect(ctx.http.get("/api/tools/my_incidents", params={"caller_email": KWABENA}), {200}, "my_incidents")
    j = json_of(r, "my_incidents")
    nums = [i.get("number") for i in j.get("incidents", [])]
    if j.get("count") != P.BIG_CALLER_COUNT or len(nums) != P.BIG_CALLER_COUNT or len(set(nums)) != P.BIG_CALLER_COUNT:
        raise Fail(f"Kwabena has {P.BIG_CALLER_COUNT} incidents; you returned count={j.get('count')} and {len(nums)} rows ({len(set(nums))} distinct). Did you stop after the first page?")
    return f"all {len(nums)} incidents"


@suite.check("snow.open", "ServiceNow: reading", "`open=true` returns only New, In Progress and On Hold", 4,
             "Filter in the query (`state IN 1,2,3`), not after fetching everything: a customer with 40,000 incidents will not thank you.")
def snow_open(ctx: Ctx):
    ctx.needs("snow.page")
    r = expect(ctx.http.get("/api/tools/my_incidents", params={"caller_email": KWABENA, "open": "true"}), {200}, "my_incidents open")
    j = json_of(r, "my_incidents open")
    with P.lock:
        want = {i["number"] for i in P.incidents if i["caller_id"] == user_id(KWABENA) and i["state"] in ("1", "2", "3")}
    got = {i["number"] for i in j.get("incidents", [])}
    if got != want:
        raise Fail(f"expected {len(want)} open incidents, got {len(got)} (missing {len(want - got)}, extra {len(got - want)})")
    return f"{len(got)} open"


@suite.check("snow.scope", "ServiceNow: reading", "Only the caller's own incidents, with readable states", 5,
             "Filter by caller_id = the sys_id. States come back as '1'..'8'; return the label (sysparm_display_value=true, or map them): 'In Progress', not '2'.")
def snow_scope(ctx: Ctx):
    r = expect(ctx.http.get("/api/tools/my_incidents", params={"caller_email": ESI}), {200}, "my_incidents for Esi")
    j = json_of(r, "my_incidents for Esi")
    with P.lock:
        mine = {i["number"] for i in P.incidents if i["caller_id"] == user_id(ESI)}
    nums = {i.get("number") for i in j.get("incidents", [])}
    if nums != mine:
        raise Fail(f"Esi has {len(mine)} incidents; you returned {len(nums)} ({len(nums - mine)} that are not hers)")
    row = next((i for i in j["incidents"] if i["number"] == P.FOLLOW_UP_INCIDENT), None)
    if not row or row.get("state") != "In Progress":
        raise Fail(f"{P.FOLLOW_UP_INCIDENT} should read state 'In Progress', got {row and row.get('state')!r}")
    r = ctx.http.get("/api/tools/my_incidents", params={"caller_email": "nobody.here@volta.example"})
    if r.status_code != 404:
        raise Fail(f"an unknown caller should be 404, got {r.status_code}")
    return "own incidents only; labels; unknown caller 404"


@suite.check("snow.429", "ServiceNow: when it misbehaves", "Rides out two 429s and honours Retry-After", 6,
             "On 429, wait for Retry-After seconds (the header, not a guess), then retry. Don't create the incident twice.")
def snow_429(ctx: Ctx):
    rid = ctx.rid("429")
    with chaos(snow_429=2, retry_after=1):
        t0 = time.monotonic()
        r = ctx.create(request_id=rid)
        took = time.monotonic() - t0
    expect(r, range(200, 300), "create_incident through two 429s")
    if len(incidents_with(rid)) != 1:
        raise Fail(f"{len(incidents_with(rid))} incidents after the 429s")
    if took < 1.5:
        raise Fail(f"it succeeded in {took:.1f}s: two Retry-After: 1 waits should take about 2s. Did you retry immediately?")
    return f"succeeded after {took:.1f}s"


@suite.check("snow.hibernate", "ServiceNow: when it misbehaves", "A hibernating instance (503 with an HTML page) doesn't crash you", 6,
             "A developer instance that has slept answers 503 with HTML, not JSON. `.json()` on that is your 500. Retry with backoff; don't parse an error page.")
def snow_hibernate(ctx: Ctx):
    rid = ctx.rid("hib")
    with chaos(snow_503=2):
        r = ctx.create(request_id=rid)
    expect(r, range(200, 300), "create_incident through two 503s with an HTML body")
    if len(incidents_with(rid)) != 1:
        raise Fail(f"{len(incidents_with(rid))} incidents after the 503s")
    return "rode it out"


@suite.check("snow.outage", "ServiceNow: when it misbehaves", "A real outage gives a fast, honest 503 and no half-made ticket", 6,
             "Give up after a few tries (say within 30 seconds) and return 502/503/504 with {error: ...} so the agent can tell the person. Never create a record you can't confirm.")
def snow_outage(ctx: Ctx):
    rid = ctx.rid("down")
    with chaos(snow_503=1000):
        t0 = time.monotonic()
        r = ctx.create(request_id=rid)
        took = time.monotonic() - t0
    if r.status_code not in (502, 503, 504):
        raise Fail(f"expected 502, 503 or 504 during an outage, got {r.status_code}")
    if not json_of(r, "outage response").get("error"):
        raise Fail("the outage response should carry an `error` message")
    if took > 35:
        raise Fail(f"took {took:.0f}s to give up. Someone is waiting on a WhatsApp reply")
    if incidents_with(rid):
        raise Fail("an incident exists for a request that was reported as failed")
    return f"gave up in {took:.0f}s with {r.status_code}"


# ======================= SAP =======================

@suite.check("sap.status", "SAP: reading", "Order status: right fields, right types", 8,
             "GET A_SalesOrder('0000012345')?$expand=to_Item with Accept: application/json. Amounts are strings ('12450.00'), dates are /Date(ms)/, and the status letters need translating. See CONTRACT.md for the exact response.")
def sap_status(ctx: Ctx):
    r = expect(ctx.http.get("/api/tools/order_status", params={"order": "0000012345"}), {200}, "order_status")
    j = json_of(r, "order_status")
    want = {"order": "0000012345", "customer_name": "Volta Cement Ltd", "currency": "GHS", "order_date": "2026-09-14",
            "status": "partially processed", "delivery_status": "not yet processed", "blocked": False}
    for k, v in want.items():
        if j.get(k) != v:
            raise Fail(f"`{k}` should be {v!r}, got {j.get(k)!r}")
    if not isinstance(j.get("total_amount"), (int, float)) or abs(j["total_amount"] - 12450.0) > 0.001:
        raise Fail(f"`total_amount` should be the number 12450.0, got {j.get('total_amount')!r}")
    items = P.orders["0000012345"]["_items"]
    got = j.get("items") or []
    if len(got) != len(items):
        raise Fail(f"the order has {len(items)} items, you returned {len(got)}")
    for it, g in zip(items, got):
        if (g.get("item"), g.get("material")) != (it["SalesOrderItem"], it["Material"]) or abs(float(g.get("quantity", -1)) - float(it["RequestedQuantity"])) > 0.001 \
                or abs(float(g.get("net_amount", -1)) - float(it["NetAmount"])) > 0.001:
            raise Fail(f"item {it['SalesOrderItem']} is wrong: expected {it['Material']} x {it['RequestedQuantity']} at {it['NetAmount']}, got {g}")
    return "all fields and 3 items correct"


@suite.check("sap.padding", "SAP: reading", "Accepts '12345', 'SO 12345' and a padded key", 5,
             "SAP keys are zero-padded to 10 characters. People type 12345. Normalise before you ask: A_SalesOrder('12345') is a 404.")
def sap_padding(ctx: Ctx):
    for raw in ("12345", "SO 12345", " 0000012345 ", "so-12345"):
        j = json_of(expect(ctx.http.get("/api/tools/order_status", params={"order": raw}), {200}, f"order_status({raw!r})"), "order_status")
        if j.get("order") != "0000012345":
            raise Fail(f"{raw!r} should resolve to 0000012345, got {j.get('order')!r}")
    return "four spellings, one order"


@suite.check("sap.notfound", "SAP: reading", "Unknown and nonsense orders are 404 and 4xx, not 500", 4,
             "Pass SAP's 404 on as a 404 with a readable message; reject input that can't be an order number yourself, before calling SAP.")
def sap_notfound(ctx: Ctx):
    r = ctx.http.get("/api/tools/order_status", params={"order": "0000099999"})
    if r.status_code != 404 or not json_of(r, "unknown order").get("error"):
        raise Fail(f"unknown order: expected 404 with an `error`, got {r.status_code}")
    r = ctx.http.get("/api/tools/order_status", params={"order": "drop table"})
    if r.status_code not in (400, 422):
        raise Fail(f"nonsense input: expected 400 or 422, got {r.status_code}")
    return "404 and 4xx"


@suite.check("sap.summary", "SAP: reading", "Orders since a date: right count and total, across pages", 8,
             "$filter=SalesOrderDate ge datetime'2026-10-01T00:00:00' (the datetime'...' wrapper is mandatory), then follow __next until it is gone. Sum the strings as decimals, not floats. Response: {count, total_amount}.")
def sap_summary(ctx: Ctx):
    for since in ("2026-10-01", "2026-01-01"):
        with P.lock:
            rows = [o for o in P.orders.values() if o["SalesOrderDate"].strftime("%Y-%m-%d") >= since]
        want_n, want_total = len(rows), round(sum(float(o["TotalNetAmount"]) for o in rows), 2)
        j = json_of(expect(ctx.http.get("/api/tools/orders_summary", params={"since": since}), {200}, f"orders_summary since {since}"), "orders_summary")
        if j.get("count") != want_n or abs(float(j.get("total_amount", -1)) - want_total) > 0.005:
            raise Fail(f"since {since}: expected {want_n} orders totalling {want_total:.2f}, got count={j.get('count')} total={j.get('total_amount')}")
    return "both ranges exact (the second needs 3 pages)"


@suite.check("sap.json", "SAP: reading", "Always asks for JSON", 4,
             "Without `Accept: application/json` (or $format=json) SAP answers in Atom XML. Every call you make must ask.")
def sap_json(ctx: Ctx):
    ctx.needs("sap.status")
    xml = [c for c in calls_since(0, "sap") if "xml" in c["content_type"] and "metadata" not in c["path"]]
    if xml:
        raise Fail(f"{len(xml)} of your SAP calls got XML back, e.g. {xml[0]['method']} {xml[0]['path']}: add Accept: application/json")
    return "no XML responses"


@suite.check("sap.hold", "SAP: writing", "Places a delivery block (CSRF token, session cookie, If-Match)", 8,
             "GET with `x-csrf-token: Fetch` and keep the cookie jar; send the token it returns and the ETag as If-Match on the PATCH. A 403 with x-csrf-token: Required means the token or cookie is missing. Body: {DeliveryBlockReason: '01'}.")
def sap_hold(ctx: Ctx):
    rid = ctx.rid("hold")
    r = expect(ctx.hold("0000012348", request_id=rid), range(200, 300), "hold_order")
    j = json_of(r, "hold_order")
    if P.orders["0000012348"]["DeliveryBlockReason"] != "01":
        raise Fail(f"SAP still shows DeliveryBlockReason {P.orders['0000012348']['DeliveryBlockReason']!r}")
    if j.get("blocked") is not True or j.get("order") != "0000012348":
        raise Fail(f"expected {{order: '0000012348', blocked: true}}, got {j}")
    return "order 0000012348 blocked in SAP"


@suite.check("sap.hold_idem", "SAP: writing", "The same hold twice is one change", 5,
             "Remember the request_ids you have applied. Repeat calls return the same answer without another PATCH.")
def sap_hold_idem(ctx: Ctx):
    ctx.needs("sap.hold")
    rid = ctx.rid("holdidem")
    ctx.hold("0000012352", request_id=rid)
    m = mark()
    r = expect(ctx.hold("0000012352", request_id=rid), range(200, 300), "hold_order again")
    patches = [c for c in calls_since(m, "sap") if c["method"] == "PATCH"]
    if patches:
        raise Fail(f"the repeat made {len(patches)} PATCH call(s) to SAP")
    if P.orders["0000012352"]["DeliveryBlockReason"] != "01":
        raise Fail("the order is not blocked")
    return "no second write"


@suite.check("sap.delivered", "SAP: writing", "An order already delivered is refused with the reason", 5,
             "SAP answers 400 'already completely delivered'. Return 409 with that message in `error`: the agent must be able to say why.")
def sap_delivered(ctx: Ctx):
    r = ctx.hold("0000012346")
    if r.status_code != 409 or "deliver" not in str(json_of(r, "hold on delivered").get("error", "")).lower():
        raise Fail(f"expected 409 with the reason mentioning delivery, got {r.status_code}: {r.text[:140]}")
    if P.orders["0000012346"]["DeliveryBlockReason"] != "":
        raise Fail("the delivered order was changed")
    return "409 with the reason"


@suite.check("sap.approval", "SAP: writing", "Orders over GHS 50,000 need a named approver", 6,
             "Policy lives in your code, not in the prompt (kata 10). Total over 50,000 and no `approved_by` ending in @volta.example -> 403 {error, needs_approval: true}. With one, proceed.")
def sap_approval(ctx: Ctx):
    r = ctx.hold("0000012347")
    j = json_of(r, "hold over the limit")
    if r.status_code != 403 or j.get("needs_approval") is not True:
        raise Fail(f"expected 403 with needs_approval=true for a GHS 78,900 order, got {r.status_code}: {j}")
    if P.orders["0000012347"]["DeliveryBlockReason"] != "":
        raise Fail("the order was blocked without approval")
    r = ctx.hold("0000012347", approved_by="not-an-approver@gmail.com")
    if r.status_code != 403:
        raise Fail(f"an approver outside volta.example should be refused, got {r.status_code}")
    expect(ctx.hold("0000012347", approved_by="esi.tetteh@volta.example"), range(200, 300), "hold with an approver")
    if P.orders["0000012347"]["DeliveryBlockReason"] != "01":
        raise Fail("with a valid approver the order should be blocked")
    return "403, 403, then allowed"


@suite.check("sap.reason", "SAP: writing", "A hold needs a real reason", 3,
             "reason must be at least 10 characters after trimming: it goes in the audit trail Esi hands to the auditors.")
def sap_reason(ctx: Ctx):
    r = ctx.hold("0000012353", reason="ok")
    if r.status_code != 422 or P.orders["0000012353"]["DeliveryBlockReason"] != "":
        raise Fail(f"a 2-character reason should be 422 and change nothing; got {r.status_code}")
    return "422"


@suite.check("sap.lock", "SAP: when it misbehaves", "A locked order says 'try again', and succeeds when it is free", 6,
             "SAP locks an order while someone edits it and answers 400 'currently being processed by user ...'. Return 423 (or 409/503) with {error, retry: true}; the agent will try later.")
def sap_lock(ctx: Ctx):
    with chaos(sap_locked=["0000012350"]):
        r = ctx.hold("0000012350")
        j = json_of(r, "hold on a locked order")
        if r.status_code not in (409, 423, 503) or j.get("retry") is not True:
            raise Fail(f"a locked order should be 423/409/503 with retry=true; got {r.status_code}: {j}")
        if P.orders["0000012350"]["DeliveryBlockReason"] != "":
            raise Fail("the locked order was changed")
    expect(ctx.hold("0000012350"), range(200, 300), "hold after the lock cleared")
    if P.orders["0000012350"]["DeliveryBlockReason"] != "01":
        raise Fail("after the lock cleared the order should be blocked")
    return "refused while locked, done once free"


@suite.check("sap.etag", "SAP: when it misbehaves", "Survives someone changing the order between your read and your write", 6,
             "A 412 means the ETag you hold is stale. Re-read the order (new ETag, same session), decide whether the change still makes sense, and PATCH again, once.")
def sap_etag(ctx: Ctx):
    m = mark()
    with chaos(sap_etag_bump=1):
        r = ctx.hold("0000012349")
    expect(r, range(200, 300), "hold when the order changed underneath you")
    if P.orders["0000012349"]["DeliveryBlockReason"] != "01":
        raise Fail("the order should end up blocked")
    seen = [c["status"] for c in calls_since(m, "sap") if c["method"] == "PATCH"]
    if 412 not in seen:
        raise Fail(f"expected to see a 412 and a retry; PATCH statuses were {seen}")
    return f"PATCH statuses {seen}"


@suite.check("sap.slow", "SAP: when it misbehaves", "A slow SAP (2.5 s per call) still gets an answer", 4,
             "Set a timeout longer than SAP's slowest normal answer (10 s or more), and don't retry a read three times in parallel on a timeout.")
def sap_slow(ctx: Ctx):
    with chaos(sap_slow_ms=2500):
        t0 = time.monotonic()
        r = ctx.http.get("/api/tools/order_status", params={"order": "0000012351"})
        took = time.monotonic() - t0
    j = json_of(expect(r, {200}, "order_status while SAP is slow"), "order_status")
    if j.get("order") != "0000012351":
        raise Fail(f"wrong order back: {j.get('order')!r}")
    return f"answered in {took:.1f}s"


@suite.check("sap.secrets", "Hygiene", "Credentials never travel in a URL", 3,
             "Basic auth goes in the Authorization header, from configuration. A password in a query string ends up in every proxy log.")
def secrets(ctx: Ctx):
    ctx.needs("snow.create")
    calls = calls_since(0)
    bare = [c for c in calls if not c["has_auth"]]
    if bare:
        raise Fail(f"{len(bare)} call(s) carried no Authorization header, e.g. {bare[0]['system']} {bare[0]['method']} {bare[0]['path']}")
    if any(c["auth_in_query"] for c in calls):
        raise Fail("a username or password appeared in a query string")
    return f"{len(calls)} calls, all authenticated in the header"


def run(only: set[str] | None = None, progress=None) -> dict:
    ctx = Ctx()
    try:
        return suite.run(ctx, workers=1, only=only, progress=progress)
    finally:
        ctx.http.close()
