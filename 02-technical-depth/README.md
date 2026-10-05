# 02 — Technical depth

Four areas, in order of FDE leverage for *you*. Each module starts with a **Prove it** check. If you can already do it cold, skip ahead.

| Module | Lab | Weeks |
|---|---|---|
| [01 Messy data](01-messy-data/README.md) | Reconcile 3 source systems into one clean Postgres model, scored against hidden truth | 1.5 |
| [02 Enterprise integration](02-enterprise-integration/README.md) | OIDC SSO + SCIM + idempotent CRM webhook sync | 2 |
| [03 AI engineering & evals](03-ai-engineering/README.md) | Document-extraction pipeline with an eval harness and human-review routing | 2.5 |
| [04 Deploy anywhere](04-deploy-anywhere/README.md) | Terraform a lab into a private-subnet "customer account" with observability | 1 |
| [05 Unfamiliar territory](05-unfamiliar-territory/README.md) | Ramp on a large unknown codebase + database in one timeboxed day, twice | 0.5 |

**Rule for every lab:** before writing code, write a half-page `SCOPE.md` in the lab folder using the [scoping template](../03-customer-craft/templates/scoping-doc.md). Pretend the lab brief came from a customer. That habit is the whole point of module 03.
