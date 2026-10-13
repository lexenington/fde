"""Volta Industrial Supplies' enterprise platforms: a ServiceNow instance and an SAP S/4HANA system (and the shared
chaos switches, request log and seed data). The routers are in snow.py and sap.py.

Both behave the way the real ones do, including the parts that hurt:

ServiceNow: Basic auth, every value a string, reference fields as {link, value}, `sysparm_query` strings, a 50-row
page cap with a Link header, no idempotency (so `correlation_id` is yours to use), business rules that abort updates
with 403, closed incidents that are read-only, 429s, and a hibernating instance that answers 503 with an HTML page.

SAP: OData v2, `Accept: application/json` or you get Atom XML, dates as /Date(ms)/, amounts as strings, zero-padded
keys, CSRF token + session cookie for every write, ETag/If-Match, `$skiptoken` paging, lock errors, and slow answers.
"""

import random
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone

from . import config

SNOW_USER, SNOW_PASSWORD = "svc_agent", "SnowPass!23"
SAP_USER, SAP_PASSWORD, SAP_CLIENT = "AGENT01", "SapPass!23", "100"
SNOW_PAGE_CAP = 50
SAP_PAGE_CAP = 50
NEEDS_APPROVAL_OVER_GHS = 50_000     # the customer's rule, enforced by YOUR tool layer

STATE_LABELS = {"1": "New", "2": "In Progress", "3": "On Hold", "6": "Resolved", "7": "Closed", "8": "Canceled"}
PRIORITY = {("1", "1"): "1", ("1", "2"): "2", ("2", "1"): "2", ("1", "3"): "3", ("2", "2"): "3", ("3", "1"): "3",
            ("2", "3"): "4", ("3", "2"): "4", ("3", "3"): "5"}
PEOPLE = [
    ("Kwabena Ofori", "kwabena.ofori"), ("Esi Tetteh", "esi.tetteh"), ("Nana Yaa Boateng", "nanayaa.boateng"),
    ("Kojo Antwi", "kojo.antwi"), ("Abena Sarpong", "abena.sarpong"), ("Yaw Darko", "yaw.darko"),
    ("Akosua Mensimah", "akosua.mensimah"), ("Kwesi Appiah", "kwesi.appiah"), ("Efua Quaye", "efua.quaye"),
    ("Mohammed Fuseini", "mohammed.fuseini"), ("Gifty Asare", "gifty.asare"), ("Samuel Nkrumah", "samuel.nkrumah"),
]
BIG_CALLER = "kwabena.ofori@volta.example"      # 123 incidents: the pagination test
FOLLOW_UP_INCIDENT = "INC0010007"                # open, In Progress: the comment test
CLOSED_INCIDENT = "INC0010011"                   # Closed: read-only
BIG_CALLER_COUNT = 123

CUSTOMERS = [("0010000042", "Volta Cement Ltd"), ("0010000043", "Takoradi Marine Services"), ("0010000044", "Kumasi Bolt & Fastener Co"),
             ("0010000045", "Tamale Agro Supplies"), ("0010000046", "Accra Packaging Ltd"), ("0010000047", "Ho Poultry Cooperative"),
             ("0010000048", "Cape Coast Hotels Group"), ("0010000049", "Sunyani Timber Works")]
MATERIALS = [("CEM-42R", "Portland cement 42.5R, 50kg"), ("RBR-12", "Reinforcing bar 12mm"), ("PVC-110", "PVC pipe 110mm"),
             ("PAL-EU", "Euro pallet"), ("FST-M10", "Bolt set M10"), ("TRP-4X6", "Tarpaulin 4x6m")]

lock = threading.RLock()
log: deque = deque(maxlen=800)       # every call the learner's app makes to ServiceNow or SAP
chaos: dict = {}
users: list[dict] = []
incidents: list[dict] = []
journal: list[dict] = []
orders: dict[str, dict] = {}
partners: dict[str, dict] = {}
sessions: dict[str, str] = {}        # SAP session id -> csrf token
next_inc = [10200]


