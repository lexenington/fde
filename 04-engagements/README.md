# 04 — Engagements

Three simulated, end-to-end customer deployments. These are the point of the whole curriculum: each one becomes a public **case study** on your portfolio and your best interview material.

| # | Engagement | Main skills exercised | Weeks |
|---|---|---|---|
| 1 | [Lakeside Clinics — WhatsApp patient assistant](01-lakeside-clinics.md) | Agent design, safety, escalation, evals, multilingual, low connectivity | 3 (weeks 9-11) |
| 2 | [Savanna Microfinance — loan-officer copilot](02-savanna-microfinance.md) | Messy data, permission-aware RAG, SSO, deploy in customer's AWS, risk sign-off | 3 (weeks 12-14) |
| 3 | [A real customer](03-real-customer.md) | Everything, with real stakes and a real reference | runs alongside, weeks 2-15 |

**The customers' systems are simulated in the [FDE Console](../console/README.md)**: each engagement has a `WORLD.md` (the integration contract) and an acceptance test that runs against your code. Live now: [Lakeside](lakeside/WORLD.md) and [Savanna](savanna/WORLD.md).

## How to run a simulated engagement

1. Read the brief and **only** the brief. Stakeholder memos contradict each other on purpose.
2. Do discovery anyway: run the Console's stakeholder calls for this customer (or get a friend to role-play the sponsor using the memo), and keep the transcript.
3. Produce the **scoping doc** before any code ([template](../03-customer-craft/templates/scoping-doc.md)).
4. Build in weekly increments. Write a **weekly update** each week, even though nobody is reading it.
5. Hit the **acceptance bar** with an eval run you can reproduce.
6. Deliver: runbook, handover doc, a 5-min recorded demo, **field feedback** note.
7. Publish the **case study** ([template](case-study-template.md)).

## Rubric (score yourself honestly, 1–5 per row)

| Dimension | 5 looks like |
|---|---|
| Problem framing | Success metric with baseline; out-of-scope list that you actually used |
| Technical quality | Simplest architecture that hits the bar; tests; idempotent; observable |
| Measurement | Reproducible eval; slices; error analysis; numbers in every claim |
| Safety & risk | Threats enumerated and tested; human-in-the-loop designed, not bolted on |
| Deployability | Someone else can deploy, operate and roll back from your docs alone |
| Communication | Every doc readable by its audience in < 5 min; demo shows the *user's* workflow |
| Product leverage | Field feedback that a PM could act on |
