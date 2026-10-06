"""02/02 Enterprise integration: drives YOUR app through the customer's IdP, SCIM and CRM, then scores it.

Contract: 02-technical-depth/02-enterprise-integration/lab/CONTRACT.md
"""

import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import httpx

from .. import config, tokens
from ..crm import deliver, make_event, store, user_add_note, user_change_stage
from .base import Blocked, Fail, Suite, expect

suite = Suite(lab="02-enterprise-integration", title="Enterprise-ready RunMySales")
DENIED = {401, 403}
DENIED_OR_HIDDEN = {403, 404}


class Ctx:
    def __init__(self):
        self.run_id = time.strftime("%Y%m%d-%H%M%S")
        self.learner_url = store.learner_url.rstrip("/")
        self.http = httpx.Client(base_url=self.learner_url, timeout=15)
        self.status: dict[str, str] = {}
        self.tag = uuid.uuid4().hex[:6]
        self._tokens: dict[tuple, str] = {}
        self.deal_b1: str | None = None

    def token(self, user: str, client: str = "runmysales") -> str:
        if (user, client) not in self._tokens:
            try:
                self._tokens[(user, client)] = tokens.get_token(user, client)
            except tokens.IdPError as e:
                raise Blocked(str(e))
        return self._tokens[(user, client)]

    def as_user(self, user: str) -> dict:
        return {"authorization": f"Bearer {self.token(user)}"}

    def needs(self, *ids: str):
        failed = [i for i in ids if self.status.get(i) != "pass"]
        if failed:
            raise Blocked(f"needs {', '.join(failed)} to pass first")

    def booking(self, n: str) -> dict:
        return {"booking_id": f"bk_{self.tag}_{n}",
                "customer": {"name": f"Customer {n} ({self.tag})", "email": f"cust.{n}.{self.tag}@example.com",
                             "phone": "+233244000" + n[-1] * 3},
                "amount_ghs": 2500.0}


SCIM = {"authorization": f"Bearer {config.SCIM_TOKEN}"}
USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"
PATCH_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:PatchOp"


def scim_user(user: str) -> dict:
    u = config.USERS[user]
    first, last = u["name"].split(" ", 1)
    return {"schemas": [USER_SCHEMA], "userName": u["email"], "externalId": u["email"],
            "name": {"givenName": first, "familyName": last},
            "emails": [{"value": u["email"], "type": "work", "primary": True}], "active": True}


def scim_find(ctx: Ctx, email: str) -> dict | None:
    r = expect(ctx.http.get("/scim/v2/Users", params={"filter": f'userName eq "{email}"'}, headers=SCIM),
               range(200, 300), f"GET /scim/v2/Users?filter=userName eq \"{email}\"")
    found = r.json().get("Resources", [])
    return found[0] if found else None


def crm_deals_for(booking_id: str) -> list[dict]:
    with store.lock:
        return [d for d in store.deals.values() if d["properties"].get("booking_id") == booking_id]


def get_deal(ctx: Ctx, user: str, deal_id: str) -> httpx.Response:
    return ctx.http.get(f"/api/deals/{deal_id}", headers=ctx.as_user(user))


def poll(fn, seconds: float = 6.0, every: float = 0.3):
    deadline = time.monotonic() + seconds
    while True:
        value = fn()
        if value or time.monotonic() > deadline:
            return value
        time.sleep(every)


# ---------------- Preflight ----------------

@suite.check("preflight", "Setup", "Your app is reachable", 0,
             "Start your app on port 8000 (or change the app URL in the Console). From Docker, your machine is host.docker.internal.")
def preflight(ctx: Ctx):
    r = ctx.http.get("/", timeout=5)
    return f"{ctx.learner_url} answered {r.status_code}"


# ---------------- SCIM provisioning ----------------

@suite.check("scim.auth", "Provisioning (SCIM)", "SCIM rejects callers without the bearer token", 5,
             "Every /scim/v2 request must carry `Authorization: Bearer <SCIM_TOKEN>`. The IdP is the only caller you trust here.")
def scim_auth(ctx: Ctx):
    expect(ctx.http.post("/scim/v2/Users", json=scim_user("kofi")), DENIED, "SCIM POST with no token")
    expect(ctx.http.post("/scim/v2/Users", json=scim_user("kofi"), headers={"authorization": "Bearer nope"}),
           DENIED, "SCIM POST with a wrong token")
    return "401/403 for missing and wrong tokens"


