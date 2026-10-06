# Full-Stack → Forward Deployed Engineer

A personal bridge curriculum for **Alexander Agboada** (7+ yrs full-stack, Python/TS, Django/Flask/React/Next, Postgres, Docker/K8s/AWS, shipped Claude-API agents).

This is not a "learn to code" path. You already ship. The FDE bar is different:

> An FDE is the engineer who goes **into a customer's world** — their data, their systems, their politics, their deadline — and comes back out with **working software in production that moves a business metric**, while feeding what they learned back to the product team.

The difference from what you do now isn't the code. It's **who defines the problem, whose infrastructure it runs on, and how you prove it worked.**

---

## The map

| # | Module | What it closes | Time (part-time) |
|---|---|---|---|
| 00 | [The role](00-the-role/README.md) | Know exactly what you're aiming at — the three flavours of FDE and how each is evaluated | 2 days |
| 01 | [Gap analysis](01-gap-analysis/README.md) | Your profile vs. the FDE bar, honestly. Reframing your existing projects | 2 days |
| 02 | [Technical depth](02-technical-depth/README.md) | The four technical areas full-stack devs are usually thin on | 6–7 weeks |
| | ↳ [Messy data](02-technical-depth/01-messy-data/README.md) | Ingesting, reconciling and loading data you didn't design | |
| | ↳ [Enterprise integration](02-technical-depth/02-enterprise-integration/README.md) | SSO, SCIM, CRMs, webhooks, idempotency, rate limits | |
| | ↳ [AI engineering & evals](02-technical-depth/03-ai-engineering/README.md) | From "demo works" to "measured, safe, in production" | |
| | ↳ [Deploy anywhere](02-technical-depth/04-deploy-anywhere/README.md) | Running in the customer's cloud / VPC / constrained environment | |
| | ↳ [Unfamiliar territory](02-technical-depth/05-unfamiliar-territory/README.md) | Ramping in a day on a codebase, database and domain you've never seen | |
| 03 | [Customer craft](03-customer-craft/README.md) | Discovery, scoping, demos, stakeholders, writing — plus templates | 2 weeks (in parallel) |
| 04 | [Engagements](04-engagements/README.md) | Three simulated end-to-end customer deployments = your new portfolio | 4–5 weeks |
| 05 | [Getting hired](05-getting-hired/README.md) | Target companies, remote-from-Ghana strategy, résumé, interview loop, visibility | 2 weeks (overlaps) |
| 06 | [Beyond](06-beyond/README.md) | Roles these skills unlock, and turning Webfront360 into a business | ongoing |
| 07 | [AI-startup FDE](07-ai-startup-fde/README.md) | Running many customers on one AI product: implementation playbooks, simulation testing, release checks, startup interviews and offers | 1.5 weeks (before applying to tier B) |
| 🖥 | [FDE Field Console](console/README.md) | A local web app that plays the customer (IdP, SCIM, CRM, webhooks) and scores your lab code against it. `docker compose up` in `console/` | stakeholder calls and the plan from week 1, the lab pages as you reach them |
| 🥋 | [Katas](katas/README.md) | Thirteen 30-60 minute drills with the tests already written and red: idempotency, JWT validation, rate limits, record matching, policy chunking, Terraform plan review. One per week, on Monday | weeks 2-13, see PLAN.md |
| ☁ | [AWS FDE track](aws-fde-track/README.md) | AWS's Ground / Orchestrate / Prove FDE pathways mapped to this repo, extra labs, and the AIP-C01 route | in parallel, weeks 6–16 |

**Total: ~16–18 weeks at 10–15 hrs/week** (07 and the AWS track overlap with other modules). Track it in [PROGRESS.md](PROGRESS.md). Reading list in [resources.md](resources.md).

## How to use this repo

0. **Open [PLAN.md](PLAN.md).** It says what to do this week, session by session, with the tool to use and what "done" looks like. The Console's *This week* page (http://localhost:3300/plan) shows the same, with your progress.
1. Read 00 and 01 first, in full. They set the target, and everything else follows from them.
2. Every technical module has a **"Prove it"** check up top. If you can already do it, skip the module and move on. Don't re-learn what you know.
3. Labs live inside their module (`lab/` folders). Do the work in this repo and commit it. **The git history is evidence.**
4. Module 03 runs *alongside* 02. You practise customer craft on every lab by writing the scoping doc *before* the code.
5. Module 04 is the point of the whole thing. Each engagement produces a public write-up. Those write-ups replace the "projects" grid on your portfolio.

## Setup (this machine)

Done: Python 3.12 is installed (winget, user scope), `.venv` has the packages from `requirements.txt`, and the repo is a git repository. Labs are in Python, since that's the FDE lingua franca. In each new terminal:

```powershell
.\.venv\Scripts\Activate.ps1
```

**On a new machine** (the above is already done on this one):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest -q katas/06-phone-normalise     # red: that is the correct starting state
```

Commit after every lab step. **The git history is your evidence trail.**

You'll also need Docker Desktop (for Postgres in the data lab, and for the [Field Console](console/README.md)) and an Anthropic API key (`ANTHROPIC_API_KEY`) for the AI lab.

## The one-sentence goal

By week 16 you should be able to say, with links to prove it:

> *"I take an ambiguous business problem inside someone else's systems, scope it with the stakeholders, ship an AI-enabled solution into their environment, measure that it works, and leave them able to run it. Here are three times I did that."*
