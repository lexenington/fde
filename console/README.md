# FDE Field Console

The customer's world, on your machine. One command brings up the systems a real customer would point you at, a web Console to watch and poke them, and checkers that drive **your** lab code through them and score it.

```powershell
cd console
docker compose up --build        # first boot takes a few minutes; Keycloak needs ~30s after that
```

Then open **http://localhost:3300**.

| Service | URL | What it is |
|---|---|---|
| Console | http://localhost:3300 | Dashboard, lab briefs, checker runs and history, CRM and IdP views |
| Customer simulator | http://localhost:8090 (API docs at `/docs`) | Adom Logistics' CRM API (`/crm/v3`), webhooks, rate limits, the lab checkers |
| Customer IdP | http://localhost:8081 (admin / admin) | Keycloak, standing in for Okta / Entra ID. Realms `adom` (02/02) and `savanna` (engagement 2) |
| Savanna SFTP drop | `sftp://savanna:sftp-pass@localhost:2222/export` | Core banking's nightly export, read-only |
| Lakeside database | `localhost:5433` (see the Console) | Postgres: their legacy booking system. If 5433 is taken on your machine, put `LAKESIDE_DB_PORT=5434` in `console/.env`; the Console then shows the port you chose, and your code should use it |
| **Your app** | http://localhost:8000 | Not in this stack. You build and run it yourself, in the lab folder |

## This week