@suite.check("scim.create", "Provisioning (SCIM)", "IdP can provision users (create, or find + reactivate)", 8,
             "POST /scim/v2/Users returns 201 with an `id`; a second POST for the same userName returns 409. "
             "GET ?filter=userName eq \"...\" returns a ListResponse. PATCH with an Okta-style op `{op: replace, value: {active: true}}` reactivates.")
def scim_create(ctx: Ctx):
    notes = []
    for user in ("kofi", "ama", "efua"):
        email = config.USERS[user]["email"]
        r = ctx.http.post("/scim/v2/Users", json=scim_user(user), headers=SCIM)
        if r.status_code == 201:
            if not r.json().get("id"):
                raise Fail(f"201 for {email} but no `id` in the response")
            notes.append(f"{user}: created")
        elif r.status_code == 409:
            found = scim_find(ctx, email)
            if not found:
                raise Fail(f"409 for {email}, but the filter query does not find the user")
            expect(ctx.http.patch(f"/scim/v2/Users/{found['id']}", headers=SCIM, json={
                "schemas": [PATCH_SCHEMA], "Operations": [{"op": "replace", "value": {"active": True}}]}),
                range(200, 300), f"PATCH active=true for {email}")
            notes.append(f"{user}: existed, reactivated")
        else:
            expect(r, {201, 409}, f"POST /scim/v2/Users for {email}")
        found = scim_find(ctx, email)
        if not found or found.get("userName", "").lower() != email:
            raise Fail(f"after provisioning, filter by userName does not return {email}")
        if found.get("active") is not True:
            raise Fail(f"{email} is provisioned but `active` is {found.get('active')!r}")
    return "; ".join(notes)


# ---------------- Identity (OIDC tokens) ----------------

@suite.check("oidc.valid", "Identity (OIDC)", "A valid token for a provisioned user is accepted", 8,
             "Validate the access token: signature via the realm's JWKS, `iss` = http://localhost:8081/realms/adom, `aud` contains `runmysales`, `exp`. "
             "GET /api/me returns the user's email.")
def oidc_valid(ctx: Ctx):
    ctx.needs("scim.create")
    r = expect(ctx.http.get("/api/me", headers=ctx.as_user("kofi")), {200}, "GET /api/me as kofi")
    if r.json().get("email", "").lower() != config.USERS["kofi"]["email"]:
        raise Fail(f"/api/me returned {r.json()!r}, expected kofi's email")
    return "200 with the right email"


@suite.check("oidc.no_token", "Identity (OIDC)", "No token, no access", 3, "Missing or malformed Authorization header -> 401.")
def oidc_no_token(ctx: Ctx):
    expect(ctx.http.get("/api/me"), {401}, "GET /api/me with no token")
    expect(ctx.http.get("/api/me", headers={"authorization": "Bearer not-a-jwt"}), {401}, "GET /api/me with garbage token")
    return "401"


@suite.check("oidc.wrong_aud", "Identity (OIDC)", "A token issued for another app is rejected", 6,
             "Same IdP, same user, valid signature, but `aud` is `other-app`. If you skip audience validation, any app in the company can call yours.")
def oidc_wrong_aud(ctx: Ctx):
    ctx.needs("oidc.valid")
    expect(ctx.http.get("/api/me", headers={"authorization": f"Bearer {ctx.token('kofi', 'other-app')}"}),
           {401}, "token for other-app")
    return "401"


@suite.check("oidc.tampered", "Identity (OIDC)", "A token with an edited payload is rejected", 6,
             "The checker changed `email` to efua's and kept the original signature. Decoding without verifying would let kofi become a manager.")
def oidc_tampered(ctx: Ctx):
    ctx.needs("oidc.valid")
    bad = tokens.tampered(ctx.token("kofi"), email=config.USERS["efua"]["email"], groups=["sales-managers"])
    expect(ctx.http.get("/api/me", headers={"authorization": f"Bearer {bad}"}), {401}, "tampered token")
    return "401"


@suite.check("oidc.forged", "Identity (OIDC)", "A token signed with an unknown key is rejected", 6,
             "Same claims and `kid`, signed with a key the IdP never published. Only trust keys from the JWKS URL, and never a key embedded in the token.")
