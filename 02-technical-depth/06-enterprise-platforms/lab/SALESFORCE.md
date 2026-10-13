# Salesforce: your own org

The Console doesn't simulate Salesforce: it's free to get the real thing, and its quirks (limits, licences, field-level security) don't fake well. Sign up for a **Developer Edition** org (developer.salesforce.com/signup; check the current terms), then build and check the following yourself. Commit your evidence in this folder (`SALESFORCE-EVIDENCE.md`: commands, responses, screenshots).

## Build
1. **Authenticate server-to-server.** A connected app (or external client app, whichever your org offers) with the **JWT bearer flow**, using a certificate. Not the username-password flow, and not your own login. Note which scopes you gave it, and why.
2. **A least-privilege integration user** with its own permission set: read/write on Account and Case only. Write down the exact list for REPORT.md.
3. **Upsert accounts by external ID.** Add a custom field `SAP_BP__c` (text, external ID, unique) on Account. `PATCH /services/data/vNN.0/sobjects/Account/SAP_BP__c/0010000042` creates or updates in one idempotent call. Sync Volta's eight business partners from the Console's SAP.
4. **Create a Case from a ServiceNow incident** using your kata 15 mapping, with `ExternalId__c` (add it) set to the incident number, via upsert so a retry can't duplicate it.
5. **Read with SOQL and follow the pages.** `SELECT Id, Subject, Status FROM Case WHERE ExternalId__c != null`. A query returns up to 2,000 records per batch with `done` and `nextRecordsUrl`: follow it.
6. **Handle the errors**: a Salesforce error is a *list* (`[{"message", "errorCode", "fields"}]`). Deal with `REQUEST_LIMIT_EXCEEDED`, `UNABLE_TO_LOCK_ROW` (retry with backoff), `INVALID_FIELD` and `FIELD_CUSTOM_VALIDATION_EXCEPTION`.

## Self-check (all must be true, with evidence)
- [ ] Running your sync twice creates no duplicate Accounts or Cases
- [ ] The integration user cannot read a Contact, delete an Account or open Setup (try each, keep the error)
- [ ] You can state your org's daily API request limit and how many calls your sync used (Setup → System Overview, or the `Sforce-Limit-Info` response header)
- [ ] A sync of 200 accounts uses fewer than 20 API calls (hint: the Composite or sObject Collections endpoints, or Bulk API 2.0 for larger loads, not one call per record)
- [ ] A field the integration user can't see is handled: reads come back *without* the field, with no error
- [ ] Credentials and the private key are not in the repository
