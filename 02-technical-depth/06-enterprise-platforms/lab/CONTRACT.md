# The contract: Volta's platforms and your agent's tool layer

You build a small service on `http://localhost:8000` (any language): the **tool layer** an LLM agent calls. The Console plays Volta's ServiceNow and SAP, and its checker plays the model: it makes the tool calls an agent would make, then looks *inside* both systems to see what really happened. Your agent's prompt and judgement are yours to eval; this grades the plumbing underneath.

Start the Console (`docker compose up --build` in `console/`), then open **Customer: Volta Industrial → ServiceNow & SAP**. It shows the data, every call you make, and switches for bad days.

## The two systems

**ServiceNow (Table API)**
- Base `http://localhost:8090/servicenow`, Basic auth `svc_agent` / `SnowPass!23`
- Tables you may use: `incident`, `sys_user`. Paths: `/api/now/table/incident`, `/api/now/table/incident/{sys_id}`, `/api/now/table/sys_user`
- Things that will surprise you, because they surprise everyone:
  - Every value is a **string**, including `urgency: "1"` and `state: "2"`. States are codes (`1` New, `2` In Progress, `3` On Hold, `6` Resolved, `7` Closed, `8` Canceled)
  - Reference fields (`caller_id`) are `{"link": ..., "value": "<sys_id>"}` objects. `sysparm_display_value=true` gives the label instead
  - `caller_id` on create must be a user's `sys_id` (or `user_name`): look people up by email in `sys_user`
  - Queries: `sysparm_query=caller_id=<sys_id>^stateIN1,2,3^ORDERBYDESCnumber`, plus `sysparm_fields`, `sysparm_limit`, `sysparm_offset`
  - A page is capped at **50 rows**. `X-Total-Count` tells you the total, and the `Link` header has `rel="next"`
  - `comments` and `work_notes` are write-only: they read back as empty strings
  - `correlation_id` is a real field: it is how you make an integration idempotent, because ServiceNow won't
  - Closed incidents are read-only (403). Resolving needs `close_code` and `close_notes` (a business rule answers 403)
  - Errors look like `{"error": {"message", "detail"}, "status": "failure"}`
  - Bad days: **429** with `Retry-After`; a hibernating instance answers **503 with an HTML page**

**SAP S/4HANA (OData v2)**
- Base `http://localhost:8090/sap/opu/odata/sap/API_SALES_ORDER_SRV`, Basic auth `AGENT01` / `SapPass!23`, client `100`
- Entity sets: `A_SalesOrder` (with `to_Item`), `A_BusinessPartner`; `$metadata` lists the fields
- Things that will surprise you:
  - Without `Accept: application/json` you get **Atom XML**
  - Keys are zero-padded: `A_SalesOrder('0000012345')`. `'12345'` is a 404
  - Dates are `/Date(1789344000000)/`; amounts are strings (`"12450.00"`); status fields are letters (`A` not yet, `B` partly, `C` completely)
  - `$filter` on a date needs `datetime'2026-10-01T00:00:00'`
  - Collections page at 50 with `d.__next` (a `$skiptoken` URL). `$inlinecount=allpages` adds `d.__count`
  - **Writes** need an `x-csrf-token`: do a GET with header `x-csrf-token: Fetch`, keep the **session cookie** it sets, send the returned token on the PATCH, plus `If-Match: <the ETag>`. Without them: 403 or 428
  - The only writable property is `DeliveryBlockReason` (`"01"` = credit hold). A fully delivered order can't take a block (400)
  - Errors look like `{"error": {"code", "message": {"lang", "value"}}}`
  - Bad days: slow answers, an order **locked** by another user (400 naming the user), and an ETag that moved because someone else changed the order (412)

## Your service

`GET /health` returns 200. Everything else is JSON. Errors are `{"error": "<readable message>"}`; never a stack trace and never a 500 for something the contract covers.

| Tool | Request | Success |
|---|---|---|
| `POST /api/tools/create_incident` | `{request_id, caller_email, short_description, description?, urgency (1-3), category?}` | `{number, sys_id, state, priority, created}`. `state` is the label (`"New"`); `created` is false when this `request_id` was already handled |
| `POST /api/tools/add_comment` | `{request_id, number, comment}` | `{number, applied}`. `applied` is false for a `request_id` you already applied |
| `GET /api/tools/my_incidents?caller_email=&open=` | `open=true` means New, In Progress, On Hold | `{count, incidents: [{number, short_description, state}]}`: **all** of them, `state` as a label |
| `GET /api/tools/order_status?order=` | `12345`, `SO 12345` and `0000012345` are the same order | `{order, customer_name, total_amount (number), currency, order_date ("2026-09-14"), status, delivery_status, blocked (bool), items: [{item, material, quantity, net_amount}]}`. Status words: `not yet processed`, `partially processed`, `completely processed` |
| `GET /api/tools/orders_summary?since=2026-10-01` | all orders dated on or after `since` | `{count, total_amount}`, exact to the pesewa |
| `POST /api/tools/hold_order` | `{request_id, order, reason, approved_by?}` | `{order, blocked: true}` |

**Error behaviour the checks look for**

| Situation | Respond |
|---|---|
| unknown caller or order | 404 |
| invalid input (urgency 7, empty summary, a reason shorter than 10 characters, text that isn't an order number) | 422 (400 for the order-number case is fine) |
| comment on a closed incident; hold on a delivered order | 409 |
| hold on an order with `total_amount` over **GHS 50,000** and no `approved_by` ending in `@volta.example` | 403 with `{error, needs_approval: true}` |
| ServiceNow or SAP down after your retries (give up within ~30 s) | 503 (or 502/504) |
| order locked in SAP | 423 (or 409/503) with `{error, retry: true}` |

## What gets checked

28 checks, in ServiceNow, SAP and hygiene sections: a correct incident, a messy email, idempotency (sequential and 8-way parallel), validation, comments (once, and never on closed incidents), paging all 123 of a caller's incidents, the `open` filter, states as labels, riding out 429s (honouring `Retry-After`) and a hibernating instance, a clean failure in an outage; SAP field types, key padding, 404s, paged date-filtered totals, JSON-only calls, a hold with CSRF and ETag, idempotent holds, delivered orders, the GHS 50,000 rule, locks, a changed ETag, a slow system, and credentials only in headers.

## What this world does not test

- **Your agent**: the prompt, the model choice, whether it picks the right tool or refuses the wrong request. Write a 20-case eval for that. The checker never lets a model make these calls.
- **Salesforce**: it needs a real org, see [SALESFORCE.md](SALESFORCE.md).
- **Real access**: Volta's Basis team, change boards and security reviews. The stakeholder calls (Akua Danso, Ebenezer Boadu, Adwoa Pokuaa) are where to practise that.
- **Quality of your report** and whether Volta's IT lead would sign off your role list.

## Practical notes
- Each run resets Volta's data to the seed. A run takes about a minute and a half.
- Runs are saved to [`runs/`](runs/). Commit them.
- Keep the ServiceNow and SAP credentials in configuration, not in code, and never in a URL: a check looks.
