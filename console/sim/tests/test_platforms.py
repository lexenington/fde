import base64

import pytest
from fastapi.testclient import TestClient

from sim import platforms as P
from sim.app import app
from sim.checks import SUITES

c = TestClient(app)
SN = "/servicenow/api/now/table"
SAP = "/sap/opu/odata/sap/API_SALES_ORDER_SRV"


def basic(u, p):
    return {"authorization": "Basic " + base64.b64encode(f"{u}:{p}".encode()).decode()}


SNOW_AUTH, SAP_AUTH = basic(P.SNOW_USER, P.SNOW_PASSWORD), basic(P.SAP_USER, P.SAP_PASSWORD)
JSON = {**SAP_AUTH, "accept": "application/json"}


@pytest.fixture(autouse=True)
def fresh():
    P.seed()
    P.log.clear()


def sys_id(email):
    return next(u["sys_id"] for u in P.users if u["email"] == email)


# ---------------- ServiceNow ----------------

def test_snow_needs_credentials():
    assert c.get(f"{SN}/incident").status_code == 401
    assert c.get(f"{SN}/incident", headers=basic("svc_agent", "wrong")).status_code == 401


def test_snow_pages_are_capped_with_a_total_and_a_next_link():
    r = c.get(f"{SN}/incident?sysparm_limit=1000", headers=SNOW_AUTH)
    assert len(r.json()["result"]) == 50 and int(r.headers["x-total-count"]) == len(P.incidents)
    assert 'rel="next"' in r.headers["link"] and "sysparm_offset=50" in r.headers["link"]
    last = c.get(f"{SN}/incident?sysparm_offset={len(P.incidents) - 3}", headers=SNOW_AUTH)
    assert len(last.json()["result"]) == 3 and 'rel="next"' not in last.headers["link"]


def test_snow_query_operators_and_ordering():
    kw = sys_id(P.BIG_CALLER)
    r = c.get(f"{SN}/incident", params={"sysparm_query": f"caller_id={kw}^stateIN1,2,3^ORDERBYDESCnumber", "sysparm_limit": 200}, headers=SNOW_AUTH)
    rows = r.json()["result"]
    assert 0 < len(rows) == int(r.headers["x-total-count"]) and all(x["state"] in "123" for x in rows)
    assert [x["number"] for x in rows] == sorted((x["number"] for x in rows), reverse=True)
    like = c.get(f"{SN}/incident", params={"sysparm_query": "short_descriptionLIKEvpn"}, headers=SNOW_AUTH).json()["result"]
    assert like and all("vpn" in x["short_description"].lower() for x in like)


def test_snow_values_are_strings_references_are_objects_and_display_value_gives_labels():
    row = c.get(f"{SN}/incident", params={"sysparm_query": f"number={P.FOLLOW_UP_INCIDENT}"}, headers=SNOW_AUTH).json()["result"][0]
    assert row["state"] == "2" and row["priority"] == "4" and isinstance(row["caller_id"], dict) and row["caller_id"]["value"]
    assert row["comments"] == "" and row["work_notes"] == ""
    shown = c.get(f"{SN}/incident", params={"sysparm_query": f"number={P.FOLLOW_UP_INCIDENT}", "sysparm_display_value": "true"}, headers=SNOW_AUTH).json()["result"][0]
    assert shown["state"] == "In Progress" and shown["caller_id"] == "Esi Tetteh"


def test_snow_create_needs_a_real_caller_and_computes_priority():
    body = {"short_description": "Printer jam", "urgency": "1", "correlation_id": "abc"}
    assert c.post(f"{SN}/incident", json={**body, "caller_id": "someone@x.com"}, headers=SNOW_AUTH).status_code == 400
    r = c.post(f"{SN}/incident", json={**body, "caller_id": sys_id("esi.tetteh@volta.example")}, headers=SNOW_AUTH)
    assert r.status_code == 201 and r.json()["result"]["priority"] == "3" and r.json()["result"]["number"] == "INC0010200"
    assert c.post(f"{SN}/incident", json={**body, "urgency": "9", "caller_id": sys_id("esi.tetteh@volta.example")}, headers=SNOW_AUTH).status_code == 400


def test_snow_business_rules_and_acls():
    inc = next(i for i in P.incidents if i["number"] == P.FOLLOW_UP_INCIDENT)
    r = c.patch(f"{SN}/incident/{inc['sys_id']}", json={"state": "6"}, headers=SNOW_AUTH)
    assert r.status_code == 403 and "mandatory" in r.json()["error"]["detail"]
    assert c.patch(f"{SN}/incident/{inc['sys_id']}", json={"comments": "hello"}, headers=SNOW_AUTH).status_code == 200
    assert [j["text"] for j in P.journal if j["incident"] == inc["sys_id"]] == ["hello"]
    closed = next(i for i in P.incidents if i["number"] == P.CLOSED_INCIDENT)
    assert c.patch(f"{SN}/incident/{closed['sys_id']}", json={"comments": "x"}, headers=SNOW_AUTH).status_code == 403
    assert c.delete(f"{SN}/incident/{inc['sys_id']}", headers=SNOW_AUTH).status_code == 403


def test_snow_chaos_429_then_hibernating_html():
    P.chaos.update(snow_429=1, snow_503=1, retry_after=3)
    r = c.get(f"{SN}/incident", headers=SNOW_AUTH)
    assert r.status_code == 503 and "text/html" in r.headers["content-type"] and "Hibernating" in r.text
    r = c.get(f"{SN}/incident", headers=SNOW_AUTH)
    assert r.status_code == 429 and r.headers["retry-after"] == "3"
    assert c.get(f"{SN}/incident", headers=SNOW_AUTH).status_code == 200