def oidc_forged(ctx: Ctx):
    ctx.needs("oidc.valid")
    expect(ctx.http.get("/api/me", headers={"authorization": f"Bearer {tokens.forged(ctx.token('kofi'))}"}),
           {401}, "forged token")
    return "401"


@suite.check("oidc.alg_none", "Identity (OIDC)", "`alg: none` is rejected", 4,
             "Pin the accepted algorithms (RS256). Never let the token's header choose.")
def oidc_alg_none(ctx: Ctx):
    ctx.needs("oidc.valid")
    expect(ctx.http.get("/api/me", headers={"authorization": f"Bearer {tokens.alg_none(ctx.token('kofi'))}"}),
           {401}, "alg=none token")
    return "401"


@suite.check("oidc.unprovisioned", "Identity (OIDC)", "A valid IdP user who was never provisioned is denied", 5,
             "Yaw can log in to the IdP, but IT never assigned him your app. A valid token is not enough; the user must exist and be active in your app.")
def oidc_unprovisioned(ctx: Ctx):
    expect(ctx.http.get("/api/me", headers=ctx.as_user("yaw")), DENIED, "GET /api/me as unprovisioned yaw")
    return "denied"


@suite.check("rbac.roles", "Roles", "IdP groups map to app roles", 4,
             "Map the `groups` claim: sales-managers -> \"manager\", sales-reps -> \"rep\". /api/me returns `role`.")
def rbac_roles(ctx: Ctx):
    ctx.needs("oidc.valid")
    for user, want in (("kofi", "rep"), ("efua", "manager")):
        r = expect(ctx.http.get("/api/me", headers=ctx.as_user(user)), {200}, f"GET /api/me as {user}")
        if r.json().get("role") != want:
            raise Fail(f"{user}: role is {r.json().get('role')!r}, expected {want!r}")
    return "kofi=rep, efua=manager"


# ---------------- CRM sync ----------------

@suite.check("sync.create", "CRM sync", "A booking creates one contact and one deal in the CRM", 8,
             "POST /api/bookings -> create/reuse the CRM contact (unique by email; 409 tells you the existing id), then a deal with "
             "owner_email = the caller and properties.booking_id. Return crm_deal_id.")
def sync_create(ctx: Ctx):
    ctx.needs("oidc.valid")
    b = ctx.booking("b1")
    r = expect(ctx.http.post("/api/bookings", json=b, headers=ctx.as_user("ama")), range(200, 300), "POST /api/bookings as ama")
    deal_id = r.json().get("crm_deal_id")
    deals = crm_deals_for(b["booking_id"])
    if len(deals) != 1:
        raise Fail(f"CRM has {len(deals)} deals with booking_id={b['booking_id']}, expected 1")
    d = deals[0]
    if deal_id != d["id"]:
        raise Fail(f"you returned crm_deal_id={deal_id!r}, but the CRM deal is {d['id']}")
    if d["owner_email"] != config.USERS["ama"]["email"]:
        raise Fail(f"deal owner_email is {d['owner_email']!r}, expected ama (the caller)")
    contact = store.contacts.get(d["contact_id"])
    if not contact or contact["email"] != b["customer"]["email"]:
        raise Fail("the deal is not linked to a contact with the customer's email")
    ctx.deal_b1 = deal_id
    return f"deal {deal_id}"


@suite.check("sync.idempotent", "CRM sync", "Re-sending the same booking does not duplicate it", 6,
             "Clients retry. The same booking_id twice more must return the same crm_deal_id and leave exactly one deal.")
def sync_idempotent(ctx: Ctx):
    ctx.needs("sync.create")
    b = ctx.booking("b1")
    for i in range(2):
        r = expect(ctx.http.post("/api/bookings", json=b, headers=ctx.as_user("ama")), range(200, 300), f"retry {i + 1}")
        if r.json().get("crm_deal_id") != ctx.deal_b1:
            raise Fail(f"retry {i + 1} returned {r.json().get('crm_deal_id')!r}, first call returned {ctx.deal_b1}")
    n = len(crm_deals_for(b["booking_id"]))
    if n != 1:
        raise Fail(f"{n} deals in the CRM after retries")
    return "same deal, one row"


@suite.check("sync.concurrent", "CRM sync", "Three simultaneous copies of a booking create one deal", 5,
             "Double-taps and retries arrive at the same time. Check-then-create races; you need a lock or a unique constraint on booking_id in YOUR database.")
