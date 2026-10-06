# Lab contract: what Adom Logistics' systems expect from your app

You build this in **your own app** (RunMySales, or a minimal clone), in any language. The [FDE Console](../../../console/README.md) plays Adom's IdP, provisioning and CRM, drives your app through them, and scores it. Treat this page as the integration spec their IT team handed you. It says *what* must happen, never *how*.

Your app runs on your machine at `http://localhost:8000` (configurable in the Console).

## What Adom's IT sent you

| Thing | Value |
|---|---|
| OIDC issuer | `http://localhost:8081/realms/adom` (discovery at `/.well-known/openid-configuration`) |
| Your client id / audience | `runmysales` |
| SCIM bearer token (the IdP sends it to you) | `scim-dev-token` |
| CRM API | `http://localhost:8090/crm/v3`, header `Authorization: Bearer crm-dev-key` |
| CRM webhook secret | `whsec_dev_adom` |
| Test users (password `Passw0rd!`) | kofi.mensah@, ama.owusu@ (group `sales-reps`), efua.asante@ (`sales-managers`), yaw.boateng@ (never assigned your app); all `@adom.example` |

Keep them in config, not code. Part of the exercise is noticing which ones are secrets.

## 1. SCIM 2.0 provisioning: `/scim/v2/Users`

All requests carry `Authorization: Bearer <SCIM token>`. Anything else gets 401.

| Call | Must do |
|---|---|
| `POST /scim/v2/Users` | Create the user (`userName` is their email). `201` with the user resource including your `id`. Same `userName` again → `409` |
| `GET /scim/v2/Users?filter=userName eq "x@adom.example"` | `200` ListResponse: `{"schemas": [...ListResponse], "totalResults": n, "Resources": [...]}`. Each resource has `id`, `userName`, `active` |
| `PATCH /scim/v2/Users/{id}` | PatchOp that sets `active`. You will receive **both** dialects: Okta's `{"op": "replace", "value": {"active": true}}` and Entra's `{"op": "Replace", "path": "active", "value": "False"}` |

A deactivated user's **existing, unexpired tokens** must stop working straight away.

## 2. Your API: OIDC bearer tokens

Every `/api/*` call carries `Authorization: Bearer <access token from Adom's IdP>`.

- Invalid, missing, forged, tampered, wrong-audience or `alg: none` token → `401`.
- Valid token, but the user isn't provisioned or isn't active → `401` or `403`.
- Link a token to a provisioned user by the `email` claim. (Real IdPs give you a stable subject id too. In `REFLECTION.md`, say why matching on email is risky and what you'd do instead.)
- Roles come from the token's `groups` claim: `sales-managers` → `manager`, `sales-reps` → `rep`.

| Endpoint | Behaviour |
|---|---|
| `GET /api/me` | `200 {"email": "...", "role": "rep" or "manager"}` |
| `POST /api/bookings` | Body below. Create (or reuse) the customer as a CRM **contact**, and create one CRM **deal** with `owner_email` = the caller's email and `properties.booking_id`. Return `2xx {"crm_deal_id": "...", "crm_contact_id": "..."}`. The same `booking_id` sent again, even at the same moment, returns the same deal and creates nothing new |
| `GET /api/deals/{crm_deal_id}` | `200 {"crm_deal_id", "stage", "owner_email", "notes": [{"note_id", "text"}]}`, reflecting webhooks. Reps only see deals they own (`403` or `404` otherwise); managers see all |

```json
POST /api/bookings
{"booking_id": "bk_123", "customer": {"name": "Abena Darko", "email": "abena@example.com", "phone": "+233244000111"}, "amount_ghs": 2500.0}
```

## 3. The CRM API you call (`/crm/v3`)

| Call | Notes |
|---|---|
| `POST /contacts` `{email, name, phone}` | `201`. Email is unique: a duplicate gets `409` with `{"detail": {"existing_id": "..."}}` |
| `GET /contacts?email=` | Search |
| `POST /deals` `{contact_id, name, amount_ghs, owner_email, stage?, properties: {booking_id}}` | `201`. **Not** deduplicated. Call it twice, get two deals |
| `GET /deals?booking_id=&contact_id=`, `GET /deals/{id}`, `PATCH /deals/{id}` | Search, read, update |

Limits: 5 requests/second, burst 10. Over that, `429` with `Retry-After` (seconds). The CRM also has bad days. See its API docs at `http://localhost:8090/docs`.

## 4. Webhooks the CRM sends you: `POST /webhooks/crm`

When someone at Adom changes a deal in the CRM, it POSTs an event to you:

```json
{"id": "evt_...", "type": "deal.stage_changed", "occurred_at": "2026-10-06T10:00:00+00:00", "data": {"deal_id": "dl_...", "stage": "contract_sent"}}
{"id": "evt_...", "type": "deal.note_added",    "occurred_at": "...", "data": {"deal_id": "dl_...", "note_id": "nt_...", "text": "..."}}
```

Header: `X-CRM-Signature: t=<unix seconds>,v1=<hex HMAC-SHA256 of "<t>." + raw request body, keyed with the webhook secret>`.

- Reject a bad signature, or a timestamp more than 5 minutes from now, with `401`.
- Delivery is **at least once**: the same event can arrive several times. Apply it once, and still answer `2xx`.
- Any non-2xx answer makes the CRM retry with backoff.

## How you're scored

Open the Console → **02 Enterprise integration** → **Run checker**, or run `docker compose exec sim python -m sim.checks integration` from `console/`. Each run is saved to `lab/runs/`. Commit it: the history of scores is evidence.

The checker can't see everything. Still do these yourself:
- write your own pytest acceptance tests (README, "Acceptance tests to write")
- the browser login flow (authorization code + PKCE)
- the audit log, the nightly reconciliation job, `SECURITY.md` and `REFLECTION.md`