def _ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def new_sys_id() -> str:
    return "%032x" % random.getrandbits(128)


def reset_chaos():
    chaos.clear()
    chaos.update({"snow_429": 0, "snow_503": 0, "retry_after": 1, "sap_slow_ms": 0, "sap_locked": [], "sap_etag_bump": 0})


def _incident(n: int, caller: dict, summary: str, state: str, urgency: str, created: datetime, **kw) -> dict:
    impact = kw.pop("impact", "3")
    return {"sys_id": new_sys_id(), "number": f"INC{n:07d}", "short_description": summary, "description": kw.pop("description", ""),
            "state": state, "urgency": urgency, "impact": impact, "priority": PRIORITY[(urgency, impact)],
            "category": kw.pop("category", "inquiry"), "caller_id": caller["sys_id"], "assigned_to": "", "correlation_id": kw.pop("correlation_id", ""),
            "sys_created_on": _ts(created), "sys_updated_on": _ts(created), "opened_at": _ts(created),
            "close_code": kw.pop("close_code", ""), "close_notes": kw.pop("close_notes", ""), **kw}


def seed():
    rnd = random.Random(7)
    base = datetime(2026, 10, 6, 8, 0, tzinfo=timezone.utc)
    with lock:
        users.clear(); incidents.clear(); journal.clear(); orders.clear(); partners.clear(); sessions.clear()
        next_inc[0] = 10200
        reset_chaos()
        for name, handle in PEOPLE:
            users.append({"sys_id": new_sys_id(), "user_name": handle, "name": name, "email": f"{handle}@volta.example", "active": "true",
                          "department": rnd.choice(["Finance", "Operations", "Sales", "IT", "Logistics"])})
        by_email = {u["email"]: u for u in users}
        summaries = ["VPN will not connect", "Cannot print to the 2nd-floor printer", "Laptop battery swollen", "Password reset",
                     "SAP GUI crashes on login", "Email not syncing on phone", "Request: second monitor", "Wi-Fi drops in the warehouse",
                     "Shared drive access", "Barcode scanner not pairing"]
        # fixed incidents the checks refer to (numbers 1-12)
        esi, kwa = by_email["esi.tetteh@volta.example"], by_email[BIG_CALLER]
        for i in range(1, 13):
            caller = esi if i in (7, 8) else users[2 + i % (len(users) - 2)]
            state = "7" if i == 11 else "2" if i == 7 else "1"
            incidents.append(_incident(10000 + i, caller, "VPN not connecting from home" if i == 7 else summaries[i % 10], state, "2",
                                       base - timedelta(days=30 - i), close_code="Solved (Permanently)" if i == 11 else "",
                                       close_notes="Fixed" if i == 11 else ""))
        # the big caller: 123 incidents, mixed states
        for k in range(BIG_CALLER_COUNT):
            state = rnd.choices(["1", "2", "3", "6", "7"], [3, 2, 1, 2, 8])[0]
            incidents.append(_incident(10013 + k, kwa, f"{summaries[k % 10]} (#{k + 1})", state, rnd.choice(["1", "2", "3", "3"]),
                                       base - timedelta(days=200 - k), close_code="Solved (Permanently)" if state in "67" else "",
                                       close_notes="Done" if state in "67" else ""))
        for k in range(30):
            incidents.append(_incident(10136 + k, rnd.choice(users[2:]), summaries[k % 10], rnd.choice(["1", "2", "7"]), "3", base - timedelta(days=60 - k)))
        # SAP
        for bp, name in CUSTOMERS:
            partners[bp] = {"BusinessPartner": bp, "BusinessPartnerFullName": name, "BusinessPartnerCategory": "2", "Country": "GH"}
        specs = {
            "0000012345": dict(bp="0010000042", total=12450.00, proc="B", deliv="A", day="2026-09-14", n=3),
            "0000012346": dict(bp="0010000043", total=8300.50, proc="C", deliv="C", day="2026-09-02", n=2),
            "0000012347": dict(bp="0010000044", total=78900.00, proc="A", deliv="A", day="2026-10-01", n=4),
            "0000012348": dict(bp="0010000045", total=2150.75, proc="A", deliv="A", day="2026-10-03", n=1),
            "0000012349": dict(bp="0010000046", total=5400.00, proc="A", deliv="A", day="2026-10-04", n=2),
            "0000012350": dict(bp="0010000047", total=3900.00, proc="A", deliv="A", day="2026-10-04", n=2),
            "0000012351": dict(bp="0010000048", total=15600.00, proc="B", deliv="B", day="2026-09-28", n=3),
            "0000012352": dict(bp="0010000049", total=980.00, proc="A", deliv="A", day="2026-10-05", n=1),
        }
        for i in range(8, 130):
            specs[f"{12345 + i:010d}"] = dict(bp=CUSTOMERS[i % 8][0], total=round(rnd.uniform(500, 40000), 2), proc="C", deliv="C",
                                                   day=f"2026-0{rnd.randint(6, 9)}-{rnd.randint(10, 28)}", n=rnd.randint(1, 3))
        for no, sp in specs.items():
            items, remaining = [], sp["total"]
            for j in range(sp["n"]):
                net = round(remaining if j == sp["n"] - 1 else round(sp["total"] / sp["n"], 2), 2)
                remaining = round(remaining - net, 2)
                mat = MATERIALS[(int(no) + j) % len(MATERIALS)]
                qty = rnd.randint(5, 200)
                items.append({"SalesOrder": no, "SalesOrderItem": f"{(j + 1) * 10:06d}", "Material": mat[0], "SalesOrderItemText": mat[1],
                              "RequestedQuantity": f"{qty}.000", "RequestedQuantityUnit": "EA", "NetAmount": f"{net:.2f}", "TransactionCurrency": "GHS"})
            day = datetime.fromisoformat(sp["day"]).replace(tzinfo=timezone.utc)
            orders[no] = {"SalesOrder": no, "SalesOrderType": "OR", "SoldToParty": sp["bp"], "SalesOrderDate": day, "CreationDate": day,
                          "TotalNetAmount": f"{sp['total']:.2f}", "TransactionCurrency": "GHS", "OverallSDProcessStatus": sp["proc"],
                          "OverallDeliveryStatus": sp["deliv"], "DeliveryBlockReason": "", "_version": 1, "_items": items}