def sync_concurrent(ctx: Ctx):
    ctx.needs("sync.create")
    b = ctx.booking("b2")
    headers = ctx.as_user("ama")
    with ThreadPoolExecutor(3) as pool:
        resps = list(pool.map(lambda _: ctx.http.post("/api/bookings", json=b, headers=headers), range(3)))
    codes = [r.status_code for r in resps]
    if not any(200 <= c < 300 for c in codes):
        raise Fail(f"no copy succeeded: {codes}")
    time.sleep(1)  # let any stragglers land
    n = len(crm_deals_for(b["booking_id"]))
    if n != 1:
        raise Fail(f"{n} deals in the CRM for one booking (responses: {codes})")
    ids = {r.json().get("crm_deal_id") for r in resps if 200 <= r.status_code < 300}
    if len(ids) != 1:
        raise Fail(f"successful responses returned different deal ids: {ids}")
    return f"one deal; responses {codes}"


@suite.check("sync.rate_limit", "CRM sync", "429 + Retry-After is respected, and the booking still lands", 8,
             "The CRM will answer 429 with `Retry-After: 2` twice. Wait at least that long before retrying (no hammering), and don't give up.")
def sync_rate_limit(ctx: Ctx):
    ctx.needs("sync.create")
    b = ctx.booking("b3")
    with store.lock:
        start = len(store.requests)
        store.chaos.update(force_429=2, retry_after=2)
    try:
        r = ctx.http.post("/api/bookings", json=b, headers=ctx.as_user("ama"), timeout=40)
    finally:
        with store.lock:
            store.chaos["force_429"] = 0
            log = list(store.requests)[start:]
    expect(r, range(200, 300), "POST /api/bookings while the CRM is rate limiting")
    if len(crm_deals_for(b["booking_id"])) != 1:
        raise Fail("booking reported success but the CRM does not have exactly one deal for it")
    throttled = [e for e in log if e["status"] == 429 and e.get("retry_after") == "2"]
    if len(throttled) < 2:
        raise Fail("the CRM did not see your retries (expected 2 throttled requests)")
    for e in throttled:
        nxt = next((x for x in log if x["t"] > e["t"]), None)
        if nxt and nxt["t"] - e["t"] < 1.8:
            raise Fail(f"retried after {nxt['t'] - e['t']:.2f}s; Retry-After said 2s")
    return f"{len(log)} CRM calls, waited as told"


# ---------------- Data permissions ----------------

@suite.check("rbac.rep_isolation", "Roles", "A rep cannot read another rep's deal", 6,
             "Enforce row-level permissions in your query, not in the UI: reps see deals where owner_email = their email.")
def rbac_rep_isolation(ctx: Ctx):
    ctx.needs("sync.create", "rbac.roles")
    r = expect(get_deal(ctx, "ama", ctx.deal_b1), {200}, "ama reading her own deal")
    if r.json().get("owner_email") != config.USERS["ama"]["email"]:
        raise Fail(f"owner_email is {r.json().get('owner_email')!r}")
    expect(get_deal(ctx, "kofi", ctx.deal_b1), DENIED_OR_HIDDEN, "kofi reading ama's deal")
    return "owner 200, other rep denied"


@suite.check("rbac.manager", "Roles", "A manager can read every deal", 4, "sales-managers see all deals.")
def rbac_manager(ctx: Ctx):
    ctx.needs("sync.create", "rbac.roles")
    expect(get_deal(ctx, "efua", ctx.deal_b1), {200}, "efua (manager) reading ama's deal")
    return "200"


# ---------------- Webhooks ----------------

@suite.check("hook.stage", "Webhooks", "A CRM stage change reaches your app", 8,
             "Verify `X-CRM-Signature: t=<unix>,v1=<hex>` = HMAC-SHA256(secret, f\"{t}.\" + RAW body). Use the raw bytes; re-serialised JSON won't match. "
             "Ack with 2xx, then update the deal; GET /api/deals/{id} shows the new stage.")
def hook_stage(ctx: Ctx):
    ctx.needs("sync.create")
    evt = user_change_stage(ctx.deal_b1, "contract_sent")
    status = deliver(evt, label="checker: stage change")
    if status is None or not 200 <= status < 300:
        raise Fail(f"webhook delivery got {status}")
    got = poll(lambda: get_deal(ctx, "ama", ctx.deal_b1).json().get("stage") == "contract_sent")
    if not got:
        raise Fail("webhook was acked, but GET /api/deals/{id} never showed stage=contract_sent")
    return "acked and applied"


