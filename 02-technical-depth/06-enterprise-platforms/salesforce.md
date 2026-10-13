# Salesforce in one page (for the engineer who has to plug an agent into it)

## The model
Salesforce is a database with a permission system and a UI around it. **Objects** are tables (`Account`, `Contact`, `Lead`, `Opportunity`, `Case`; yours end in `__c`), **fields** are columns (custom ones also end in `__c`), **records** have a 15- or 18-character Id (use the 18; it is case-safe). Relationships are lookups and master-detail. An **Account** is a company, a **Contact** a person at it, an **Opportunity** a deal, a **Case** a customer problem. Customers have always bent these: ask for a field list of the objects you touch, with the admin, on day one.

## The integration surface
- **REST API:** `/services/data/vNN.0/sobjects/Case`, JSON, returns `instance_url` from login. Pin the API version.
- **SOQL:** SQL-like, no joins (relationship queries instead: `SELECT Name, Account.Name FROM Contact`), no `SELECT *`. A query returns up to 2,000 records per batch; follow `nextRecordsUrl` until `done` is true.
- **Upsert by external ID:** `PATCH /sobjects/Account/SAP_BP__c/0010000042`. The single most useful call for an integration: idempotent create-or-update, keyed on the other system's id.
- **Volume:** sObject Collections (up to 200 records a call), Composite (a few dependent calls in one), Bulk API 2.0 (large loads, asynchronous). One call per record is how you hit the daily limit.
- **Listening:** Platform Events, Change Data Capture and the Streaming API (CometD) push changes to you. Polling is the poor man's version.
- **Auth:** OAuth 2.0. For a server with no user, the **JWT bearer flow** with a certificate on a connected app. Avoid username-password.

## How it fails
- **Limits.** A total of API requests per rolling 24 hours for the whole org, shared by every integration; `REQUEST_LIMIT_EXCEEDED` when you run out. The `Sforce-Limit-Info` response header tells you where you stand. Inside Apex there are per-transaction governor limits (queries, DML rows, CPU) that explain why admins say no to "just a trigger".
- **Locks.** `UNABLE_TO_LOCK_ROW` when two writers hit the same parent. Retry with backoff.
- **Silent field hiding.** *Field-level security* means the integration user may simply not see a field. The response comes back without it, no error.
- **Validation rules** and **flows** run on your writes and can reject them with `FIELD_CUSTOM_VALIDATION_EXCEPTION`. The rules were written for humans.
- Errors come back as a **list**: `[{"message": ..., "errorCode": ..., "fields": [...]}]`.

## Who holds the keys
The **Salesforce admin** (here: Sales Operations). They decide the integration licence, the permission set, the sandbox you may use and the release calendar. Ask for: a dedicated integration user, a permission set listing exactly the objects and fields, a full or developer sandbox, and the daily API budget you may spend.

## Questions to ask in week one
- Which objects and custom fields do we touch, and who owns each? What is the external id that links to the other systems?
- How many API calls does everything else use per day? How many may I use?
- Which validation rules, flows and duplicate rules fire on Accounts and Cases?
- Sandbox: how often is it refreshed, and what data is in it?