def note(entry: dict):
    with lock:
        log.append(entry)


def public_state() -> dict:
    with lock:
        recent = sorted(incidents, key=lambda i: i["sys_created_on"], reverse=True)[:25]
        names = {u["sys_id"]: u["name"] for u in users}
        return {
            "chaos": dict(chaos),
            "incidents_total": len(incidents),
            "incidents": [{"number": i["number"], "short_description": i["short_description"], "state": STATE_LABELS.get(i["state"], i["state"]),
                           "priority": i["priority"], "caller": names.get(i["caller_id"], "?"), "correlation_id": i["correlation_id"],
                           "created": i["sys_created_on"]} for i in recent],
            "orders": [{"SalesOrder": o["SalesOrder"], "customer": partners[o["SoldToParty"]]["BusinessPartnerFullName"], "total": o["TotalNetAmount"],
                        "processing": o["OverallSDProcessStatus"], "delivery": o["OverallDeliveryStatus"], "block": o["DeliveryBlockReason"],
                        "locked": o["SalesOrder"] in chaos["sap_locked"]} for o in list(orders.values())[:12]],
            "calls": [dict(c) for c in list(log)[-40:]][::-1],
            "credentials": {"servicenow": {"base_url": "http://localhost:8090/servicenow", "user": SNOW_USER, "password": SNOW_PASSWORD},
                            "sap": {"base_url": "http://localhost:8090/sap/opu/odata/sap/API_SALES_ORDER_SRV", "user": SAP_USER,
                                    "password": SAP_PASSWORD, "sap_client": SAP_CLIENT}},
        }


seed()
