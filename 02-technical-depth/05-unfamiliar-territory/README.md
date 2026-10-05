# 02/05 — Unfamiliar territory: ramping fast on someone else's system

**Prove it (skip if yes):** Dropped into a 100k-line codebase you've never seen, with a database you don't know, can you within one working day explain how a request flows through it, find where to make a change, make it safely, and write down what you learned for the next person?

## Why this matters for FDEs

Every engagement starts with you as the least-informed person in the room. The customer's IT contractor wrote that PHP app in 2019. Their data team has a 400-table warehouse with names like `T_CUST_MSTR_V2_FINAL`. You get a week, not a quarter. Speed of orientation is a core FDE skill, and interviews test it directly ("here's a repo, add X").

## Techniques

| Situation | Moves |
|---|---|
| **Unknown codebase** | Start from an entry point (route, CLI command, cron) and trace one real request end to end. Read the tests before the code. `git log --stat` on the files that matter, to see who changes what. Run it locally before changing anything |
| **Unknown database** | List tables by row count and last-modified time; the big, recently written ones are the real ones. Find foreign keys (declared or implied by naming). Sample rows. Write down the 10 tables that matter and what a row means in each |
| **Unknown business domain** | Build a glossary on day one: every acronym and in-house term, defined by the customer. Get it reviewed by them. Learn their unit economics: how they make money, and what one error costs |
| **Production you don't own** | Read-only first. Know the rollback before you deploy. Change one thing at a time. Tell the owner before, not after |
| **Coding agents** | Use Claude Code (or similar) to map the repo, answer "where is X handled?", and draft changes, then verify everything it says against the code. Check first whether the customer allows AI tools on their code and data. Some don't, and breaking that rule ends engagements |

## Lab: the 1-day ramp

Pick a large open-source application you've never touched, in a stack close to what customers run. Suggestions: Odoo (Python ERP, popular with African SMEs), Frappe/ERPNext, Saleor (Django e-commerce), Chatwoot (customer-support platform, Ruby but worth the stretch).

In **one timeboxed day**:
1. Get it running locally with seed data.
2. Write `ARCHITECTURE.md` (1 page): components, how one key request flows, where the data lives.
3. Write `GLOSSARY.md` and `DATA-MAP.md` (the 10 tables that matter).
4. Make one small real change behind a flag, with a test. Example for Odoo/ERPNext: an AI-suggested invoice category field.
5. Write `RAMP-LOG.md`: what you did hour by hour, where you lost time, and what you'll do faster next time.

Repeat with a second codebase two weeks later and compare the ramp logs. The second ramp should be noticeably faster. Being able to say you've practised this deliberately is good interview material.
