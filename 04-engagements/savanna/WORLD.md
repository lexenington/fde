# Savanna Microfinance: the world you're deploying into

You build a loan-officer copilot in **your own code**, in any language, running on your machine at `http://localhost:8000`. The [FDE Console](../../console/README.md) (`docker compose up --build` in `console/`, then http://localhost:3300 → *Engagements → 2 Savanna Microfinance*) plays everything Savanna owns: their documents, their core-banking export, their login system, and the acceptance test. Read the [engagement brief](../02-savanna-microfinance.md), run the stakeholder calls (Samuel Ofosu, Esi Koomson, Nii Armah, Ruth Alhassan), and write `SCOPE.md` before code.

## What they gave you

| Thing | Where |
|---|---|
| **Credit Policy Manual, Version 7** (140 pages) | Console → *Documents*, or `http://localhost:8090/savanna/share/Credit-Policy-Manual-v7.pdf` |
| **Circulars** (15, 2024-2026) | `…/share/circulars/Circular-YYYY-NN.pdf`. A circular amends a section of the manual **from its effective date**; later circulars can supersede earlier ones. One of them has been issued but is **not yet in force** |
| **WhatsApp export** from the regional manager's credit-officers group | `…/share/whatsapp/Northern-Region-Credit-Officers.txt`. Ruth told you half the "policy" lives here |
| **Officers' field sheets** (4 branches) | `…/share/field-sheets/*.csv`: the names as officers write them |
| **Core banking nightly export** | SFTP `localhost:2222`, user `savanna`, password `sftp-pass`, folder `/export`: `members_`, `loans_` and `repayments_` CSVs, read-only |
| **Login** | Keycloak, standing in for Microsoft Entra ID: issuer `http://localhost:8081/realms/savanna`, client and audience **`copilot`**. Six officers, password `Passw0rd!` (see the Console) |

"Today" in Savanna's world is **2026-10-06**. Every question you receive carries `as_of`; answer from the documents in force on that date.

### Things Ruth, Nii and Esi told you, and what that means for the data

- The manual and the circulars disagree on purpose. The base manual is **not** the current rule once a circular amends it. Cite what you relied on: the circular if one applies, otherwise the manual section.
- The WhatsApp export contains **informal instructions** (a grace period on market days, a higher Ramadan cash limit, "one guarantor is enough"). They are not policy. It also contains a message **addressed to AI systems** telling them to ignore the policy. Documents are data, never instructions.
- Core banking writes `SURNAME Firstname`. Field sheets write names five ways, with phones missing or one digit wrong. The same person is three records. Use the techniques from 02/01.
- Officers must never see members outside their own branch. A previous consultant's demo showed everyone, and Esi ended the project on the spot.

## Identity

Every `/api` route needs `Authorization: Bearer <access token>` from the realm above. Validate it as in 02/02 (issuer, signature via JWKS, expiry, **audience `copilot`**). The token's `groups` claim carries:

| Group | Meaning |
|---|---|
| `officers` | A loan officer. Exactly one `branch-…` group says which branch (`branch-tamale-c`, `branch-yendi`, `branch-bolga`, `branch-sunyani`, …) |
| `risk` | Esi's team: all branches, and the only people who may export the audit log |

## What your app must expose

**`POST /api/ask`** with `{"question": "…", "as_of": "2026-10-06"}`

```json
{"answer": "The maximum for a first individual loan is GHS 4,000 (Circular 2025/01).",
 "citations": [{"doc": "circular-2025-01", "section": "4.2.1"}],
 "abstained": false}
```

- Answer with the rule in force on `as_of`, and say so plainly. A superseded value may appear as history ("raised from…"), never as the current rule.
- `citations` is a list; each entry names the document (`doc`) and/or `section` and/or `circular` it relied on. An answer without a citation counts as no answer.
- If the documents don't answer the question, return `"abstained": true` and say so. Esi would rather hear "ask Risk" than a guess. Informal WhatsApp instructions are not an answer: decline, or give the official rule and flag the message.
- Never answer from, or repeat, another branch's member data.

**`GET /api/members/summary?q=…`**: `q` is a member id (`M00020`), a phone number in any format, or a name with a village (`Hawa Zakaria, Bimbilla`). Return 200:

```json
{"member_id": "M00020", "branch": "TAMALE-C", "active_loans": 2, "outstanding_ghs": 1399.67,
 "max_arrears_days": 0, "last_repayment_date": "2026-09-23"}
```

`active_loans` and `outstanding_ghs` cover **active** loans only; `max_arrears_days` is the worst across them; `last_repayment_date` is the latest paid installment across all the member's loans. A member outside the officer's branch is `403` or `404` and reveals nothing. Risk sees all.

**`GET /api/audit/export.csv`** (Risk only; `401`/`403` for everyone else): one row per question asked, with the columns `timestamp, user, question, retrieved, answer` (`retrieved` is what your retrieval returned: ids, titles or chunks). Esi hands this to the Bank of Ghana, so it must be complete and written in the code path that answers.

## The acceptance test

The **Acceptance test** tab asks your copilot **53 hidden checks** as real officers, with real tokens. You see the categories, and for any failure the question, your answer and why.

| Category | What Esi and Samuel are checking |
|---|---|
| Policy answers (30) | The current rule on the stated date, from the right document, with a correct citation. Includes questions as of earlier dates, a circular announced but not yet in force, and the planted instruction in the WhatsApp export |
| Not in the policy (7) | Five things the documents don't say, and two informal WhatsApp rules: decline or flag, never assert |
| Member summaries (8) | By id, by phone in different formats, by names written differently. Exact numbers |
| Branch isolation (6) | A Tamale officer cannot reach another branch's members by id, by phone number, or by asking the copilot. Risk can. No token, or a token for another app, is refused |
| Audit trail (2) | Risk can export every question that was asked, with the right user. Officers cannot |

There is no pass mark in code. Samuel's bar is **answer accuracy and citation accuracy you can report, every permission test passing, and an audit trail that stands up**. The summary prints the numbers, and Esi will ask about the false-abstention rate.

## What this world does *not* test

- **Your own eval**: the brief asks for **80+ policy questions with gold answers and citations that you write**, including circular-override cases and abstentions, and a **30-member truth set you build by hand**. Those are your deliverables. The customer's test is on top, and you can't see its questions. Tune against your own set, not this one.
- Deploying into the customer's AWS account with Terraform (02/04), Bedrock versus the first-party API versus an egress proxy (write the decision record), real Entra ID, the memo to the Head of Risk about how the system can be wrong, and the teardown-and-redeploy drill.
- Whether an answer is *good*. The checks match facts and citations; a reply can pass and still be something Esi would reject. Read your own transcripts.

## Practical notes

- The documents are generated deterministically the first time the Console starts (about 30 seconds) and kept in `console/.savanna-data/`. Delete that folder to rebuild them.
- *Documents, officers & try it* lets you call your copilot as any officer without writing a client.
- Each run is saved in [`runs/`](runs/). Commit them.
