# 02/02 — Enterprise integration

**Prove it (skip if yes):** Without looking anything up, can you (a) explain the SAML and OIDC login flows on a whiteboard, including what the IdP signs and what you validate, (b) explain what SCIM is for and what happens when someone leaves the company, and (c) design a webhook consumer that never double-processes an event and never loses one?

## Why this matters for FDEs

The first blocker at most enterprise customers isn't the model or the feature. It's **"we can't let it touch production until it uses our SSO, respects our permissions, and passes the security review."** An FDE who can say "send me your Okta metadata, I'll have SSO working by Thursday, and here's our answer to question 47 of your security questionnaire" saves weeks.

## Concepts to learn

### Identity
| Topic | Must know |
|---|---|
| **OIDC / OAuth 2.0** | Authorization code + PKCE, ID token vs access token, `iss`/`aud`/`exp`/`nonce` validation, JWKS key rotation, client-credentials for service-to-service |
| **SAML 2.0** | SP vs IdP initiated, assertions, signature + certificate validation, metadata XML, clock skew. You'll mostly *integrate* it via a library (python3-saml) or a broker (WorkOS, Auth0) rather than implement it |
| **SCIM 2.0** | `/Users` and `/Groups` endpoints, how Okta/Entra push create/update/deactivate, why deprovisioning is the part customers actually audit |
| **RBAC / ABAC** | Mapping IdP groups → app roles; row-level permissions ("agents see only their region's tickets") |
| **Service accounts** | Least privilege, key rotation, workload identity vs long-lived keys |

### Systems you'll meet at customers
Salesforce (SOQL, Bulk API, governor limits), ServiceNow, Zendesk/Intercom, HubSpot, SAP (OData; you'll go through middleware), Microsoft Graph (Teams/SharePoint/Outlook), Slack, Snowflake/BigQuery/Databricks, SFTP drops (yes, still), and in Africa specifically: Mobile Money APIs (MTN MoMo, Paystack, Flutterwave), USSD gateways, and WhatsApp Business API.

### Reliability patterns (non-negotiable)
| Pattern | One-line |
|---|---|
| Idempotency keys | Same request twice → same effect once. Store key + result |
| Webhook signature verification | HMAC over raw body, constant-time compare, timestamp tolerance to stop replays |
| Outbox pattern | Write the DB change and the "event to send" in one transaction, ship asynchronously |
| Retries with backoff + jitter | And know which errors *not* to retry (4xx except 408/429) |
| Dead-letter queue | Where poison messages go, with an owner and a replay tool |
| Rate-limit handling | Respect `Retry-After`, token bucket client-side, bulk APIs for backfills |
| Reconciliation job | Webhooks *will* be missed; a nightly diff against source of truth catches it |

### Security & compliance vocabulary
SOC 2 Type II, ISO 27001, GDPR / Ghana Data Protection Act 2012, DPA, data residency, encryption at rest/in transit, customer-managed keys, audit logs, pen-test reports, the CAIQ/SIG questionnaires. For AI features, add: what data is sent to the model provider and whether it's retained or used for training, zero-data-retention options, and the AI governance frameworks (NIST AI RMF, ISO/IEC 42001, EU AI Act) covered in 02/03. You don't need to be a security engineer. You need to answer these questions without panicking and know when to bring one in.

## Lab: "Enterprise-ready" RunMySales

Take your own RunMySales (or a minimal clone) and make it something a 2,000-person company's IT team would approve.

**The customer is simulated for you.** `cd console && docker compose up --build`, then open http://localhost:3300. It plays Adom Logistics (2,000 staff): their identity provider (Keycloak, standing in for Okta/Entra), their SCIM provisioning and their CRM (rate limits, flaky signed webhooks). It also scores your app with 22 checks. Read [`lab/CONTRACT.md`](lab/CONTRACT.md) first; it's the integration spec their IT team sent you. You no longer need an Okta tenant or a HubSpot account to start. Doing deliverable 1 against a real Okta or Entra dev tenant afterwards is still worth it, because it's what you'll meet at customers.

### Deliverables
1. **OIDC SSO** against a free Okta developer tenant *or* Microsoft Entra ID dev tenant. Validate tokens properly (issuer, audience, signature via JWKS, expiry, nonce). Write a test that a token for the wrong audience is rejected.
2. **SCIM endpoint** (`/scim/v2/Users`, `/scim/v2/Groups`). Connect it to the Okta/Entra SCIM provisioning app. Demonstrate: assign a user in Okta → user appears; unassign → user deactivated *and their sessions revoked*.
3. **Group → role mapping**: Okta group `sales-managers` sees all conversations; `sales-reps` see only their own.
4. **CRM sync** to a free HubSpot developer account (or Salesforce Developer Edition):
   - Booked appointments create/update a CRM contact + deal, **idempotently** (run the sync twice: no duplicates).
   - Receive CRM webhooks with **signature verification** and **replay protection**.
   - Process webhooks through a queue (you know BullMQ; or use RQ/Celery to practise Python) with retries + a DLQ.
   - A **nightly reconciliation** job that diffs your DB vs the CRM and reports drift.
5. **Audit log**: every admin action and every data export recorded (who, what, when, from where).
6. **`SECURITY.md`**: answer these 15 questionnaire items for your app as if a customer asked: data flow diagram; where data is stored and in which region; encryption at rest/in transit; subprocessors (Anthropic, hosting); retention & deletion; access control; SSO/MFA; logging; incident response; backup/restore; vulnerability management; pen testing; employee access; LLM-specific: is customer data used for training, prompt-injection mitigations, PII handling.

### Acceptance tests to write (pytest)
The Console's checker covers these from the outside. Write them anyway, as your own tests: the checker tells you *that* something broke, and your tests tell you *where*.

- Replayed webhook (same signature, old timestamp) → 401
- Same webhook delivered 3× → processed once
- CRM returns 429 with `Retry-After: 2` → client waits and succeeds
- SCIM `PATCH active=false` → user can no longer call the API with an existing session
- Token with `aud` of another app → 401

### Reflection (write in `REFLECTION.md`)
Which of these took longest? That's the one customers will ask you about. Write the 3-sentence explanation you'd give their IT lead.
