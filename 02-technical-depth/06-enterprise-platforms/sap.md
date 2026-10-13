# SAP in one page (for the engineer who has to plug an agent into it)

## The model
SAP S/4HANA (or its predecessor ECC) is the customer's ERP: sales, billing, stock, purchasing, finance. Data lives in tables you will rarely touch directly; you meet **business objects** through services. A **Business Partner** is any customer or supplier; a **Sales Order** has items, a delivery status, a billing status and blocks; the same customer may appear under several roles. Keys are **zero-padded strings** (`0000012345`). A **client** (`100`) is a separate logical system in the same installation. There is a **dev, a quality and a production system**, and transports carry changes between them.

## The integration surface
- **OData services** (the modern way): `/sap/opu/odata/sap/API_SALES_ORDER_SRV/A_SalesOrder`, from the **SAP Gateway**. v2 is JSON or XML; v4 exists for newer services. Browse them in the **SAP API Business Hub** (api.sap.com) and read `$metadata` first. A service is *activated* by the customer's team before you can call it.
- **BAPIs / RFC** (function modules, called with SAP's RFC libraries) for what no OData service covers. This is a different skill and usually needs a Basis-owned connection.
- **IDocs / EDI** for asynchronous business documents between systems.
- **Events** (SAP Event Mesh, business events) where the customer has them. Many don't.
- **Auth:** a **technical user** (Basic) or OAuth through SAP BTP. The user has *authorisation objects*; "missing authorisation" is a 403 you can't fix from your side.
- Writes: **CSRF token + session cookie + `If-Match` ETag**, every time.

## How it fails (and how it looks)
- **Atom XML by default.** No `Accept: application/json`, no JSON.
- **Dates and numbers:** `/Date(1789344000000)/` and `"12450.00"`. Decimal and timezone mistakes are how money goes missing.
- **Key padding** (`'12345'` is a 404) and **datetime literals** in filters (`datetime'2026-10-01T00:00:00'`).
- **Server-driven paging** (`__next`, `$skiptoken`): the first page is not the collection.
- **Locks.** An order being edited is locked; the error names the user. Expected, not an outage.
- **Concurrency.** `412` means the ETag moved. Read again before you write again.
- **Slowness**, especially at month end. Set sensible timeouts, don't retry in parallel.
- **Business rules.** SAP refuses what is wrong in business terms (a delivered order can't take a block) with a message written for a consultant. Pass it on in plain words.

## Who holds the keys
**Basis** (the system administrators), **security** (authorisations) and the **functional owner** of the process (here: order-to-cash). Access takes **weeks**, goes through a change board, and is read-only first. A personal login is never the answer. There is no free S/4HANA to practise on: use the API Business Hub sandbox (sample data, API key) and the Console's SAP.

## Questions to ask in week one
- Which OData services are activated, in which system, and who can activate another?
- Can I have a read-only technical user in dev this week, and quality next, with the exact authorisations written down?
- What are the real volumes, busy periods and locking habits (month end, billing runs)?
- What may an agent change, who approves it, and where is the approval recorded?
- Who is on call in Basis if an integration misbehaves?
