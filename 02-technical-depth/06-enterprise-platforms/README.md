# 02/06 — Enterprise platforms: Salesforce, ServiceNow, SAP

**Prove it (skip if yes):** An AI agent needs to log a ticket in ServiceNow, update the customer's account in Salesforce and tell a customer where their SAP sales order is, from a single WhatsApp message. Without duplicating a ticket on a retry, losing page 2 of a result, or crashing when one of the three systems is down, and without giving the model permission to do more than the customer's policy allows. Can you build the tool layer, and say how you would test it, in under two weeks?

## Why this matters for FDEs

Look at what Ghanaian enterprise FDE postings actually ask for: *embed agents into CRMs, ITSM tools and internal applications*, with **Salesforce, ServiceNow and SAP** named as required skills. They are where the customer's data and workflows already live, and an agent that can't read and write them is a demo.

You don't need to become an administrator of any of them. You need to know three things about each: its **data model** (what a "customer", a "ticket", an "order" is, and how it is keyed), its **integration surface** (the API, the auth, the limits), and its **personality**: how it fails, how access really gets granted, and who in the customer's company holds the keys.

This module is deliberately honest about what you are claiming. "I integrate agents into these platforms, safely, and I have the evidence" is credible after two weeks. "I'm a Salesforce developer" is not, and an interviewer will find out in two questions.

## The three platforms in one table

| | **Salesforce** | **ServiceNow** | **SAP (S/4HANA)** |
|---|---|---|---|
| What the customer uses it for | Customers, leads, deals, cases (CRM) | IT tickets, changes, requests, assets (ITSM) | Orders, invoices, stock, finance, procurement (ERP) |
| Core objects | Account, Contact, Lead, Opportunity, Case, custom `__c` objects | `incident`, `change_request`, `sc_request`, `sys_user`, `cmdb_ci` | Business Partner, Sales Order, Delivery, Billing Document, Material |
| API you will use | REST + SOQL; Bulk API 2.0 for volume; Platform Events / Change Data Capture to listen | Table API, Scripted REST, Flow Designer/IntegrationHub | OData v2/v4 services (`API_SALES_ORDER_SRV`...); BAPIs/RFC; IDocs for async |
| Auth you will meet | OAuth 2.0 (connected app; JWT bearer for server-to-server) | Basic or OAuth; MID Server for on-prem | Basic over a technical user, or OAuth via BTP; CSRF token + cookie for every write |
| Its personality | API request limits per org; governor limits in Apex; `UNABLE_TO_LOCK_ROW`; field-level security hides fields silently | Everything is a string; reference fields are objects; ACLs and business rules veto your write with a 403; PDIs hibernate | Keys are zero-padded; dates are `/Date(ms)/`; defaults to XML; objects get locked by a user; access takes weeks |
| Free to learn on | **Developer Edition org** (real) | **Personal Developer Instance** (real) | No free S/4HANA: the API Business Hub sandbox and **the Console's SAP** |
| How the lab covers it | Your own org, self-checked ([SALESFORCE.md](lab/SALESFORCE.md)) | The Console's ServiceNow, graded | The Console's SAP, graded |

Per-platform one-pagers: [Salesforce](salesforce.md) · [ServiceNow](servicenow.md) · [SAP](sap.md). Read each in its own session, the day you build against it, not in one go.

## What an agent can safely do in each (the design rule)

The model proposes a call. **Your tool layer decides whether it runs** (kata 10), and every tool is shaped like the customer's policy, not like the platform's API:

- **Narrow tools, not a generic `call_api`.** `create_incident`, `add_comment`, `hold_order` with fixed, validated arguments. There is no `delete`, no `update_any_field`, no raw SOQL from the model.
- **Idempotent by a request id** the platform doesn't know about (kata 1). None of the three gives you idempotency for free.
- **Least privilege on the integration user**, written down and reviewed by the customer's platform admin (a Salesforce permission set, a ServiceNow role, an SAP authorisation profile). Ask for the minimum, in writing.
- **Reads that a person could have done**, scoped to the person asking. If a staff member can only see their own tickets in ServiceNow, the agent must not read someone else's on their behalf.
- **Approvals as code.** An order over GHS 50,000 needs a named approver. That is a function with a test, not a sentence in a prompt.

## The lab: Volta Industrial Supplies

Volta runs ServiceNow for IT and SAP for orders; their sales team lives in Salesforce. You build the **tool layer** of an operations agent (the agent itself, with its prompt and its eval, comes from 02/03 and 07). [lab/CONTRACT.md](lab/CONTRACT.md) has the endpoints, the credentials and every gotcha the Console will test.

1. **Write SCOPE.md first:** which workflows, which tools, who may use each, what the agent may never do, and your assumptions about access.
2. **ServiceNow tools** (`create_incident`, `add_comment`, `my_incidents`): against the Console's ServiceNow, then (stretch) against your own PDI.
3. **SAP tools** (`order_status`, `orders_summary`, `hold_order`): against the Console's SAP. Read `$metadata` first.
4. **Salesforce sync** against your own Developer Edition org: [lab/SALESFORCE.md](lab/SALESFORCE.md) says what to build and how to check yourself.
5. **Run the Console's checker** (*Labs → 06 Enterprise platforms*, 28 checks) and the two katas ([14 OData](../../katas/14-odata-query/README.md), [15 field mapping](../../katas/15-field-mapping/README.md)) before the second session.
6. Put an LLM on top: run the tools from a Claude tool-use loop and write **a 20-case eval of the agent**, including one case where the right action is to refuse. The Console grades the tool layer; the agent's judgement is yours to measure.
7. **`REPORT.md` for Volta's IT lead:** what the agent can and cannot touch in each system, the credentials and roles it needs (the exact list), what happens on each failure, and what you recommend they approve first.

**Done when:** the checker is at 28/28 (or you can explain each failing check), the Salesforce self-check passes against your org, the eval exists, and REPORT.md is written and cut by 30%.

## Stakeholder conversation to prepare for

In the real engagement you will not get the SAP credentials in week one. Practise saying: "Until I have a technical user, I'll build against the sandbox and against exports you give me, and I'll tell you every assumption I make. Can I have a read-only user on the sales order service by Friday?" The Console's SAP is the sandbox. The conversation about access is the part you can't simulate, so rehearse it with the *Stakeholder calls* page (the Volta IT lead is coming) or a friend.

## Credit where it's due

No one in a Ghanaian enterprise will give you a free hand in production SAP. A believable path is *read-only first, one workflow, one named owner, then writes behind approval*. The module teaches that path. Your REPORT.md is where you ask for it.