**This week** (http://localhost:3300/plan) reads `PLAN.md` and `PROGRESS.md` straight from the repo: it works out which of the 16 weeks you're in from your start date (write `Started: YYYY-MM-DD` in `PROGRESS.md`, or set it on the page), shows that week's sessions and what "done" looks like, and counts what you've ticked per phase.

## Engagement worlds

| Engagement | What the Console plays | Status |
|---|---|---|
| **1 Lakeside Clinics** | Their legacy Postgres (cryptic tables, phone numbers in six formats, a non-idempotent stored procedure, a nightly backup lock), a WhatsApp provider (24-hour window, templates, signed at-least-once webhooks, delivery receipts), a speech-to-text service, a patient phone you can type on, and a hidden **36-conversation acceptance test** | **Live**. Contract: `04-engagements/lakeside/WORLD.md` |
| **2 Savanna Microfinance** | A 140-page credit policy and 15 circulars that supersede it (one not yet in force), a WhatsApp export with informal rules and a planted prompt injection, member data from three disagreeing sources (core-banking CSVs on a read-only **SFTP** drop, field sheets), a second Keycloak realm with branch groups, a panel to try your copilot as any officer, and a hidden **53-check acceptance test** | **Live**. Contract: `04-engagements/savanna/WORLD.md` |

## Practice tools

| Page | What it does | Needs |
|---|---|---|
| **Stakeholder calls** | Ten people across three customers (Adom, Lakeside, Savanna), played by Claude. Each knows things you don't and only says them when you ask well. Ends with a scored debrief: six skills, which hidden facts you found and missed, the exact question that would have unlocked each miss, and your talk ratio. The transcript is saved to `03-customer-craft/practice/` | `ANTHROPIC_API_KEY` |
| **Inject cards** | Six mid-lab curveballs for 02/02. Four change the customer's systems (CRM quota cut, duplicate and late webhooks, secret rotation, an IdP claim change), each with a one-click check that tests whether your app copes. Every card also asks for a written reply that Claude reviews against a rubric. Everything is saved in `02-technical-depth/02-enterprise-integration/lab/injects/` | `ANTHROPIC_API_KEY` for the feedback; the checks work without it |

| **01 Messy data** (under Labs) | Scores `out/clusters.json` like `check.py` (pairwise F1), then shows the raw rows behind your wrong and missed merges, and logs every score with a note on what you changed (`lab/runs/`) | nothing |
| **03 AI engineering** (under Labs) | Reads the runs `python eval.py` saves (you run it, with your key): metrics over time, what changed against the previous run, regressions, each failing document next to its text and gold answer, and the review-routing table priced in cedis | nothing |
| **04 Deploy anywhere** (under Labs) | Reviews your `terraform show -json` plan like the customer's platform team (public ALB/IP/subnet, open ingress or egress, unencrypted or public RDS, secrets in env, missing alarms or dashboard), runs the 30-minute teardown timer, and checks the runbook and handover have their sections. Reads files only; never touches AWS | nothing |
| **05 Unfamiliar territory** (under Labs) | The ramp-day clock: six milestones stamped as you reach them, a `RAMP-LOG.md` timeline built from your stamps, shape checks on ARCHITECTURE / GLOSSARY / DATA-MAP / RAMP-LOG, and ramp #2 beside ramp #1 | nothing |
| **Katas** | The thirteen drills in [`katas/`](../katas/README.md): the brief, a button that runs your tests, and the first failures. The simulator only reads the folder (mounted read-only), so your files are untouched | nothing |

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."     # before `docker compose up`, in the same terminal
docker compose up --build
```

Calls and reviews default to `claude-opus-5-5`. Set `FDE_CHAT_MODEL` / `FDE_JUDGE_MODEL` in `docker-compose.yml` (for example `claude-sonnet-5-5`) to cut cost. A full call plus debrief is a few tens of thousands of tokens.

**Don't read `sim/content/`.** It holds the stakeholders' hidden facts and the cards' effects and rubrics. It is the answer key, like `.truth/` in the messy-data lab.

**When a card has changed something**, a yellow banner on the lab page says so, so a failing checker is never a mystery. *Clear conditions* undoes every card's effect, including the IdP's claim format.

## The one rule

The Console plays the **customer** and the **grader**. It never contains your solution. Your code lives in the lab folders, runs on your machine, and gets committed with its run files (`lab/runs/*.json`), so your git history shows the score going up.

## A working session

1. Open the lab in the Console and read the **Contract** tab. Write `SCOPE.md` first.
2. Build one capability, then **Run checker**. Only the first failure shows its hint. Fix that before you read the next one (tick "show every hint" if you're stuck).
3. Use the customer's systems by hand: change a deal stage in the **CRM** page (it sends your app a signed webhook), arm 429s, get a token for a user on the **Identity** page and curl your API with it.
4. Commit your code *and* the new run file.

From the terminal instead of the UI:

```powershell
docker compose exec sim python -m sim.checks integration
```

## Labs in the Console

| Lab | Status |
|---|---|
| 02 Enterprise integration | **Live**: OIDC, SCIM, roles, CRM sync, webhooks (22 checks) |
| 01 Messy data, 03 AI engineering | Still terminal-based (`check.py`, `eval.py`) |
| Stakeholder calls and inject cards | **Live** |
| Lakeside engagement world and acceptance test | **Live** |
| Savanna engagement world and acceptance test | **Live** |

## Troubleshooting

- **"Your app" is red on the dashboard.** Start your app on port 8000 and make it listen on `0.0.0.0` (or at least accept connections from Docker). On the CRM page you can change the URL the simulator uses. From inside Docker, your machine is `host.docker.internal`.
- **Token errors right after `up`.** Keycloak is still starting; wait for its dot on the dashboard to go green.
- **Issuer mismatch.** Tokens always carry `iss = http://localhost:8081/realms/adom`, whether they were fetched from your machine or from inside Docker. Validate against exactly that.
- **"ANTHROPIC_API_KEY is not set".** Export it in the shell where you run `docker compose up`, then `docker compose up -d sim`. The dashboard shows a Claude light.
- **A call disappeared.** Active calls live in the simulator's memory, so restarting it ends them. Transcripts are only saved when you end a call and read the debrief.
- **Savanna's documents look wrong or stale.** They're generated into `console/.savanna-data/` on first start and rebuilt when the answer key changes. Delete that folder and restart the simulator to rebuild.
- **Start again from scratch.** `docker compose down` resets Keycloak and the CRM (everything lives in memory). Your app's own database is yours to reset.

## Developing the Console itself

- **Simulator:** `cd sim`, then `pip install -r requirements.txt`, `python -m pytest -q`, and `uvicorn sim.app:app --port 8090 --reload`.
- **UI:** `cd ui`, then `npm install` and `npm run dev`. It serves on :3300 and proxies to the simulator at `SIM_INTERNAL_URL`, which defaults to `http://localhost:8090`.
- **First contact with the real model:** after exporting `ANTHROPIC_API_KEY`, run `docker compose exec sim python -m sim.llm_check`. It plays one short real stakeholder call, has the judge score it and gets feedback on one card reply, in throwaway folders, for a few cents. It tells you which of the three failed and why. Everything else in the suite runs against a scripted fake, so this is the one place that proves the real API shapes work.
- **Tests use a scripted fake instead of Claude** (`llm.set_backend`), so `python -m pytest -q` needs no API key and costs nothing.
- **Adding a stakeholder:** add a character to a JSON file in `sim/content/stakeholders/` (the content test checks the shape). **Adding a card:** add it to `sim/content/injects/<lab>.json`; a new effect or check goes in `sim/sim/injects.py`.
- **Adding a lab checker:** write a `Suite` in `sim/sim/checks/`, register it in `checks/__init__.py`, and add a page under `ui/app/labs/`.