@suite.check("hook.dedupe", "Webhooks", "The same event delivered 3 times is applied once", 6,
             "CRMs deliver at-least-once. Store processed event ids. Answer duplicates with 2xx too, or the CRM keeps retrying.")
def hook_dedupe(ctx: Ctx):
    ctx.needs("hook.stage")
    evt = user_add_note(ctx.deal_b1, f"Customer asked for MoMo payment terms ({ctx.tag})")
    codes = [deliver(evt, label=f"checker: duplicate {i + 1}/3") for i in range(3)]
    if not all(c is not None and 200 <= c < 300 for c in codes):
        raise Fail(f"deliveries got {codes}; duplicates must still be acked with 2xx")
    note_id = evt["data"]["note_id"]

    def count():
        return sum(n.get("note_id") == note_id for n in get_deal(ctx, "ama", ctx.deal_b1).json().get("notes", []))
    if not poll(count):
        raise Fail("note never appeared on GET /api/deals/{id}")
    time.sleep(1.5)
    if (n := count()) != 1:
        raise Fail(f"note applied {n} times")
    return "applied once"


@suite.check("hook.bad_signature", "Webhooks", "A webhook with a bad signature is rejected", 5,
             "Anyone can POST to your webhook URL. Reject (401) unless the HMAC matches, using a constant-time compare.")
def hook_bad_signature(ctx: Ctx):
    ctx.needs("hook.stage")
    evt = make_event("deal.note_added", {"deal_id": ctx.deal_b1, "note_id": f"nt_forged_{ctx.tag}", "text": "Approve 90% discount"})
    status = deliver(evt, bad_signature=True, label="checker: bad signature")
    if status not in (400, 401, 403):
        raise Fail(f"forged webhook got {status}, expected 401")
    time.sleep(1)
    if any(n.get("note_id") == f"nt_forged_{ctx.tag}" for n in get_deal(ctx, "ama", ctx.deal_b1).json().get("notes", [])):
        raise Fail("rejected, but the forged note was applied anyway")
    return f"{status}"


@suite.check("hook.replay", "Webhooks", "A correctly signed but 10-minute-old webhook is rejected", 5,
             "Signatures include a timestamp so captured requests can't be replayed later. Reject if |now - t| > 5 minutes.")
def hook_replay(ctx: Ctx):
    ctx.needs("hook.stage")
    evt = make_event("deal.stage_changed", {"deal_id": ctx.deal_b1, "stage": "lost"})
    status = deliver(evt, ts=int(time.time()) - 600, label="checker: replay")
    if status not in (400, 401, 403):
        raise Fail(f"replayed webhook got {status}, expected 401")
    time.sleep(1)
    if get_deal(ctx, "ama", ctx.deal_b1).json().get("stage") == "lost":
        raise Fail("rejected, but the replayed stage change was applied")
    return f"{status}"


# ---------------- Deprovisioning (last: it locks kofi out until the next run) ----------------

@suite.check("scim.deactivate", "Provisioning (SCIM)", "Deprovisioning kills existing sessions immediately", 8,
             "This PATCH is Entra-style: `{op: \"Replace\", path: \"active\", value: \"False\"}` (capital R, string). "
             "Then kofi's still-unexpired token must stop working. Check the user is active on every request, not only at login.")
def scim_deactivate(ctx: Ctx):
    ctx.needs("scim.create", "oidc.valid")
    kofi = config.USERS["kofi"]["email"]
    expect(ctx.http.get("/api/me", headers=ctx.as_user("kofi")), {200}, "kofi before deactivation")
    found = scim_find(ctx, kofi)
    if not found:
        raise Fail("kofi not found via SCIM filter")
    expect(ctx.http.patch(f"/scim/v2/Users/{found['id']}", headers=SCIM, json={
        "schemas": [PATCH_SCHEMA], "Operations": [{"op": "Replace", "path": "active", "value": "False"}]}),
        range(200, 300), "Entra-style PATCH active=False")
    expect(ctx.http.get("/api/me", headers=ctx.as_user("kofi")), DENIED, "kofi's existing token after deactivation")
    return "token rejected right after deprovisioning"


def run() -> dict:
    ctx = Ctx()
    try:
        return suite.run(ctx)
    finally:
        ctx.http.close()
