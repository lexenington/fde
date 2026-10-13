# Kata 14: OData v2, the way SAP wants it

**Time-box: 45 minutes.** Used in: 02/06 (the SAP half of the lab: order status, order summaries, holds), any S/4HANA or SuccessFactors integration.

**The task.** Implement `build_query`, `parse_sap_date`, `pad_key` and `all_results` in `odata_query.py`. `python -m pytest -q katas/14-odata-query`.

**What bites people, and what the tests encode**
- a date in a `$filter` must be `datetime'2026-10-01T00:00:00'`. `'2026-10-01'` is an error and a bare `2026-10-01` is a different error
- strings are single-quoted and a quote inside is doubled. Field names go into the URL unquoted, so they must be checked: that is where OData injection lives
- v2 has no `contains()`: it is `substringof('x',Field)`, with the arguments the other way round from what you expect
- `/Date(ms)/` is milliseconds since 1970 in UTC, even when SAP appends an offset. Do not "apply" it
- keys are zero-padded, and people type `SO 12345`
- a server-driven page ends when `__next` is missing, not when a page is short. A server that repeats itself is a bug you should survive

**Then.** Point your functions at the Console's SAP (*ServiceNow & SAP* page has the URL and credentials) and fetch every order since 1 January. How many pages was that? What would happen if you had stopped at the first?
