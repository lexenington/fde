# Katas

Short, sharp drills for the exact skills the labs and engagements lean on. **Thirty to sixty minutes each. The tests are already written, and they are red.** Your job is to make them green, without editing the tests.

Why they exist: the labs are big and unforgiving, and a lab session that spends 90 minutes debugging a token-bucket off-by-one isn't a lab session. Do the kata first, on a tiny problem with instant feedback, and you walk into the lab with the part that bites already solved. Each kata names where it is used.

## How to do one

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest -q katas/05-jwt-validation        # red: that's the starting point
# edit the stub, run again, until green
```

Or open the Console's **Katas** page (http://localhost:3300/katas): brief, run button, first failures.

- Read the stub's docstring and the README **before** the tests. The docstring is the spec; the tests are where the edge cases are.
- Read the *first* failure only. Fix it. Run again.
- Time-box it. If you're at twice the time, write down the case you're stuck on and ask Claude to review your code with `practice-with-claude.md` prompt 4. Don't ask for the solution: the reference solutions are not in this repo on purpose.
- Done means green **and** you can say in one sentence why each edge-case test exists. Commit when green.

## The thirteen

| # | Kata | Time | Where it pays off |
|---|---|---|---|
| 01 | [Idempotency store](01-idempotency/README.md) | 45 min | 02/02 CRM sync, Lakeside's double "yes" |
| 02 | [Token bucket](02-rate-limiter/README.md) | 30 min | 02/02 rate limits, the quota-cut card |
| 03 | [Retry with backoff and jitter](03-retry-backoff/README.md) | 40 min | every integration |
| 04 | [Webhook signature](04-webhook-signature/README.md) | 40 min | 02/02, secret-rotation card, WhatsApp webhooks |
| 05 | [JWT validation](05-jwt-validation/README.md) | 60 min | 02/02 SSO, Savanna tokens |
| 06 | [Ghana phone numbers](06-phone-normalise/README.md) | 30 min | 02/01, Lakeside returning patients |
| 07 | [Clusters and F1](07-record-matching/README.md) | 45 min | 02/01 (F1 ≥ 0.92), Savanna members |
| 08 | [Rule as of a date](08-rule-as-of/README.md) | 30 min | Savanna circulars |
| 09 | [Policy chunking](09-policy-chunking/README.md) | 60 min | Savanna RAG |
| 10 | [Policy as code](10-policy-as-code/README.md) | 45 min | 02/03 approval gates, branch isolation |
| 11 | [The routing table](11-routing-table/README.md) | 30 min | 02/03 the CFO's threshold table |
| 12 | [SQL analysis](12-sql-analysis/README.md) | 45 min | 02/01, Lakeside no-show analysis |
| 13 | [Terraform plan review](13-terraform-plan-review/README.md) | 45 min | 02/04, the customer's change board |

[PLAN.md](../PLAN.md) puts each one on a Monday (or a build session) in the week it helps.

## Setup

`pip install -r requirements.txt` from the repo root (pytest and `pyjwt[crypto]` are all they need). No Docker, no API key, no network.