# ---------------- SAP ----------------

def test_sap_defaults_to_xml_unless_you_ask_for_json():
    r = c.get(f"{SAP}/A_SalesOrder", headers=SAP_AUTH)
    assert "atom+xml" in r.headers["content-type"]
    assert "json" in c.get(f"{SAP}/A_SalesOrder?$format=json", headers=SAP_AUTH).headers["content-type"]


def test_sap_entity_shapes_and_zero_padded_keys():
    d = c.get(f"{SAP}/A_SalesOrder('0000012345')?$expand=to_Item", headers=JSON).json()["d"]
    assert d["TotalNetAmount"] == "12450.00" and d["SalesOrderDate"].startswith("/Date(") and len(d["to_Item"]["results"]) == 3
    assert c.get(f"{SAP}/A_SalesOrder('12345')", headers=JSON).status_code == 404


def test_sap_filter_needs_datetime_literals_and_paging_uses_skiptoken():
    bad = c.get(f"{SAP}/A_SalesOrder", params={"$filter": "SalesOrderDate ge '2026-10-01'"}, headers=JSON)
    assert bad.status_code == 400
    ok = c.get(f"{SAP}/A_SalesOrder", params={"$filter": "SalesOrderDate ge datetime'2026-10-01T00:00:00'", "$inlinecount": "allpages"}, headers=JSON).json()["d"]
    assert ok["__count"] == "5" and len(ok["results"]) == 5 and "__next" not in ok
    page1 = c.get(f"{SAP}/A_SalesOrder", headers=JSON).json()["d"]
    assert len(page1["results"]) == 50 and "$skiptoken=50" in page1["__next"]
    page3 = c.get(f"{SAP}/A_SalesOrder?$skiptoken=100", headers=JSON).json()["d"]
    assert len(page3["results"]) == len(P.orders) - 100 and "__next" not in page3


def write_session():
    r = c.get(f"{SAP}/A_SalesOrder('0000012348')", headers={**JSON, "x-csrf-token": "Fetch"})
    return r.headers["x-csrf-token"], r.headers["etag"], r.cookies


def test_sap_writes_need_csrf_cookie_and_etag():
    tok, etag, cookies = write_session()
    url, body = f"{SAP}/A_SalesOrder('0000012348')", {"DeliveryBlockReason": "01"}
    r = TestClient(app).patch(url, json=body, headers={**JSON, "x-csrf-token": tok, "if-match": etag})      # a client with no session cookie
    assert r.status_code == 403 and r.headers["x-csrf-token"] == "Required"          # token without the session cookie
    r = c.patch(url, json=body, headers={**JSON, "x-csrf-token": tok})
    assert r.status_code == 428
    r = c.patch(url, json=body, headers={**JSON, "x-csrf-token": tok, "if-match": 'W/"stale"'})
    assert r.status_code == 412
    r = c.patch(url, json=body, headers={**JSON, "x-csrf-token": tok, "if-match": etag})
    assert r.status_code == 204 and P.orders["0000012348"]["DeliveryBlockReason"] == "01"
    again = c.patch(url, json=body, headers={**JSON, "x-csrf-token": tok, "if-match": etag})
    assert again.status_code == 412          # the ETag moved when the order changed


def test_sap_refuses_delivered_and_locked_orders():
    tok, etag, cookies = write_session()
    h = {**JSON, "x-csrf-token": tok, "if-match": "*"}
    done = c.patch(f"{SAP}/A_SalesOrder('0000012346')", json={"DeliveryBlockReason": "01"}, headers=h)
    assert done.status_code == 400 and "already completely delivered" in done.json()["error"]["message"]["value"]
    P.chaos["sap_locked"] = ["0000012348"]
    locked = c.patch(f"{SAP}/A_SalesOrder('0000012348')", json={"DeliveryBlockReason": "01"}, headers=h)
    assert locked.status_code == 400 and "currently being processed" in locked.json()["error"]["message"]["value"]


def test_sap_needs_credentials_and_serves_metadata():
    assert c.get(f"{SAP}/A_SalesOrder").status_code == 401
    assert "EntityType" in c.get(f"{SAP}/$metadata", headers=SAP_AUTH).text


# ---------------- Console wiring ----------------

def test_the_calls_are_logged_with_what_the_checks_need():
    c.get(f"{SN}/incident?sysparm_limit=1", headers=SNOW_AUTH)
    c.get(f"{SAP}/A_SalesOrder", headers=SAP_AUTH)
    first, second = list(P.log)
    assert first["system"] == "servicenow" and first["has_auth"] and not first["auth_in_query"]
    assert second["system"] == "sap" and "xml" in second["content_type"]


def test_admin_state_chaos_and_reset():
    assert c.post("/platforms/chaos", json={"sap_slow_ms": 10, "sap_locked": ["0000012350"]}).json()["chaos"]["sap_locked"] == ["0000012350"]
    st = c.get("/platforms/state").json()
    assert st["incidents_total"] == len(P.incidents) and st["credentials"]["sap"]["user"] == "AGENT01"
    assert c.post("/platforms/reset").json()["chaos"]["sap_slow_ms"] == 0


def test_the_suite_is_registered_and_everything_is_blocked_when_the_app_is_down(monkeypatch):
    from sim.crm import store
    monkeypatch.setattr(store, "learner_url", "http://127.0.0.1:9")
    s = SUITES["platforms"]
    assert len(s["suite"].checks) >= 25 and s["async"] and s["suite"].checks[0].id == "preflight"
    result = s["run"]()
    assert result["score"] == 0 and {r["status"] for r in result["results"]} <= {"fail", "blocked"}
