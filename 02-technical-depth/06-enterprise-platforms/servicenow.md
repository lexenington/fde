# ServiceNow in one page (for the engineer who has to plug an agent into it)

## The model
ServiceNow is a platform of **tables**, each with fields, ACLs (who may do what) and **business rules** (scripts that run when records change). Every record has a `sys_id` (32 hex characters). The ITSM tables you will meet: `incident` (something is broken), `sc_request` / `sc_req_item` (somebody wants something), `change_request` (a planned change, the thing the change board approves), `problem`, `sys_user`, `sys_user_group`, and the CMDB (`cmdb_ci`, the inventory of what the company runs). Tickets extend a base table, `task`, which is why they share fields such as `number`, `state`, `assigned_to`, `correlation_id`.

## The integration surface
- **Table API:** `/api/now/table/{table}` with `GET`, `POST`, `PATCH`, `DELETE`. This is the one an agent uses.
- **Query language:** `sysparm_query=caller_id=<sys_id>^stateIN1,2,3^ORDERBYDESCsys_created_on`, with `sysparm_fields`, `sysparm_limit`, `sysparm_offset` and `sysparm_display_value=true`. Learn the operators (`=`, `!=`, `LIKE`, `STARTSWITH`, `IN`, `>`, `<`).
- **Scripted REST APIs and Flow Designer / IntegrationHub:** what the customer's own developers use when the Table API is too raw. If they offer you a scripted endpoint, take it: it is a contract they maintain.
- **MID Server:** a small agent the customer installs inside their network so the cloud instance can reach on-prem systems. If you hear "we'll need a MID Server", the integration is crossing the firewall, and there is a team and a change request attached.
- **Auth:** Basic (a service user) or OAuth. The service user's **roles** are everything: `itil` lets it work incidents; without it, writes 403.

## How it fails (and how it looks)
- **Everything is a string.** `"2"`, not 2. References are objects: `{"link": ..., "value": "<sys_id>"}`.
- **Journal fields lie.** `comments` and `work_notes` are write-only through the table API: they read back as empty strings.
- **No idempotency.** Retry a POST and you get a second ticket. Use `correlation_id` (with a lookup first), or your own store.
- **Pages are capped** by the instance (50 in the Console, often 10,000 on a default one, and a `Link` header with `rel="next"` either way). Read `X-Total-Count`.
- **ACLs and business rules say no with a 403** that doesn't always tell you why: closed tickets are read-only, resolving needs a resolution code and notes, and some fields aren't writable by your role. Test with the real role.
- **Rate-limit rules** are configurable per user; expect a 429 with `Retry-After`.
- **Developer instances hibernate** after a period of inactivity and answer **503 with an HTML page**. Don't parse it as JSON.

## Who holds the keys
The **ServiceNow platform owner** (here: the service desk manager). Everything reaches production through a **change request** and its board. Ask for: a dev instance, a service user with named roles, and the integration pattern they prefer (Table API, scripted REST or IntegrationHub).

## Questions to ask in week one
- Which tables and fields do we read and write? What is their rule for integrations (`correlation_id`, a source field)?
- Which role does the integration user get, and who approves it?
- What do users see about their own tickets, and what must the agent never expose?
- Which categories, assignment groups and priorities exist? Are they mandatory?
- How do changes get to production, and when does the board meet?
